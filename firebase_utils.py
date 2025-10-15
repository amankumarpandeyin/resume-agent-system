# firebase_utils.py
import uuid
from google.cloud import firestore

db = firestore.Client()

def create_new_conversation():
    conversation_id = str(uuid.uuid4())
    conversation_ref = db.collection('conversations').document(conversation_id)
    conversation_ref.set({'history': [], 'created_at': firestore.SERVER_TIMESTAMP})
    return conversation_id

def get_conversation_history(conversation_id: str):
    doc = db.collection('conversations').document(conversation_id).get()
    return doc.to_dict().get('history', []) if doc.exists else []

def update_conversation_history(conversation_id: str, new_entry: dict):
    db.collection('conversations').document(conversation_id).update({
        'history': firestore.ArrayUnion([new_entry])
    })

def save_resume_version(conversation_id: str, original_text: str, modified_text: str = None, agent_reasoning: str = ""):
    query = db.collection('resumes').where('conversationId', '==', conversation_id).order_by('version', direction=firestore.Query.DESCENDING).limit(1)
    docs = list(query.stream())
    new_version = docs[0].to_dict().get('version', 0) + 1 if docs else 1
    
    db.collection('resumes').document().set({
        'conversationId': conversation_id,
        'version': new_version,
        'original_text': original_text,
        'modified_text': modified_text if modified_text is not None else original_text,
        'agent_reasoning': agent_reasoning,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    return new_version

def get_latest_resume(conversation_id: str):
    query = db.collection('resumes').where('conversationId', '==', conversation_id).order_by('version', direction=firestore.Query.DESCENDING).limit(1)
    docs = list(query.stream())
    return docs[0].to_dict() if docs else None

# --- NEW FUNCTIONS TO FIX ERROR 1 ---
def get_all_resume_versions(conversation_id: str):
    query = db.collection('resumes').where('conversationId', '==', conversation_id).order_by('version')
    return [doc.to_dict() for doc in query.stream()]

def revert_to_version(conversation_id: str, version: int):
    query = db.collection('resumes').where('conversationId', '==', conversation_id).where('version', '==', version).limit(1)
    docs = list(query.stream())
    if not docs: return None

    version_to_revert = docs[0].to_dict()
    first_version_query = db.collection('resumes').where('conversationId', '==', conversation_id).order_by('version').limit(1)
    original_text = list(first_version_query.stream())[0].to_dict().get('original_text', '')

    save_resume_version(
        conversation_id=conversation_id,
        original_text=original_text,
        modified_text=version_to_revert.get('modified_text'),
        agent_reasoning=f"Reverted to version {version}."
    )
    return get_latest_resume(conversation_id)
