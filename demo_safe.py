#!/usr/bin/env python3
"""
Token-efficient demo script for smooth presentation
This uses minimal tokens to avoid rate limits during demos
"""

import os
import time
from dotenv import load_dotenv
from crewai import Crew, Process, Agent, Task
from langchain_groq import ChatGroq
from tools import web_search_tool

load_dotenv()

# Initialize LLM
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="groq/llama-3.1-8b-instant"
)

def demo_1_router():
    """Demo 1: Show intelligent routing"""
    print("\n" + "="*80)
    print("DEMO 1: Intelligent Query Routing")
    print("="*80)
    
    router = Agent(
        role='Router',
        goal='Analyze query and output JSON array of agents',
        backstory='You output ONLY JSON arrays like ["job_matcher"] or ["company_researcher", "section_enhancer"]',
        llm=llm,
        verbose=False
    )
    
    test_queries = [
        "Make my resume better for AI Engineer at Google",
        "Translate my resume to German",
        "Improve my projects section"
    ]
    
    for query in test_queries:
        task = Task(
            description=f'Route this query: "{query}"\nOutput ONLY a JSON array.',
            agent=router,
            expected_output='JSON array'
        )
        
        try:
            result = Crew(agents=[router], tasks=[task], verbose=False).kickoff()
            print(f"Query: {query}")
            print(f"→ Routes to: {result}")
            print()
            time.sleep(2)  # Prevent rate limit
        except Exception as e:
            print(f"Error: {e}")

def demo_2_web_search():
    """Demo 2: Show web search capability (token-efficient)"""
    print("\n" + "="*80)
    print("DEMO 2: Company Research with Web Search")
    print("="*80)
    
    researcher = Agent(
        role='Researcher',
        goal='Find company info using ONE web search',
        backstory='You search once and report findings concisely.',
        tools=[web_search_tool],
        llm=llm,
        verbose=False
    )
    
    task = Task(
        description='Search for "VectorShift company mission" and report 3 key findings in under 50 words.',
        agent=researcher,
        expected_output='3 bullet points'
    )
    
    try:
        print("Searching for VectorShift company information...")
        result = Crew(agents=[researcher], tasks=[task], verbose=True).kickoff()
        print(f"\nFindings:\n{result}")
    except Exception as e:
        print(f"Error: {e}")
        print("Tip: Wait 10 seconds and try again if rate limited")

def demo_3_section_enhancement():
    """Demo 3: Show resume enhancement WITHOUT web search"""
    print("\n" + "="*80)
    print("DEMO 3: Resume Section Enhancement (No Web Search)")
    print("="*80)
    
    enhancer = Agent(
        role='Resume Writer',
        goal='Improve ONE bullet point using STAR method',
        backstory='You enhance existing content without adding new skills.',
        llm=llm,
        verbose=False
    )
    
    original = "• Worked on data pipelines for AI systems"
    
    task = Task(
        description=f'Improve this ONE bullet point:\n{original}\n\nMake it more impactful. Output ONLY the improved version in under 30 words.',
        agent=enhancer,
        expected_output='One improved bullet point'
    )
    
    try:
        print(f"Original: {original}")
        result = Crew(agents=[enhancer], tasks=[task], verbose=False).kickoff()
        print(f"Enhanced: {result}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all demos with safety checks"""
    print("\n╔" + "="*78 + "╗")
    print("║" + " "*25 + "SAFE DEMO MODE" + " "*38 + "║")
    print("║" + " Token-Efficient Tests for Smooth Presentation" + " "*31 + "║")
    print("╚" + "="*78 + "╝\n")
    
    demos = [
        ("Router Demo", demo_1_router),
        ("Web Search Demo", demo_2_web_search),
        ("Enhancement Demo", demo_3_section_enhancement)
    ]
    
    for name, demo_func in demos:
        try:
            demo_func()
            print(f"\n✅ {name} completed")
            print("⏳ Waiting 5 seconds before next demo...")
            time.sleep(5)
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            print("Continuing to next demo...\n")
    
    print("\n🎉 Demo complete!")
    print("\n💡 For full system demo, use the FastAPI server:")
    print("   uvicorn main:app --reload")

if __name__ == "__main__":
    main()