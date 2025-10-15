import os
from dotenv import load_dotenv

# Yo, this is the config file. It's where we stash all our secrets and settings.
# We're using dotenv to load up environment variables from a .env file. Keep your keys out of the code, people.
load_dotenv()

# --- API Keys ---
# All the secret sauce for the services we're hitting.
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # For that sweet, sweet Groq speed.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") # For when our agents need to browse the web.

# --- Firebase Config ---
# Your Firebase project ID goes here.
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID") 

# Heads up: For Firebase to work, you need a service account.
# Set the GOOGLE_APPLICATION_CREDENTIALS env var to point to your service account JSON file.
# Our firebase_utils.py script is smart enough to find it from there.

# --- LLM Config ---
# We're rolling with Groq 'cause it's fast as hell.
# IMPORTANT: Groq models need the 'groq/' prefix for LiteLLM to recognize them
# Using Llama 3.1 8B Instant - blazing fast at 560 tokens/sec
LLM_MODEL_NAME = 'groq/llama-3.1-8b-instant'

# --- Agent Config ---
# The router agent gets its own model config, 'cause it needs to be extra quick.
ROUTER_MODEL_NAME = 'groq/llama-3.1-8b-instant'

# Synthesizer uses same model for now
SYNTHESIZER_MODEL_NAME = 'groq/llama-3.1-8b-instant'
