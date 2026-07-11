import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from your_module import SnowflakeTableManager

@pytest.fixture
def mock_conn():
    with patch('snowflake.connector.connect') as mock_connect:
        yield mock_connect

def test_table_exists_true(mock_conn):
    # Setup
    manager = SnowflakeTableManager({})
    mock_df = pd.DataFrame({'COUNT(*)': [1]})
    
    with patch('pandas.read_sql', return_value=mock_df):
        exists = manager.table_exists("MY_TABLE", "PUBLIC", "MY_DB")
        assert exists is True

def test_table_exists_false(mock_conn):
    manager = SnowflakeTableManager({})
    mock_df = pd.DataFrame({'COUNT(*)': [0]})
    
    with patch('pandas.read_sql', return_value=mock_df):
        exists = manager.table_exists("NON_EXISTENT", "PUBLIC", "MY_DB")
        assert exists is False

def test_column_mismatch_detection():
    manager = SnowflakeTableManager({})
    # Mocking metadata return
    with patch.object(manager, 'get_column_info', return_value=pd.DataFrame({'COLUMN_NAME': ['ID', 'NAME']})):
        result = manager.check_column_mismatches("T", "S", "D", ['ID', 'DATE'])
        assert "DATE" in result['missing']
        assert "NAME" in result['extra']
