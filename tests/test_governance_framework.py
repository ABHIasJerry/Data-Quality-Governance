"""
Unit Tests for Data Governance Framework
Test core functionality and data quality checks
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from snowflake_connector import SnowflakeConnector
from metadata_scanner import MetadataScanner
from data_quality_checker import DataQualityChecker, CheckSeverity
from governance_manager import GovernanceManager


class TestSnowflakeConnector(unittest.TestCase):
    """Test Snowflake connection management"""
    
    def setUp(self):
        self.config = {
            'user': 'test_user',
            'password': 'test_pass',
            'account': 'test_account'
        }
    
    def test_connector_initialization(self):
        """Test connector can be initialized"""
        connector = SnowflakeConnector(self.config)
        self.assertIsNotNone(connector)
        self.assertEqual(connector.config['user'], 'test_user')
    
    @patch('snowflake_connector.snowflake.connector.connect')
    def test_connection_success(self, mock_connect):
        """Test successful connection"""
        mock_connect.return_value = MagicMock()
        connector = SnowflakeConnector(self.config)
        connector.connect()
        mock_connect.assert_called_once()
    
    def test_query_execution(self):
        """Test query execution"""
        connector = SnowflakeConnector(self.config)
        connector.connection = MagicMock()
        
        mock_cursor = MagicMock()
        mock_cursor.description = [('COLUMN1',), ('COLUMN2',)]
        mock_cursor.fetchall.return_value = [('value1', 'value2')]
        connector.connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        results = connector.execute_query("SELECT * FROM table")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['COLUMN1'], 'value1')


class TestMetadataScanner(unittest.TestCase):
    """Test metadata scanning functionality"""
    
    def setUp(self):
        self.mock_connector = MagicMock(spec=SnowflakeConnector)
        self.scanner = MetadataScanner(self.mock_connector)
    
    def test_scanner_initialization(self):
        """Test scanner initialization"""
        self.assertIsNotNone(self.scanner)
        self.assertEqual(self.scanner.connector, self.mock_connector)
    
    def test_scan_table_metadata(self):
        """Test table metadata scanning"""
        # Mock return values
        self.mock_connector.execute_query.side_effect = [
            # Columns
            [{'COLUMN_NAME': 'ID', 'ORDINAL_POSITION': 1, 'DATA_TYPE': 'NUMBER',
              'IS_NULLABLE': 'NO', 'COLUMN_DEFAULT': None}],
            # Row count
            [{'ROW_COUNT': 1000}],
            # Table size
            [{'SIZE_MB': 10.5}],
            # Creation time
            [{'CREATION_TIME': '2024-01-01'}],
            # Last altered
            [{'LAST_ALTERED': '2024-01-15'}],
            # Constraints
            [],
            # Completeness
            [{'TOTAL_ROWS': 1000, 'NON_NULL_COUNT': 1000}]
        ]
        
        metadata = self.scanner.scan_table_metadata('DB', 'SCHEMA', 'TABLE')
        
        self.assertEqual(metadata['database'], 'DB')
        self.assertEqual(metadata['schema'], 'SCHEMA')
        self.assertEqual(metadata['table_name'], 'TABLE')
        self.assertEqual(metadata['row_count'], 1000)
        self.assertEqual(len(metadata['columns']), 1)


class TestDataQualityChecker(unittest.TestCase):
    """Test data quality checking"""
    
    def setUp(self):
        self.mock_connector = MagicMock(spec=SnowflakeConnector)
        self.checker = DataQualityChecker(self.mock_connector)
    
    def test_checker_initialization(self):
        """Test checker initialization"""
        self.assertIsNotNone(self.checker)
        self.assertEqual(len(self.checker.checks_performed), 0)
    
    def test_duplicate_check(self):
        """Test duplicate record detection"""
        self.mock_connector.execute_query.return_value = [{'DUPLICATE_COUNT': 5}]
        
        result = self.checker._check_duplicates('DB', 'SCHEMA', 'TABLE')
        
        self.assertFalse(result['passed'])
        self.assertEqual(result['check_type'], 'DUPLICATE_RECORDS')
        self.assertIn('5', result['details'])
    
    def test_null_check(self):
        """Test null value detection"""
        self.mock_connector.execute_query.return_value = [
            {'NULL_COUNT': 10},
            {'NULL_COUNT': 0}
        ]
        
        config = {
            'non_nullable_columns': ['ID', 'NAME']
        }
        
        result = self.checker._check_null_values('DB', 'SCHEMA', 'TABLE', config)
        
        self.assertFalse(result['passed'])
        self.assertEqual(result['check_type'], 'NULL_VALUES')
    
    def test_data_freshness_check(self):
        """Test data freshness validation"""
        self.mock_connector.execute_query.return_value = [
            {'DAYS_OLD': 5}
        ]
        
        config = {
            'timestamp_column': 'CREATED_AT',
            'max_data_age_days': 7
        }
        
        result = self.checker._check_data_freshness('DB', 'SCHEMA', 'TABLE', config)
        
        self.assertTrue(result['passed'])
        self.assertEqual(result['check_type'], 'DATA_FRESHNESS')
    
    def test_run_quality_checks(self):
        """Test running multiple quality checks"""
        self.mock_connector.execute_query.return_value = [{'DUPLICATE_COUNT': 0}]
        
        config = {
            'check_duplicates': True,
            'check_nulls': False,
            'check_data_types': False,
            'check_referential_integrity': False,
            'check_outliers': False,
            'check_freshness': False,
            'check_patterns': False
        }
        
        results = self.checker.run_quality_checks('DB', 'SCHEMA', 'TABLE', config)
        
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['check_type'], 'DUPLICATE_RECORDS')


class TestGovernanceManager(unittest.TestCase):
    """Test governance management"""
    
    def setUp(self):
        self.mock_connector = MagicMock(spec=SnowflakeConnector)
        self.manager = GovernanceManager(self.mock_connector)
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.connector, self.mock_connector)
    
    def test_register_table(self):
        """Test table registration"""
        self.mock_connector.execute_update.return_value = 1
        
        config = {
            'governance_level': 'CONFIDENTIAL',
            'owner_team': 'DATA_OPS',
            'critical_table': True,
            'pii_present': True
        }
        
        table_id = self.manager.register_table('DB', 'SCHEMA', 'TABLE', config)
        
        self.assertIsNotNone(table_id)
        self.assertIn('TABLE', table_id)
        self.mock_connector.execute_update.assert_called_once()
    
    def test_log_quality_check(self):
        """Test logging quality check results"""
        self.mock_connector.execute_update.return_value = 1
        
        check_result = {
            'check_type': 'DUPLICATE_RECORDS',
            'passed': False,
            'severity': 'ERROR',
            'details': 'Found 10 duplicate records'
        }
        
        metric_id = self.manager.log_quality_check('DB', 'TABLE_ID', check_result)
        
        self.assertIsNotNone(metric_id)
        self.assertIn('QM_', metric_id)
        self.mock_connector.execute_update.assert_called_once()
    
    def test_create_compliance_issue(self):
        """Test compliance issue creation"""
        self.mock_connector.execute_update.return_value = 1
        
        config = {
            'issue_type': 'DATA_QUALITY',
            'severity': 'ERROR',
            'description': 'Data quality violations detected',
            'remediation_action': 'Investigate and remediate',
            'due_date': '2024-12-31'
        }
        
        issue_id = self.manager.create_compliance_issue('DB', 'TABLE_ID', config)
        
        self.assertIsNotNone(issue_id)
        self.assertIn('CI_', issue_id)
        self.mock_connector.execute_update.assert_called_once()
    
    def test_record_lineage(self):
        """Test data lineage recording"""
        self.mock_connector.execute_update.return_value = 1
        
        lineage_id = self.manager.record_lineage(
            'DB',
            'SOURCE_TABLE',
            'TARGET_TABLE',
            'SELECT * FROM source',
            'SUCCESS'
        )
        
        self.assertIsNotNone(lineage_id)
        self.assertIn('LG_', lineage_id)


class TestCheckSeverity(unittest.TestCase):
    """Test severity enum"""
    
    def test_severity_values(self):
        """Test all severity levels are defined"""
        severities = [
            CheckSeverity.INFO,
            CheckSeverity.WARNING,
            CheckSeverity.ERROR,
            CheckSeverity.CRITICAL
        ]
        
        self.assertEqual(len(severities), 4)
        self.assertEqual(CheckSeverity.INFO.value, 'INFO')
        self.assertEqual(CheckSeverity.CRITICAL.value, 'CRITICAL')


if __name__ == '__main__':
    unittest.main()
