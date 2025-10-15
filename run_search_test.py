import os
import time
from dotenv import load_dotenv
from crewai import Crew, Process
from agents import create_company_researcher_agent
from tasks import create_company_research_task
from litellm.exceptions import RateLimitError

# Load environment variables
load_dotenv()

# --- Test Configuration ---
sample_query = "Research VectorShift's company values"
sample_resume = """
AMAN KUMAR PANDEY
India | +91-8081525720 | aman0hata@gmail.com
---
PROFESSIONAL SUMMARY
Engineer specializing in Python-first LLM integrations, RAG, and agentic workflows.
"""

def run_test_with_retry(max_retries=3):
    """Run the test with automatic retry on rate limits"""
    
    for attempt in range(max_retries):
        try:
            print(f"\n🚀 Attempt {attempt + 1}/{max_retries}: Starting Web Search Test...")
            
            # Add delay between attempts
            if attempt > 0:
                wait_time = 10 + (attempt * 5)  # Progressive backoff
                print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            
            # Create the Agent
            researcher_agent = create_company_researcher_agent()
            
            # Create the Task with shorter, simpler query
            research_task = create_company_research_task(
                researcher_agent, 
                sample_query, 
                sample_resume
            )
            
            # Create the Crew
            crew = Crew(
                agents=[researcher_agent],
                tasks=[research_task],
                process=Process.sequential,
                verbose=True
            )
            
            # Run the Crew
            result = crew.kickoff()
            
            print("\n\n✅ Web Search Test Complete!")
            print("=" * 80)
            print("AGENT FINAL ANSWER:")
            print("=" * 80)
            print(result)
            print("=" * 80)
            
            return True
            
        except RateLimitError as e:
            error_msg = str(e)
            
            # Extract wait time from error
            wait_time = 15
            if "Please try again in" in error_msg:
                try:
                    wait_str = error_msg.split("Please try again in ")[1].split("s")[0]
                    wait_time = float(wait_str) + 2
                except:
                    pass
            
            print(f"\n⚠️  Rate Limit Hit!")
            print(f"   Used: ~4000-6000 tokens")
            print(f"   Limit: 6000 TPM on free tier")
            
            if attempt < max_retries - 1:
                print(f"   → Retrying in {wait_time:.0f} seconds...")
            else:
                print(f"\n❌ Failed after {max_retries} attempts")
                print("\n💡 Solutions:")
                print("   1. Wait 60 seconds and try again")
                print("   2. Upgrade to Groq Dev Tier (higher limits)")
                print("   3. Use a simpler/shorter test query")
                raise
                
        except Exception as e:
            print(f"\n❌ Unexpected error: {type(e).__name__}")
            print(f"   {str(e)}")
            raise
    
    return False

if __name__ == "__main__":
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "VECTORSHIFT COMPANY RESEARCH TEST" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")
    
    success = run_test_with_retry(max_retries=3)
    
    if success:
        print("\n🎉 Test passed successfully!")
    else:
        print("\n😔 Test failed - please check the errors above")