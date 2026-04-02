import pytest
from app import app
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


"""1. สุ่มคำถามสำเร็จ"""
@patch('app.db')
def test_get_word_success(mock_db, client):
    
    mock_db["words"].aggregate.side_effect = [[{"eng": "Run", "thai": "วิ่ง"}], [{"thai": "a"}, {"thai": "b"}, {"thai": "c"}]]
    response = client.get('/api/get_word')
    assert response.status_code == 200
    assert "word" in response.get_json()

"""2. ดึงคลังคำศัพท์ส่วนตัว"""
@patch('app.db')
def test_get_my_dict_success(mock_db, client):
    
    mock_db["user_dict"].find.return_value = [{"_id": "123", "vocab": "Apple", "meaning": "แอปเปิ้ล"}]
    response = client.get('/api/mydict/user1')
    assert response.status_code == 200

"""3. บันทึกคำศัพท์ใหม่สำเร็จ"""
@patch('app.db')
def test_save_word_success(mock_db, client):
    
    mock_db["user_dict"].find_one.return_value = None
    response = client.post('/api/save_word', json={"username": "u1", "vocab": "Cat", "meaning": "แมว"})
    assert response.status_code == 200

"""4. บันทึกคำศัพท์เดิมซ้ำ (ควรพัง)"""
@patch('app.db')
def test_save_word_duplicate(mock_db, client):
    
    mock_db["user_dict"].find_one.return_value = {"vocab": "Cat"}
    response = client.post('/api/save_word', json={"username": "u1", "vocab": "Cat", "meaning": "แมว"})
    assert response.status_code == 400
"""5. อัปเดตโน้ตในคำศัพท์"""
@patch('app.db')
def test_update_note_success(mock_db, client):
    
    mock_db["user_dict"].update_one.return_value.matched_count = 1
    response = client.post('/api/save_note/65e123456789012345678901', json={"note": "จำยากจัง"})
    assert response.status_code == 200
"""6. ลบคำศัพท์ออกจากคลัง"""
@patch('app.db')
def test_delete_word_success(mock_db, client):
   
    mock_db["user_dict"].delete_one.return_value.deleted_count = 1
    response = client.delete('/api/mydict/65e123456789012345678901')
    assert response.status_code == 200

"""7. อัปเดตคะแนนและเปลี่ยน Rank (Gold)"""

@patch('app.get_mysql_connection')
def test_update_score_and_rank(mock_mysql, client):
    
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {"score": 240, "last_play_date": None}
    response = client.post('/api/update_score', json={"username": "u1", "score": 10})
    assert response.get_json()['new_rank'] == 'Gold 🥇'

@patch('app.get_mysql_connection')
def test_get_leaderboard_success(mock_mysql, client):
    """8. ดึงข้อมูลตารางคะแนน"""
    mock_cursor = mock_mysql.return_value.cursor.return_value
    mock_cursor.fetchall.return_value = [{"username": "top1", "score": 1000}]
    response = client.get('/api/leaderboard')
    assert response.status_code == 200