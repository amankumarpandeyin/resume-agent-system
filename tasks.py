from crewai import Task
import json

def create_routing_task(agent, user_query, history):
    """
    This task is for the router agent. It's the first step in any user interaction.
    The goal is to look at the user's message and the chat history, and then decide
    which agent or sequence of agents should take it from here. The output is a clean
    JSON list of agent names. No fluff.
    """
    # We're just formatting the history into a clean string for the LLM...
    history_str = '\n'.join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in history]) if history else "No history yet."
    
    return Task(
        description=(
            f"Analyze the user's query and the conversation history to determine the right agent sequence. "
            "Here are the available agents:\n"
            "- 'company_researcher': For digging into a specific company.\n"
            "- 'job_matcher': When a job description is involved.\n"
            "- 'section_enhancer': For tweaking a specific part of the resume.\n"
            "- 'translation': For language and localization stuff.\n"
            "- 'general_chitchat': For anything that's not about resumes.\n\n"
            f"USER QUERY: {user_query}\n"
            f"CONVERSATION HISTORY: {history_str}\n\n"
            "Your output MUST be a valid JSON array of agent keywords in the correct order. "
            "For example: [\"company_researcher\", \"job_matcher\"]. For a single agent, just one in the list: [\"job_matcher\"]."
        ),
        agent=agent,
        expected_output="A JSON array of agent keywords, like [\"job_matcher\"].",
        context={"query": user_query, "history": history}
    )

def create_company_research_task(agent, resume_text, user_query):
    """
    This task sends the Company Researcher agent on a mission to become an expert
    on a company and then tailor the resume to match. It's all about alignment.
    """
    return Task(
        description=(
            "The user wants to optimize their resume for a specific company. Here's the plan:\n"
            "1. Pinpoint the company name from the user's query: '{query}'.\n"
            "2. Hit the web and research the company's culture, values, and tech stack.\n"
            "3. Read the user's current resume: \n---RESUME---\n{resume}\n---\n"
            "4. Rewrite the resume. Weave in the keywords, tone, and values you found. Focus on the summary, experience, and skills.\n"
            "5. Your final output has two parts:\n"
            "   - First, explain what you changed and why it makes the resume a better fit for the company.\n"
            "   - Second, the full, updated resume, wrapped in '###UPDATED_RESUME###' tags."
        ),
        agent=agent,
        expected_output="An explanation of the changes, followed by the full updated resume inside '###UPDATED_RESUME###' tags.",
        context={"resume": resume_text, "query": user_query}
    )

def create_job_matching_task(agent, resume_text, user_query):
    """
    This is the task for the Job Matcher agent. It's a head-to-head comparison
    between the resume and a job description, with the goal of making the resume
    an undeniable match. This one is data-driven, with a match score and skill gaps.
    """
    return Task(
        description=(
            "The user wants to tailor their resume to a job description. Let's get it done:\n"
            "1. Deep-dive into the job description from the user's query: '{query}'. Understand the core requirements.\n"
            "2. Analyze the current resume: \n---RESUME---\n{resume}\n---\n"
            "3. Compare the two. Find the gaps and the opportunities.\n"
            "4. Rewrite the resume to be a perfect match. Reorder points, inject keywords, and sharpen the summary.\n"
            "5. Calculate a match score (0-100%) and explain how you got it.\n"
            "6. List 3-5 specific skill gaps and suggest how to fix them.\n"
            "7. Your final output has three parts, in this order:\n"
            "   - First, your analysis: the changes, the score, and the gaps.\n"
            "   - Second, a bulleted list of skill gaps, wrapped in '###SKILL_GAPS###' tags.\n"
            "   - Third, the full, updated resume, wrapped in '###UPDATED_RESUME###' tags."
        ),
        agent=agent,
        expected_output="Explanation with score, then the skill gaps list in '###SKILL_GAPS###', then the updated resume in '###UPDATED_RESUME###'.",
        context={"resume": resume_text, "query": user_query}
    )

def create_section_enhancement_task(agent, resume_text, user_query):
    """
    This task is for the Section Enhancer agent. It's a focused mission to
    level up a specific part of the resume using proven writing techniques.
    """
    return Task(
        description=(
            "The user wants to punch up a specific section of their resume. Here's the mission:\n"
            "1. Figure out which section they're talking about from their query: '{query}'.\n"
            "2. Analyze that section in the context of the full resume: \n---RESUME---\n{resume}\n---\n"
            "3. Rewrite only that section. Use action verbs, add metrics (even if you have to suggest placeholders like '[Increased by X%]'), and apply the STAR method.\n"
            "4. Put the full resume back together with the new and improved section.\n"
            "5. Your final output has two parts:\n"
            "   - First, explain the improvements you made and why they're more effective.\n"
            "   - Second, the full, updated resume, wrapped in '###UPDATED_RESUME###' tags."
        ),
        agent=agent,
        expected_output="An explanation of the changes, followed by the full updated resume inside '###UPDATED_RESUME###' tags.",
        context={"resume": resume_text, "query": user_query}
    )

def create_translation_task(agent, resume_text, user_query):
    """
    This task is for the Translation agent. It's not just about swapping words;
    it's about adapting the entire resume for a new cultural and professional context.
    """
    return Task(
        description=(
            "The user needs their resume translated and localized. Here's the game plan:\n"
            "1. Identify the target language and country from the user's query: '{query}'.\n"
            "2. Use your search tool to learn about the local hiring scene. What are the resume conventions in that market?\n"
            "3. Translate the whole resume. Keep it professional.\n"
            "4. Adapt the content and format based on your research. This could mean changing the tone, reordering sections, or adding local keywords.\n"
            "5. Here's the original resume for context: \n---RESUME---\n{resume}\n---\n"
            "6. Your final output has two parts:\n"
            "   - First, explain your translation and localization choices. Why did you make them?\n"
            "   - Second, the full, updated resume in the target language, wrapped in '###UPDATED_RESUME###' tags."
        ),
        agent=agent,
        expected_output="An explanation of the changes, followed by the full updated resume inside '###UPDATED_RESUME###' tags.",
        context={"resume": resume_text, "query": user_query}
    )
