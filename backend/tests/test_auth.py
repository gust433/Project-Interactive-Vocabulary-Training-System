import pytest
import bcrypt
import jwt
from app import app
from unittest.mock import MagicMock, patch
from datetime import date

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'fdslkfjsdlkufewhjroiewurewrewqwe' 
    
    with app.test_client() as client:
        yield client

# --- Auth Tests ---
@patch('app.get_mysql_connection')
def test_register_success(mock_mysql, client):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = None
    response = client.post('/api/register', json={"username": "new", "password": "1", "email": "n@m.com"})
    assert response.status_code == 201

@patch('app.get_mysql_connection')
def test_register_duplicate(mock_mysql, client):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"id": 1}
    response = client.post('/api/register', json={"username": "old", "password": "1", "email": "o@m.com"})
    assert response.status_code == 409

def test_register_missing(client):
    response = client.post('/api/register', json={"username": "u"})
    assert response.status_code == 400

@patch('app.get_mysql_connection')
def test_login_success(mock_mysql, client):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    
    hashed_password = bcrypt.hashpw(b"123", bcrypt.gensalt()).decode('utf-8')
    mock_cursor.fetchone.return_value = {"username": "u1", "password": hashed_password}
    
    response = client.post('/api/login', json={"username": "u1", "password": "123"})
    assert response.status_code == 200

@patch('app.get_mysql_connection')
def test_login_fail(mock_mysql, client):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = None
    response = client.post('/api/login', json={"username": "u", "password": "p"})
    assert response.status_code == 401

@patch('app.get_mysql_connection')
def test_status_can_play(mock_mysql, client):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"last_play_date": None, "rank": "Bronze"}
    
    token = jwt.encode({"sub": "u1", "username": "u1"}, app.config['SECRET_KEY'], algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
        
    response = client.get('/api/check_play_status/u1', headers=headers)
    
    assert response.status_code == 200, f"API Error: {response.get_json()}"
    assert response.get_json()['can_play'] is True

# แก้ไขใน test_status_played
@patch('app.get_mysql_connection')
def test_status_played(mock_mysql, client):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"last_play_date": date.today(), "rank": "Bronze"}
    
    token = jwt.encode({"sub": "u1", "username": "u1"}, app.config['SECRET_KEY'], algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
        
    response = client.get('/api/check_play_status/u1', headers=headers)
    
    assert response.status_code == 200, f"API Error: {response.get_json()}"
    assert response.get_json()['can_play'] is False
