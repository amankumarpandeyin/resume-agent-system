import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import UploadFile, File, Form
from io import BytesIO
from main import app, parse_resume, ChatRequest, ChatResponse
import firebase_utils as db 
client = TestClient(app)
MOCK_RESUME_TEXT = """
John Doe
Software Engineer
Experience:
- Developed AI agents
"""

MOCK_CONVERSATION_ID = "test_conv_123"
MOCK_UPDATED_RESUME = "Updated John Doe Resume"
@patch.object(db, 'create_new_conversation', return_value=MOCK_CONVERSATION_ID)
@patch.object(db, 'save_resume_version', return_value=1)
@patch.object(db, 'get_latest_resume', return_value={
    'modified_text': MOCK_RESUME_TEXT,
    'original_text': MOCK_RESUME_TEXT,
    'version': 1
})
@patch.object(db, 'get_conversation_history', return_value=[])
@patch.object(db, 'update_conversation_history', return_value=None)
def test_upload_success(mock_update_history, mock_get_history, mock_get_resume, mock_save_resume, mock_create_conv):
    """
    Test successful resume upload.
    """
    mock_file_content = b"%PDF-1.4\nmock pdf content"
    file = UploadFile(filename="test.pdf", file=BytesIO(mock_file_content), content_type="application/pdf")

    with patch('main.parse_resume', return_value=MOCK_RESUME_TEXT):
        response = client.post("/upload", files={"file": (file.filename, file.file, file.content_type)})

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == MOCK_CONVERSATION_ID
    assert data["resume_text"] == MOCK_RESUME_TEXT
    assert data["message"] == "Resume uploaded successfully. You can now start chatting."
    mock_create_conv.assert_called_once()
    mock_save_resume.assert_called_once()

def test_upload_invalid_file():
    """
    Test upload with unsupported file type.
    """
    mock_file_content = b"plain text"
    file = UploadFile(filename="test.txt", file=BytesIO(mock_file_content), content_type="text/plain")

    response = client.post("/upload", files={"file": (file.filename, file.file, file.content_type)})

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_upload_no_resume():
    """
    Test upload that fails parsing.
    """
    mock_file_content = b"empty"
    file = UploadFile(filename="test.pdf", file=BytesIO(mock_file_content), content_type="application/pdf")

    with patch('main.parse_resume', return_value=""):
        response = client.post("/upload", files={"file": (file.filename, file.file, file.content_type)})

    assert response.status_code == 400
    assert "Could not extract text from the resume." in response.json()["detail"]

@patch.object(db, 'get_latest_resume', return_value=None)
@patch.object(db, 'get_conversation_history', return_value=[])
@patch.object(db, 'update_conversation_history', return_value=None)
def test_chat_no_resume(mock_update, mock_history, mock_get_resume):
    """
    Test chat without uploaded resume.
    """
    request = ChatRequest(conversation_id=MOCK_CONVERSATION_ID, message="Test message")
    response = client.post("/chat", json=request.dict())

    assert response.status_code == 404
    assert "No resume found for this conversation. Please upload one first." in response.json()["detail"]

@patch('main.create_router_agent')
@patch('main.create_company_researcher_agent')
@patch('main.Crew')
@patch.object(db, 'get_conversation_history', return_value=[])
@patch.object(db, 'update_conversation_history', return_value=None)
@patch.object(db, 'get_latest_resume', return_value={
    'modified_text': MOCK_RESUME_TEXT,
    'original_text': MOCK_RESUME_TEXT
})
@patch.object(db, 'save_resume_version', return_value=2)
def test_chat_company_research(mock_save, mock_get_resume, mock_update, mock_history, mock_crew, mock_company_agent, mock_router_agent):
    """
    Test chat routing to company researcher agent.
    """
    mock_router_agent.return_value = MagicMock()
    mock_router_task = MagicMock()
    mock_router_task.kickoff.return_value = '["company_researcher"]'
    mock_router_agent.create_routing_task.return_value = mock_router_task  # Simplified
    mock_company_crew = MagicMock()
    mock_company_task = MagicMock()
    mock_company_task.kickoff.return_value = (
        "Company research done.\n###UPDATED_RESUME###\n" + MOCK_UPDATED_RESUME
    )
    mock_company_agent.return_value = MagicMock()
    mock_company_agent.create_company_research_task.return_value = mock_company_task
    mock_crew.return_value.kickoff.return_value = mock_company_task.kickoff.return_value

    request = ChatRequest(conversation_id=MOCK_CONVERSATION_ID, message="Optimize for Google")
    response = client.post("/chat", json=request.dict())

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == MOCK_CONVERSATION_ID
    assert "Company research done." in data["agent_response"]
    assert data["updated_resume"] == MOCK_UPDATED_RESUME
    mock_save.assert_called_once()

@patch('main.create_router_agent')
@patch('main.create_job_matcher_agent')
@patch('main.Crew')
@patch.object(db, 'get_conversation_history', return_value=[])
@patch.object(db, 'update_conversation_history', return_value=None)
@patch.object(db, 'get_latest_resume', return_value={
    'modified_text': MOCK_RESUME_TEXT,
    'original_text': MOCK_RESUME_TEXT
})
@patch.object(db, 'save_resume_version', return_value=2)
def test_chat_job_matcher_with_score(mock_save, mock_get_resume, mock_update, mock_history, mock_crew, mock_job_agent, mock_router_agent):
    """
    Test chat routing to job matcher with score and gaps.
    """
    mock_router_agent.return_value = MagicMock()
    mock_router_task = MagicMock()
    mock_router_task.kickoff.return_value = '["job_matcher"]'
    mock_router_agent.create_routing_task.return_value = mock_router_task
    mock_result = (
        "Match score: 85%. Gaps identified.\n"
        "###SKILL_GAPS###\n- Gap 1: Learn AWS\n- Gap 2: Improve Python\n"
        "###UPDATED_RESUME###\n" + MOCK_UPDATED_RESUME
    )
    mock_job_task = MagicMock()
    mock_job_task.kickoff.return_value = mock_result
    mock_job_agent.return_value = MagicMock()
    mock_job_agent.create_job_matching_task.return_value = mock_job_task
    mock_crew.return_value.kickoff.return_value = mock_result

    request = ChatRequest(conversation_id=MOCK_CONVERSATION_ID, message="Match this JD: Senior AI Engineer")
    response = client.post("/chat", json=request.dict())

    assert response.status_code == 200
    data = response.json()
    assert data["match_score"] == 85.0
    assert len(data["skill_gaps"]) == 2
    assert "Gap 1" in data["skill_gaps"][0]
    assert data["updated_resume"] == MOCK_UPDATED_RESUME

@patch('main.create_router_agent')
@patch('main.create_translation_agent')
@patch('main.Crew')
@patch.object(db, 'get_conversation_history', return_value=[])
@patch.object(db, 'update_conversation_history', return_value=None)
@patch.object(db, 'get_latest_resume', return_value={
    'modified_text': MOCK_RESUME_TEXT,
    'original_text': MOCK_RESUME_TEXT
})
@patch.object(db, 'save_resume_version', return_value=2)
def test_chat_translation(mock_save, mock_get_resume, mock_update, mock_history, mock_crew, mock_trans_agent, mock_router_agent):
    """
    Test chat routing to translation agent.
    """
    mock_router_agent.return_value = MagicMock()
    mock_router_task = MagicMock()
    mock_router_task.kickoff.return_value = '["translation"]'
    mock_router_agent.create_routing_task.return_value = mock_router_task

    mock_trans_result = (
        "Translated to Spanish with Mexican adaptations.\n###UPDATED_RESUME###\n" + MOCK_UPDATED_RESUME
    )
    mock_trans_task = MagicMock()
    mock_trans_task.kickoff.return_value = mock_trans_result
    mock_trans_agent.return_value = MagicMock()
    mock_trans_agent.create_translation_task.return_value = mock_trans_task
    mock_crew.return_value.kickoff.return_value = mock_trans_result

    request = ChatRequest(conversation_id=MOCK_CONVERSATION_ID, message="Translate to Spanish for Mexico")
    response = client.post("/chat", json=request.dict())

    assert response.status_code == 200
    data = response.json()
    assert "Translated to Spanish" in data["agent_response"]
    assert data["updated_resume"] == MOCK_UPDATED_RESUME

@patch('main.create_router_agent')
@patch('main.Crew')
@patch.object(db, 'get_conversation_history', return_value=[])
@patch.object(db, 'update_conversation_history', return_value=None)
@patch.object(db, 'get_latest_resume', return_value={
    'modified_text': MOCK_RESUME_TEXT,
    'original_text': MOCK_RESUME_TEXT
})
def test_chat_general_chitchat(mock_update, mock_history, mock_get_resume, mock_crew, mock_router_agent):
    """
    Test fallback to general chit-chat.
    """
    mock_router_agent.return_value = MagicMock()
    mock_router_task = MagicMock()
    mock_router_task.kickoff.return_value = '["general_chitchat"]'
    mock_router_agent.create_routing_task.return_value = mock_router_task

    request = ChatRequest(conversation_id=MOCK_CONVERSATION_ID, message="Hello, how are you?")
    response = client.post("/chat", json=request.dict())

    assert response.status_code == 200
    data = response.json()
    assert "specialized resume assistant" in data["agent_response"]
    assert data["updated_resume"] == MOCK_RESUME_TEXT  # No change

@patch.object(db, 'collection')
def test_get_versions(mock_collection):
    """
    Test GET /versions endpoint.
    """
    mock_query = MagicMock()
    mock_stream = MagicMock()
    mock_doc1 = MagicMock()
    mock_doc1.to_dict.return_value = {'version': 1, 'modified_text': MOCK_RESUME_TEXT}
    mock_stream.stream.return_value = [mock_doc1]
    mock_query.stream.return_value = mock_stream
    mock_collection.return_value.where.return_value.order_by.return_value.limit.return_value = mock_query

    response = client.get(f"/versions/{MOCK_CONVERSATION_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version"] == 1

@patch.object(db, 'collection')
def test_revert_version(mock_collection):
    """
    Test POST /revert endpoint success.
    """
    mock_target_query = MagicMock()
    mock_target_stream = MagicMock()
    mock_target_doc = MagicMock()
    mock_target_doc.to_dict.return_value = {'version': 1, 'modified_text': MOCK_RESUME_TEXT}
    mock_target_stream.stream.return_value = [mock_target_doc]
    mock_target_query.stream.return_value = mock_target_stream

    with patch.object(db, 'save_resume_version') as mock_save:
        mock_collection.return_value.where.return_value.where.return_value = mock_target_query

        response = client.post(f"/revert/{MOCK_CONVERSATION_ID}/1")

    assert response.status_code == 200
    data = response.json()
    assert f"Reverted to version 1" in data["message"]
    assert data["resume"] == MOCK_RESUME_TEXT
    mock_save.assert_called_once()

@patch.object(db, 'collection')
def test_revert_version_not_found(mock_collection):
    """
    Test POST /revert with invalid version.
    """
    mock_query = MagicMock()
    mock_stream = MagicMock()
    mock_stream.stream.return_value = []
    mock_query.stream.return_value = mock_stream
    mock_collection.return_value.where.return_value.where.return_value = mock_query

    response = client.post(f"/revert/{MOCK_CONVERSATION_ID}/999")

    assert response.status_code == 404
    assert "Version not found." in response.json()["detail"]