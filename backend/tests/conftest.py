import pytest
from app import app
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_mysql():
    with patch('app.get_mysql_connection') as mocked:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mocked.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        yield mocked, mock_conn, mock_cursor

@pytest.fixture
def mock_mongo():
    with patch('app.get_mongo_collection') as mocked:
        mock_db = MagicMock()
        mocked.return_value = mock_db
        yield mocked, mock_db