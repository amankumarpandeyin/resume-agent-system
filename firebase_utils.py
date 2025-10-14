# firebase_utils.py - All our Firebase interactions are bundled up in here.
# Keeps the main code clean and lets us talk to the database without clutter.
import uuid
from google.cloud import firestore
from google.api_core.exceptions import NotFound

# Spin up the Firestore client.
# It's smart enough to find the GOOGLE_APPLICATION_CREDENTIALS env var on its own.
db = firestore.Client()

def create_new_conversation():
    """Kicks off a new chat session in Firestore and gives us a unique ID."""
    conversation_id = str(uuid.uuid4())
    conversation_ref = db.collection('conversations').document(conversation_id)
    conversation_ref.set({
        'history': [],
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return conversation_id

def get_conversation_history(conversation_id: str):
    """Grabs the chat history for a given session. No history, no problem - just returns an empty list."""
    try:
        conversation_ref = db.collection('conversations').document(conversation_id)
        doc = conversation_ref.get()
        if doc.exists:
            return doc.to_dict().get('history', [])
        else:
            return []
    except NotFound:
        return []

def update_conversation_history(conversation_id: str, new_entry: dict):
    """Appends a new message to the chat log. Keeps the conversation flowing."""
    conversation_ref = db.collection('conversations').document(conversation_id)
    conversation_ref.update({
        'history': firestore.ArrayUnion([new_entry])
    })

def save_resume_version(conversation_id: str, original_text: str, modified_text: str = None, agent_reasoning: str = ""):
    """
    Saves a snapshot of the resume. This is our version control.
    We find the latest version number and just increment it. Git-like, but simpler.
    """
    # Find the latest version for this convo to figure out the new version number.
    query = db.collection('resumes').where('conversationId', '==', conversation_id).order_by('version', direction=firestore.Query.DESCENDING).limit(1)
    docs = list(query.stream())
    
    new_version = 1
    if docs:
        latest_version = docs[0].to_dict().get('version', 0)
        new_version = latest_version + 1

    resume_doc_ref = db.collection('resumes').document()
    resume_doc_ref.set({
        'conversationId': conversation_id,
        'version': new_version,
        'original_text': original_text,
        'modified_text': modified_text if modified_text is not None else original_text,
        'agent_reasoning': agent_reasoning,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    return new_version

def get_latest_resume(conversation_id: str):
    """Fetches the most recent version of the resume for a given chat. Always gets the latest and greatest."""
    query = db.collection('resumes').where('conversationId', '==', conversation_id).order_by('version', direction=firestore.Query.DESCENDING).limit(1)
    docs = list(query.stream())

    if docs:
        return docs[0].to_dict()
    else:
        return None
