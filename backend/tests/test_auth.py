import pytest
from app import app
from unittest.mock import MagicMock, patch
from datetime import date

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# register success
@patch('app.get_mysql_connection')
def test_register_success(mock_mysql, client):
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = None
    response = client.post('/api/register', json={"username": "new", "password": "123", "email": "a@b.com"})
    assert response.status_code == 201
# ชื่อซ้ำ
@patch('app.get_mysql_connection')
def test_register_duplicate_username(mock_mysql, client):
  
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"id": 1}
    response = client.post('/api/register', json={"username": "old", "password": "123", "email": "a@b.com"})
    assert response.status_code == 409
# ข้อมูลไม่ครบ
def test_register_missing_fields(client):
    
    response = client.post('/api/register', json={"username": "user"}) 
    assert response.status_code == 400
# login success
@patch('app.get_mysql_connection')
def test_login_success(mock_mysql, client):
    
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"username": "user1", "password": "123"}
    response = client.post('/api/login', json={"username": "user1", "password": "123"})
    assert response.status_code == 200
#login fail
@patch('app.get_mysql_connection')
def test_login_failed(mock_mysql, client):
   
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = None 
    response = client.post('/api/login', json={"username": "u1", "password": "wrong"})
    assert response.status_code == 401
# can play today?(not yet)
@patch('app.get_mysql_connection')
def test_check_play_status_can_play(mock_mysql, client):
    
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"last_play_date": None, "rank": "Bronze"}
    response = client.get('/api/check_play_status/user1')
    assert response.get_json()['can_play'] is True
# can play today?(already)

@patch('app.get_mysql_connection')
def test_check_play_status_already_played(mock_mysql, client):
    
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"last_play_date": date.today(), "rank": "Bronze"}
    response = client.get('/api/check_play_status/user1')
    assert response.get_json()['can_play'] is False