# agents.py - This is where we build our crew of AI agents. Each one is a specialist
from crewai import Agent
from langchain_groq import ChatGroq
from tools import web_search_tool
from config import LLM_MODEL_NAME, ROUTER_MODEL_NAME

# Setting up the LLM. Groq is sick, the response times are insane
llm = ChatGroq(
    model_name=LLM_MODEL_NAME,
    temperature=0, # We want deterministic outputs, no creative writing here
    max_tokens=4096,
)

# A leaner model for the router. Speed is the name of the game.
router_llm = ChatGroq(
    model_name=ROUTER_MODEL_NAME,
    temperature=0,
    max_tokens=512
)

# --- AGENT BLUEPRINTS ---
# This is where we define the personalities and jobs of our AI agents

def create_router_agent():
    """
    This agent is the bouncer of our club. It checks the user's ID (their message)
    and decides which specialist agent gets to handle the request. It's all about
    making sure the right AI is on the right job.
    """
    return Agent(
        role='Conversation Router',
        goal=(
            "Figure out what the user wants and chain the right agents to get it done. "
            "Your output is a JSON list of agent names. Simple. "
            "e.g., ['company_researcher', 'job_matcher']"
        ),
        backstory=(
            "You're the quarterback of this AI team. You see the whole field, read the user's intent, "
            "and call the play. You don't do the work, you delegate it. Your only job is to "
            "output a clean JSON array of the agents needed for the task. Nothing more, nothing less."
        ),
        llm=router_llm,
        verbose=True,
        allow_delegation=False # This agent doesn't ask for help, it gives orders
    )

def create_company_researcher_agent():
    """
    This agent is our corporate spy. It digs up intel on companies—culture, values, tech stack,
    you name it. Then it rewrites the resume to make the user look like the perfect candidate.
    """
    return Agent(
        role='Corporate Intel and Resume Aligner',
        goal=(
            "Scour the web for intel on a target company, then surgically rewrite the user's "
            "resume to match their vibe and needs. You need to explain your changes, so the user knows you're not just making stuff up."
        ),
        backstory=(
            "You're a digital chameleon. You can blend into any corporate culture by analyzing their public footprint. "
            "You read between the lines of mission statements and engineering blogs to find what they *really* want. "
            "Then you make the user's resume a mirror image of that desire."
        ),
        llm=llm,
        tools=[web_search_tool], # Can't be a spy without your gadgets.
        verbose=True
    )

def create_job_matcher_agent():
    """
    This is our ATS-killer. It takes a job description and a resume, and makes them
    best friends. It's all about keyword optimization and highlighting the right experiences.
    """
    return Agent(
        role='Job Description Demystifier',
        goal=(
            "Take a job description, rip it apart, and rebuild the user's resume to be its perfect match. "
            "You're not just matching keywords, you're aligning narratives. "
            "Give a match score and point out the gaps. Brutal honesty is key."
        ),
        backstory=(
            "You're the ultimate cheat code for job applications. You think like an Applicant Tracking System (ATS), "
            "but you have the strategic mind of a top-tier recruiter. You see the matrix of a job description "
            "and know exactly how to plug the resume in for maximum impact."
        ),
        llm=llm,
        verbose=True
    )

def create_section_enhancer_agent():
    """

    This agent is a resume wordsmith. It takes a specific section and gives it a glow-up,
    turning boring descriptions into high-impact achievement statements.
    """
    return Agent(
        role='Resume Wordsmith',
        goal=(
            "Take a dull resume section and make it shine. Use action verbs, quantify everything, "
            "and use the STAR method like it's second nature. Explain your edits so the user learns something."
        ),
        backstory=(
            "You're a resume writing prodigy. You can turn a list of duties into a highlight reel of achievements. "
            "You live by the mantra 'show, don't tell'. Every bullet point you write is a testament to the candidate's value."
        ),
        llm=llm,
        verbose=True
    )

def create_translation_agent():
    """
    Our polyglot agent. It doesn't just translate; it localizes. It knows that a resume
    for a job in Berlin is different from one for a job in Tokyo.
    """
    return Agent(
        role='Global Resume Localizer',
        goal=(
            "Translate a resume and adapt it to the cultural and professional norms of a specific country. "
            "This isn't just about language; it's about format, tone, and what's valued in that market. "
            "Explain your localization choices."
        ),
        backstory=(
            "You're a globetrotting career coach who's fluent in both languages and cultures. "
            "You know that a direct translation is a rookie mistake. You adapt the resume to make it "
            "feel native, not just translated. You're the difference between a tourist and a local."
        ),
        llm=llm,
        tools=[web_search_tool],
        verbose=True
    )
