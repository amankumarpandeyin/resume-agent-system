from crewai import Task
import json


def create_routing_task(agent, user_query, history):
    """Creates the task for the router agent to classify the user's query."""
    history_str = '\n'.join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in history])
    return Task(
        description=(
            f"Analyze the user's query and conversation history to determine the right agent sequence. "
            "Available agents: 'company_researcher', 'job_matcher', 'section_enhancer', 'translation', 'general_chitchat'.\n\n"
            f"USER QUERY: {user_query}\n"
            f"CONVERSATION HISTORY: {history_str}\n\n"
            "Your output MUST be a valid JSON array of agent keywords in the correct order. "
            "Example: [\"company_researcher\", \"job_matcher\"]. For a single agent: [\"job_matcher\"]."
        ),
        agent=agent,
        expected_output="A JSON array of agent keywords, like [\"job_matcher\"]."
    )

# --- MISSING FUNCTION TO ADD ---
def create_task(description: str, agent, expected_output: str):
    """A generic function to create any task."""
    return Task(description=description, agent=agent, expected_output=expected_output)
def create_company_research_task(agent, query, resume):
    return Task(
        description=f"""
        A user wants to optimize their resume for a specific company based on this query: '{query}'.

        Your task is to:
        1. Use your web search tool to thoroughly research the company mentioned in the query.
           Focus on its culture, core values, mission, recent news, and the technologies it uses.
        2. Analyze the provided resume below and compare it against your research findings.
        3. Based on your analysis, provide a brief summary of your findings and strategic advice
           on how the user should align their resume. Do not rewrite the resume yourself.

        USER'S RESUME:
        ---
        {resume}
        ---
        """,
        agent=agent,
        expected_output="A summary of your research findings and 3-5 actionable recommendations for resume alignment."
    )

def create_job_matching_task(agent, resume_text, user_query):
    return Task(
        description=(
            f"A user wants to tailor their resume to a job description provided in their query: '{user_query}'.\n"
            f"1. Analyze the job description and the resume:\n---RESUME---\n{resume_text}\n---\n"
            f"2. Rewrite the resume to be a perfect match.\n"
            f"3. Calculate a match score (0-100%) and list 3-5 skill gaps.\n"
            f"4. Your output must contain your analysis, then a list of skill gaps inside '###SKILL_GAPS###' tags, "
            f"and finally the full updated resume inside '###UPDATED_RESUME###' tags."
        ),
        agent=agent,
        expected_output="An explanation with a score, a list of skill gaps, and the full updated resume."
    )
def create_section_enhancement_task(agent, resume_text, user_query):
    return Task(
        description=(
            f"A user wants to improve a specific resume section based on their query: '{user_query}'.\n"
            f"1. Identify the target section.\n"
            f"2. Analyze the section within the full resume:\n---RESUME---\n{resume_text}\n---\n"
            f"3. Rewrite only the target section using action verbs, metrics, and the STAR method.\n"
            f"4. Explain the improvements, then provide the full updated resume in '###UPDATED_RESUME###' tags."
        ),
        agent=agent,
        expected_output="An explanation of changes, followed by the full updated resume."
    )

def create_translation_task(agent, resume_text, user_query):
    return Task(
        description=(
            f"A user wants to translate their resume based on the query: '{user_query}'.\n"
            f"1. Identify the target language and country.\n"
            f"2. Research local hiring conventions for that country.\n"
            f"3. Translate and adapt the resume:\n---RESUME---\n{resume_text}\n---\n"
            f"4. Explain your localization choices, then provide the full translated resume in '###UPDATED_RESUME###' tags."
        ),
        agent=agent,
        expected_output="An explanation of localization choices, followed by the full updated resume."
    )
