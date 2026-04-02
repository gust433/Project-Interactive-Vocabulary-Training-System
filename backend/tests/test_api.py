import pytest
import jwt
from app import app
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'fdslkfjsdlkufewhjroiewurewrewqwe' 
    with app.test_client() as client:
        yield client

@pytest.fixture
def token_headers():
    token = jwt.encode({"sub": "testuser", "username": "testuser"}, app.config['SECRET_KEY'], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

# --- API Tests ---

@patch('app.db')
def test_get_word_success(mock_db, client, token_headers):
    mock_db["words"].aggregate.side_effect = [[{"eng":"A","thai":"ก"}], [{"thai":"ข"},{"thai":"ค"},{"thai":"ง"}]]
    res = client.get('/api/get_word', headers=token_headers)
    assert res.status_code == 200

@patch('app.db')
def test_get_my_dict_success(mock_db, client, token_headers):
    mock_db["user_dict"].find.return_value = [{"_id":"1","vocab":"A","meaning":"ก"}]
    res = client.get('/api/mydict/testuser', headers=token_headers)
    assert res.status_code == 200

@patch('app.db')
def test_save_word_success(mock_db, client, token_headers):
    mock_db["user_dict"].find_one.return_value = None
    res = client.post('/api/save_word', json={"username":"testuser","vocab":"A","meaning":"ก"}, headers=token_headers)
    assert res.status_code == 200

@patch('app.db')
def test_save_word_duplicate(mock_db, client, token_headers):
    mock_db["user_dict"].find_one.return_value = {"vocab":"A"}
    res = client.post('/api/save_word', json={"username":"testuser","vocab":"A","meaning":"ก"}, headers=token_headers)
    assert res.status_code == 400

@patch('app.db')
def test_update_note_success(mock_db, client, token_headers):
    mock_db["user_dict"].find_one.return_value = {"_id": "65e123456789012345678901", "username": "testuser"}
    
    mock_db["user_dict"].update_one.return_value.matched_count = 1
    
    res = client.post('/api/save_note/65e123456789012345678901', json={"note":"n"}, headers=token_headers)
    assert res.status_code == 200

@patch('app.db')
def test_delete_word_success(mock_db, client, token_headers):
    mock_db["user_dict"].find_one.return_value = {"_id": "65e123456789012345678901", "username": "testuser"}
    
    mock_db["user_dict"].delete_one.return_value.deleted_count = 1
    
    res = client.delete('/api/mydict/65e123456789012345678901', headers=token_headers)
    assert res.status_code == 200

@patch('app.get_mysql_connection')
def test_update_score_and_rank(mock_mysql, client, token_headers):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"score": 240, "last_play_date": None}
    
    res = client.post('/api/update_score', json={"username":"testuser", "score":10}, headers=token_headers)
    
    assert res.status_code == 200, f"API Error: {res.get_json()}"
    assert res.get_json()['new_rank'] == 'Gold 🥇'

@patch('app.get_mysql_connection')
def test_get_leaderboard_success(mock_mysql, client, token_headers):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchall.return_value = [{"username":"t1","score":10}]
    res = client.get('/api/leaderboard', headers=token_headers)
    assert res.status_code == 200