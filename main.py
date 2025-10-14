# main.py - The nerve center of our resume-slaying AI (-- IGNORE ---) bro
import io
import pypdf
import docx
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crewai import Crew, Process

import firebase_utils as db
from agents import (
    create_router_agent,
    create_company_researcher_agent,
    create_job_matcher_agent,
    create_section_enhancer_agent,
    create_translation_agent
)
from tasks import (
    create_routing_task,
    create_company_research_task,
    create_job_matching_task,
    create_section_enhancement_task,
    create_translation_task
)

app = FastAPI(
    title="Conversational Resume Optimization System API",
    description="An API for optimizing resumes through a multi-agent chat system.",
    version="1.0.0"
)

# --- CORS Middleware ---
# Gotta let the frontend talk to us. This is the digital handshake.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, anyone can ping us. Lock this down in prod, obviously.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---
# Defining the shapes of our data. Think of these as the bouncers for our API endpoints.
class ChatRequest(BaseModel):
    conversation_id: str
    message: str

class ChatResponse(BaseModel):
    conversation_id: str
    agent_response: str
    reasoning: str
    updated_resume: str
    match_score: float | None = None
    skill_gaps: list[str] | None = None
    
class UploadResponse(BaseModel):
    conversation_id: str
    resume_text: str
    message: str

# --- Helper Functions ---
# These are the unsung heroes, the utility belt of our main script.

def parse_resume(file: UploadFile) -> str:
    """Chews up a PDF or DOCX and spits out clean text. No magic, just solid code."""
    text = ""
    try:
        if file.content_type == 'application/pdf':
            # Using pypdf to rip through PDFs. It's fast, it's clean.
            pdf_reader = pypdf.PdfReader(io.BytesIO(file.file.read()))
            for page in pdf_reader.pages:
                text += page.extract_text()
        elif file.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            # DOCX files are just XML sandwiches. We're unwrapping them.
            document = docx.Document(io.BytesIO(file.file.read()))
            for para in document.paragraphs:
                text += para.text + '\n'
        else:
            # If it's not a PDF or DOCX, we don't want it. Simple as.
            raise HTTPException(status_code=400, detail="Unsupported file type. Stick to PDF or DOCX.")
    except Exception as e:
        # Something blew up. We're catching it and letting the user know.
        raise HTTPException(status_code=500, detail=f"File parsing went sideways: {e}")
    return text

def parse_agent_output(result: str):
    """
    This function is basically a regex ninja. It slices and dices the raw output from
    our AI agents to pull out the juicy bits: reasoning, the new resume, match scores, and skill gaps.
    It's smart enough to handle different output formats from different agents.
    """
    try:
        # The job_matcher agent has a special format. We handle that first.
        if '###SKILL_GAPS###' in result and '###UPDATED_RESUME###' in result:
            parts = result.split('###SKILL_GAPS###')
            reasoning_with_score = parts[0].strip()
            gaps_part = parts[1].split('###UPDATED_RESUME###')[0].strip()
            updated_resume = parts[1].split('###UPDATED_RESUME###')[1].strip() if len(parts[1].split('###UPDATED_RESUME###')) > 1 else ""
            
            # Score extraction. A bit of string-fu to grab the number.
            score_match = reasoning_with_score.lower().find('match score:')
            if score_match != -1:
                score_str = reasoning_with_score[score_match:score_match+20].split('%')[0].split(':')[-1].strip()
                match_score = float(score_str) if score_str.isdigit() else None
            else:
                match_score = None
            
            # Skill gaps are just a list of strings. Easy peasy.
            skill_gaps = [gap.strip() for gap in gaps_part.split('\n') if gap.strip() and gap.strip().startswith('-')]
            
            return reasoning_with_score, updated_resume, match_score, skill_gaps
        else:
            # For everyone else, it's a simpler split.
            parts = result.split("###UPDATED_RESUME###")
            reasoning = parts[0].strip()
            updated_resume = parts[1].strip() if len(parts) > 1 else ""
            return reasoning, updated_resume, None, None
    except Exception:
        # If everything fails, just return the raw output. No shame in that.
        return result.strip(), "", None, None

# --- Version Control Endpoints ---
# Because 'undo' is the most important feature in any software.

@app.get("/versions/{conversation_id}")
async def get_resume_versions(conversation_id: str):
    """Pulls all the resume versions for a given chat. Like a git history for your career."""
    query = db.collection('resumes').where('conversationId', '==', conversation_id).order_by('version')
    docs = list(query.stream())
    versions = [doc.to_dict() for doc in docs]
    return {"versions": versions}

@app.post("/revert/{conversation_id}/{version}")
async def revert_resume_version(conversation_id: str, version: int):
    """Time travel. Jumps back to a previous version of the resume."""
    query = db.collection('resumes').where('conversationId', '==', conversation_id).where('version', '==', version)
    docs = list(query.stream())
    if not docs:
        raise HTTPException(status_code=404, detail="Version not found. Can't revert to something that doesn't exist.")
    
    target_version = docs[0].to_dict()
    # We don't actually delete anything. We just create a new version that's a copy of the old one.
    # It's safer and keeps the timeline intact.
    db.save_resume_version(
        conversation_id=conversation_id,
        original_text=target_version['original_text'],
        modified_text=target_version['modified_text'],
        agent_reasoning=f"Reverted to version {version}."
    )
    return {"message": f"Reverted to version {version}", "resume": target_version['modified_text']}

# --- Core API Endpoints ---
# This is where the magic happens.

@app.post("/upload", response_model=UploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """
    The entry point. User throws a resume at us, we catch it, parse it,
    and kick off a new conversation in Firestore.
    """
    resume_text = parse_resume(file)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Couldn't get any text out of that file. You sure it's not empty?")

    # Every session gets a unique ID.
    conversation_id = db.create_new_conversation()
    
    # Save the OG resume. This is version 1.
    db.save_resume_version(
        conversation_id=conversation_id,
        original_text=resume_text,
        agent_reasoning="Initial upload."
    )
    
    return UploadResponse(
        conversation_id=conversation_id,
        resume_text=resume_text,
        message="Resume locked and loaded. Let's get to work."
    )

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    The main event. This endpoint is a whole pipeline. It routes the user's message,
    fires up the right AI agents, and pieces together a response. It's a beautiful mess.
    """
    conversation_id = request.conversation_id
    user_message = request.message
    
    # 1. What's the latest? Pull the history and the current resume from our database.
    history = db.get_conversation_history(conversation_id)
    latest_resume_data = db.get_latest_resume(conversation_id)
    
    if not latest_resume_data:
        raise HTTPException(status_code=404, detail="No resume found. Upload one first, chief.")

    current_resume_text = latest_resume_data.get('modified_text')

    # 2. Log the user's message. We need to remember what they said.
    db.update_conversation_history(conversation_id, {"role": "user", "content": user_message})
    
    # 3. The Router Agent. This is our traffic cop. It decides which agent (or agents) get the job.
    router_agent = create_router_agent()
    routing_task = create_routing_task(router_agent, user_message, history)
    
    router_crew = Crew(agents=[router_agent], tasks=[routing_task], process=Process.sequential)
    route_output = router_crew.kickoff()
    
    # The router gives us a JSON list of agents. We parse that.
    try:
        agent_sequence = json.loads(route_output.strip())
        if not isinstance(agent_sequence, list):
            # If it's not a list, make it one. Consistency is key.
            agent_sequence = [agent_sequence] if agent_sequence else []
    except json.JSONDecodeError:
        # If the JSON is busted, we fall back to a simple chit-chat response.
        agent_sequence = ['general_chitchat']

    # 4. Prep for the response. We'll build this up as we go.
    full_reasoning = ""
    updated_resume = current_resume_text
    match_score = None
    skill_gaps = None

    # 5. The main loop. We iterate through the agent sequence and let them do their thing.
    current_resume = current_resume_text
    for agent_type in agent_sequence:
        agent_type = agent_type.lower().strip()
        
        # This is basically a switch statement for our agents.
        if agent_type == 'company_researcher':
            agent = create_company_researcher_agent()
            task = create_company_research_task(agent, current_resume, user_message)
            crew = Crew(agents=[agent], tasks=[task], verbose=2)
            result = crew.kickoff()
            reasoning, new_resume, _, _ = parse_agent_output(result)
            full_reasoning += f"\n\nCompany Research: {reasoning}"
            current_resume = new_resume or current_resume
            
        elif agent_type == 'job_matcher':
            agent = create_job_matcher_agent()
            task = create_job_matching_task(agent, current_resume, user_message)
            crew = Crew(agents=[agent], tasks=[task], verbose=2)
            result = crew.kickoff()
            reasoning, new_resume, score, gaps = parse_agent_output(result)
            full_reasoning += f"\n\nJob Matching: {reasoning}"
            match_score = score
            skill_gaps = gaps
            current_resume = new_resume or current_resume

        elif agent_type == 'section_enhancer':
            agent = create_section_enhancer_agent()
            task = create_section_enhancement_task(agent, current_resume, user_message)
            crew = Crew(agents=[agent], tasks=[task], verbose=2)
            result = crew.kickoff()
            reasoning, new_resume, _, _ = parse_agent_output(result)
            full_reasoning += f"\n\nSection Enhancement: {reasoning}"
            current_resume = new_resume or current_resume
            
        elif agent_type == 'translation':
            agent = create_translation_agent()
            task = create_translation_task(agent, current_resume, user_message)
            crew = Crew(agents=[agent], tasks=[task], verbose=2)
            result = crew.kickoff()
            reasoning, new_resume, _, _ = parse_agent_output(result)
            full_reasoning += f"\n\nTranslation & Localization: {reasoning}"
            current_resume = new_resume or current_resume
            
        else:  # 'general_chitchat' or some other fallback
            chit_chat_response = "I'm an AI built for one thing: leveling up your resume. How can we make it better?"
            full_reasoning += f"\n\nGeneral: {chit_chat_response}"
            # No resume changes for chit-chat.

    updated_resume = current_resume
    agent_response = full_reasoning.strip()

    # 6. If the resume changed, we save a new version. Immutable history is a good thing.
    if updated_resume and updated_resume != current_resume_text:
        db.save_resume_version(
            conversation_id=conversation_id,
            original_text=latest_resume_data.get('original_text'),
            modified_text=updated_resume,
            agent_reasoning=full_reasoning
        )
    
    # 7. Log the AI's response. Now the conversation is balanced.
    db.update_conversation_history(conversation_id, {"role": "assistant", "content": agent_response})
    
    # 8. Send it all back to the user. Job done.
    return ChatResponse(
        conversation_id=conversation_id,
        agent_response=agent_response,
        reasoning=full_reasoning,
        updated_resume=updated_resume,
        match_score=match_score,
        skill_gaps=skill_gaps
    )

if __name__ == "__main__":
    # This is how we run the server. Fire it up and let the requests roll in.
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
