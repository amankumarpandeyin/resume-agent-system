# tools.py - The AI's toolkit. This is where we keep the gadgets our agents use to do their jobs.
from crewai_tools import TavilySearchTool

# This is our web search tool. It's how our agents can browse the internet.
# It's powered by Tavily and uses the TAVILY_API_KEY from our .env file.
web_search_tool = TavilySearchTool()
