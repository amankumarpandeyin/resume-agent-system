import io, pypdf, docx, json, time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crewai import Crew
from litellm.exceptions import RateLimitError

import firebase_utils as db
from agents import create_router_agent, create_company_researcher_agent, create_job_matcher_agent, create_section_enhancer_agent, create_translation_agent
from tasks import create_routing_task, create_task

app = FastAPI(title="Conversational Resume Optimization System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class ChatRequest(BaseModel):
    conversation_id: str
    message: str

class ChatResponse(BaseModel):
    conversation_id: str; agent_response: str; reasoning: str; updated_resume: str
    match_score: float | None = None; skill_gaps: list[str] | None = None
    
class UploadResponse(BaseModel):
    conversation_id: str; resume_text: str; message: str

def parse_resume(file: UploadFile) -> str:
    text, content_type, file_content = "", file.content_type, file.file.read()
    if content_type == 'application/pdf':
        for page in pypdf.PdfReader(io.BytesIO(file_content)).pages: text += page.extract_text()
    elif content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        for para in docx.Document(io.BytesIO(file_content)).paragraphs: text += para.text + '\n'
    else: raise HTTPException(status_code=400, detail="Unsupported file type.")
    return text

def parse_agent_output(result: str):
    reasoning, updated_resume, score, gaps = result, "", None, None
    if '###UPDATED_RESUME###' in result:
        parts = result.split('###UPDATED_RESUME###')
        reasoning = parts[0].strip()
        updated_resume = parts[1].strip() if len(parts) > 1 else ""
    if '###SKILL_GAPS###' in reasoning:
        gap_parts = reasoning.split('###SKILL_GAPS###')
        reasoning = gap_parts[0].strip()
        gaps = [g.strip() for g in gap_parts[1].strip().split('\n') if g.strip()]
    score_match = reasoning.lower().find('match score:')
    if score_match != -1:
        try: score = float(reasoning[score_match:score_match+20].split('%')[0].split(':')[-1].strip())
        except (ValueError, IndexError): pass
    return reasoning, updated_resume, score, gaps

# --- NEW HELPER FUNCTION FOR RATE LIMITING ---
def run_crew_with_retry(crew, max_retries=3):
    """Run a crew with automatic retry on rate limit errors."""
    for attempt in range(max_retries):
        try:
            result = crew.kickoff()
            # Handle new CrewAI output format
            return str(result.raw) if hasattr(result, 'raw') else str(result)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            else:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded after multiple retries. Please wait a moment and try again."
                )
        except Exception as e:
            # Catch any other unexpected errors during kickoff
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.get("/versions/{conversation_id}")
async def get_resume_versions(conversation_id: str):
    return {"versions": db.get_all_resume_versions(conversation_id)}

@app.post("/revert/{conversation_id}/{version}")
async def revert_resume_version(conversation_id: str, version: int):
    reverted = db.revert_to_version(conversation_id, version)
    if not reverted: raise HTTPException(status_code=404, detail="Version not found.")
    return {"message": f"Reverted to version {version}", "resume": reverted['modified_text']}

@app.post("/upload", response_model=UploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    text = parse_resume(file)
    if not text: raise HTTPException(status_code=400, detail="Could not extract text.")
    convo_id = db.create_new_conversation()
    db.save_resume_version(conversation_id=convo_id, original_text=text)
    return UploadResponse(conversation_id=convo_id, resume_text=text, message="Resume uploaded.")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    convo_id, message = request.conversation_id, request.message
    history, latest_resume = db.get_conversation_history(convo_id), db.get_latest_resume(convo_id)
    if not latest_resume: raise HTTPException(status_code=404, detail="No resume found.")
    
    current_resume = latest_resume['modified_text']
    db.update_conversation_history(convo_id, {"role": "user", "content": message})
    
    router_crew = Crew(agents=[create_router_agent()], tasks=[create_routing_task(create_router_agent(), message, history)])
    route_output = run_crew_with_retry(router_crew)
    
    try: agent_sequence = json.loads(route_output.strip())
    except json.JSONDecodeError: agent_sequence = ['general_chitchat']
    
    reasoning, score, gaps = "", None, None

    creators = {
        "company_researcher": (create_company_researcher_agent, "An explanation of changes, followed by the full updated resume.", "A user wants to optimize their resume for a specific company based on this query: '{message}'.\n1. Research the company's culture, values, and tech stack.\n2. Analyze the user's resume:\n---RESUME---\n{current_resume}\n---\n3. Rewrite the resume to align with the company.\n4. Explain your changes, then provide the full updated resume inside '###UPDATED_RESUME###' tags."),
        "job_matcher": (create_job_matcher_agent, "An explanation with a score, a list of skill gaps, and the full updated resume.", "A user wants to tailor their resume to a job description provided in their query: '{message}'.\n1. Analyze the job description and the resume:\n---RESUME---\n{current_resume}\n---\n2. Rewrite the resume to be a perfect match.\n3. Calculate a match score (0-100%) and list 3-5 skill gaps.\n4. Your output must contain your analysis, then a list of skill gaps inside '###SKILL_GAPS###' tags, and finally the full updated resume inside '###UPDATED_RESUME###' tags."),
        "section_enhancer": (create_section_enhancer_agent, "An explanation of changes, followed by the full updated resume.", "A user wants to improve a specific resume section based on their query: '{message}'.\n1. Identify the target section.\n2. Analyze the section within the full resume:\n---RESUME---\n{current_resume}\n---\n3. Rewrite only the target section using action verbs, metrics, and the STAR method.\n4. Explain the improvements, then provide the full updated resume in '###UPDATED_RESUME###' tags."),
        "translation": (create_translation_agent, "An explanation of localization choices, followed by the full updated resume.", "A user wants to translate their resume based on the query: '{message}'.\n1. Identify the target language and country.\n2. Research local hiring conventions for that country.\n3. Translate and adapt the resume:\n---RESUME---\n{current_resume}\n---\n4. Explain your localization choices, then provide the full translated resume in '###UPDATED_RESUME###' tags."),
    }

    for agent_type in agent_sequence:
        if agent_type in creators:
            agent_creator, expected_output, desc_template = creators[agent_type]
            agent = agent_creator()
            task = create_task(desc_template.format(message=message, current_resume=current_resume), agent, expected_output)
            result_str = run_crew_with_retry(Crew(agents=[agent], tasks=[task]))
            
            res, new_resume, s, g = parse_agent_output(result_str)
            reasoning += f"\n\n{agent_type.replace('_', ' ').title()}: {res}"
            if new_resume: current_resume = new_resume
            if s: score = s
            if g: gaps = g
        else:
            reasoning += "\n\nI'm designed to help with resumes. How can I assist you with yours?"

    response = reasoning.strip()
    if current_resume != latest_resume['modified_text']:
        db.save_resume_version(conversation_id=convo_id, original_text=latest_resume['original_text'], modified_text=current_resume, agent_reasoning=response)
    
    db.update_conversation_history(convo_id, {"role": "assistant", "content": response})
    
    return ChatResponse(
        conversation_id=convo_id, agent_response=response, reasoning=response,
        updated_resume=current_resume, match_score=score, skill_gaps=gaps
    )
