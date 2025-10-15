import os
from langchain_tavily import TavilySearch
from crewai.tools import tool 
from dotenv import load_dotenv

load_dotenv()

# Instantiate the original LangChain tool
tavily_search_instance = TavilySearch(k=3)

# Use the @tool decorator to create a CrewAI-compatible tool.
# The function name 'web_search_tool' becomes the tool itself.
@tool("Tavily Web Search")
def web_search_tool(query: str) -> str:
    """Performs a web search using the Tavily API to find up-to-date information."""
    return tavily_search_instance.invoke({"query": query})

#bye
