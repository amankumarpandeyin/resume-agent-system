import os
from crewai import Agent
from langchain_groq import ChatGroq
from tools import web_search_tool
from dotenv import load_dotenv
import litellm
load_dotenv()
litellm.max_retries = 3
groq_api_key = os.getenv("GROQ_API_KEY")
model_name = "groq/llama-3.1-8b-instant"
llm = ChatGroq(api_key=groq_api_key, model_name=model_name)
router_llm = ChatGroq(api_key=groq_api_key, model_name=model_name)
synthesizer_llm = ChatGroq(api_key=groq_api_key, model_name=model_name)


# --- AGENT DEFINITIONS ---

def create_router_agent():
    """Creates the agent responsible for routing user queries."""
    return Agent(
        role='Intelligent Conversation Router',
        goal=(
            "Analyze the user's query to determine the appropriate agent sequence. "
            "Available agents: 'job_matcher', 'company_researcher', 'section_enhancer', 'translation', 'general_chitchat'."
        ),
        backstory=(
            "You are an intelligent routing system that analyzes user intent. "
            "You output ONLY a JSON array of agent keywords in the correct execution order. "
            "For complex queries, chain multiple agents. For simple queries, use a single agent."
        ),
        llm=router_llm,
        verbose=True,
        allow_delegation=False
    )

def create_company_researcher_agent():
    """Creates the agent that researches companies."""
    return Agent(
        role='Company Culture Research Specialist',
        goal="Uncover a company's culture, values, and mission using a single, focused web search.",
        backstory=(
            "You are an expert at researching companies to provide actionable insights for job applicants. "
            "You are a master of using the web search tool to find information that isn't obvious. "
            "CRITICAL RULE: When you use the web_search_tool, you MUST pass a simple string as the 'query'. "
            "For example: `web_search_tool(query='VectorShift company culture and values')`."
        ),
        tools=[web_search_tool],
        llm=llm,
        allow_delegation=False,
        verbose=True
    )

def create_job_matcher_agent():
    """Creates the agent that analyzes job descriptions."""
    return Agent(
        role='Job Description Analysis Expert',
        goal="Analyze job requirements, calculate match score (0-100%), and identify 3-5 specific skill gaps.",
        backstory=(
            "You are an ATS expert who extracts requirements from job descriptions. "
            "You provide structured analysis: required skills, match percentage, and specific gaps. "
            "You DO NOT rewrite resumes; you provide data for other agents to use."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def create_section_enhancer_agent():
    """Creates the agent that improves resume sections."""
    return Agent(
        role='Resume Content Optimizer',
        goal="Enhance resume sections using STAR method, action verbs, and metrics WITHOUT inventing new skills.",
        backstory=(
            "You are a professional resume writer who strengthens existing content. "
            "CRITICAL RULES: "
            "1. NEVER add technologies or skills not present in the original resume "
            "2. ONLY enhance phrasing, structure, and impact of existing content "
            "3. Use quantifiable metrics where appropriate, but don't fabricate numbers "
            "4. Apply STAR method to existing achievements "
            "If provided with research keywords, incorporate them ONLY if they relate to existing experience."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def create_translation_agent():
    """Creates the agent for resume localization."""
    return Agent(
        role='International Resume Localization Expert',
        goal="Translate and adapt resumes for target countries using local conventions.",
        backstory=(
            "You are a localization expert who adapts resumes for international markets. "
            "You research local hiring customs and translate content while maintaining professional quality."
        ),
        llm=llm,
        tools=[web_search_tool],
        verbose=True,
        allow_delegation=False
    )

def create_synthesizer_agent():
    """Creates the agent that synthesizes all outputs into a final response."""
    return Agent(
        role='Resume Synthesis and Quality Assurance Specialist',
        goal="Synthesize all agent outputs into one coherent, final resume with a clear summary of changes.",
        backstory=(
            "You are the final quality check. Your responsibilities: "
            "1. Receive outputs from all previous agents (research, match scores, gaps, enhanced sections). "
            "2. Intelligently merge these into a single, cohesive final resume. "
            "3. Ensure NO hallucinated skills are added by verifying all changes against the original resume. "
            "4. Provide a clear summary: what changed, why, match score, and skill gaps. "
            "5. Output the final resume in ###UPDATED_RESUME### tags and skill gaps in ###SKILL_GAPS### tags."
        ),
        llm=synthesizer_llm,
        verbose=True,
        allow_delegation=False
    )
