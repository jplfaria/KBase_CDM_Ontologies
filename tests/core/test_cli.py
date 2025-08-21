"""Tests for cdm_ontologies.cli module."""

import os
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from cdm_ontologies.cli import (
    main, run_all, setup_logging, timestamp_print,
    fix_docker_permissions
)

class TestCLIHelpers:
    """Test CLI helper functions."""
    
    def test_timestamp_print(self, capsys):
        """Test timestamp printing."""
        timestamp_print("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out
        assert "[20" in captured.out  # Check timestamp format
    
    def test_setup_logging(self, tmp_path, monkeypatch):
        """Test logging setup."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        (tmp_path / "logs").mkdir()
        
        # Reset logging configuration first
        import logging
        logging.getLogger().handlers = []
        logging.getLogger().setLevel(logging.WARNING)
        
        # Test verbose logging
        setup_logging(verbose=True)
        # Check that handlers were added
        assert len(logging.getLogger().handlers) > 0
        
        # Clear handlers for next test
        logging.getLogger().handlers = []
        
        # Test normal logging  
        setup_logging(verbose=False)
        # Check that handlers were added
        assert len(logging.getLogger().handlers) > 0
    
    def test_fix_docker_permissions(self, monkeypatch):
        """Test Docker permission fixing."""
        # Mock subprocess.run
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        
        # Mock os.getcwd, getuid, getgid
        monkeypatch.setattr("os.getcwd", lambda: "/test/dir")
        monkeypatch.setattr("os.getuid", lambda: 1000)
        monkeypatch.setattr("os.getgid", lambda: 1000)
        
        fix_docker_permissions()
        
        # Verify docker command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'docker'
        assert args[1] == 'run'
        assert '--user' in args
        assert 'root' in args

class TestRunAll:
    """Test the run_all workflow function."""
    
    @pytest.fixture
    def mock_workflow_functions(self, monkeypatch):
        """Mock all workflow step functions."""
        mocks = {
            'analyze_core': Mock(),
            'analyze_non_core': Mock(),
            'create_pseudo_base': Mock(),
            'merge': Mock(return_value=True),
            'create_db': Mock(return_value=True),
            'extract_tsv': Mock(return_value=True),
            'create_parquet': Mock(return_value=True),
            'check_resources': Mock(return_value=(True, "Resources OK"))
        }
        
        monkeypatch.setattr("cdm_ontologies.cli.analyze_core_ontologies", mocks['analyze_core'])
        monkeypatch.setattr("cdm_ontologies.cli.analyze_non_core_ontologies", mocks['analyze_non_core'])
        monkeypatch.setattr("cdm_ontologies.cli.create_pseudo_base_ontologies", mocks['create_pseudo_base'])
        monkeypatch.setattr("cdm_ontologies.cli.merge_ontologies", mocks['merge'])
        monkeypatch.setattr("cdm_ontologies.cli.create_semantic_sql_db", mocks['create_db'])
        monkeypatch.setattr("cdm_ontologies.cli.extract_sql_tables_to_tsv", mocks['extract_tsv'])
        monkeypatch.setattr("cdm_ontologies.cli.create_parquet_files", mocks['create_parquet'])
        monkeypatch.setattr("cdm_ontologies.cli.check_system_resources", mocks['check_resources'])
        
        return mocks
    
    def test_run_all_success(self, mock_workflow_functions, tmp_path, monkeypatch):
        """Test successful execution of all workflow steps."""
        # Create logs directory
        (tmp_path / "logs").mkdir()
        monkeypatch.chdir(tmp_path)
        
        # Create args mock
        args = Mock()
        args.skip_resource_check = False
        args.continue_on_error = False
        
        # Run workflow
        result = run_all(args)
        
        # Verify all steps were called
        assert result == 0
        for name, mock in mock_workflow_functions.items():
            if name != 'check_resources':  # This one is called differently
                mock.assert_called_once()
    
    def test_run_all_skip_non_core(self, mock_workflow_functions, tmp_path, monkeypatch):
        """Test skipping non-core analysis."""
        # Set environment variable
        monkeypatch.setenv("SKIP_NON_CORE_ANALYSIS", "true")
        
        # Create logs directory
        (tmp_path / "logs").mkdir()
        monkeypatch.chdir(tmp_path)
        
        # Create args mock
        args = Mock()
        args.skip_resource_check = True
        args.continue_on_error = False
        
        # Run workflow
        result = run_all(args)
        
        # Verify non-core analysis was NOT called
        assert result == 0
        mock_workflow_functions['analyze_non_core'].assert_not_called()
    
    def test_run_all_with_failure(self, mock_workflow_functions, tmp_path, monkeypatch):
        """Test workflow stops on failure."""
        # Make merge step fail
        mock_workflow_functions['merge'].return_value = False
        
        # Create logs directory
        (tmp_path / "logs").mkdir()
        monkeypatch.chdir(tmp_path)
        
        # Create args mock
        args = Mock()
        args.skip_resource_check = True
        args.continue_on_error = False
        
        # Run workflow
        result = run_all(args)
        
        # Should fail at merge step
        assert result == 1
        # Steps after merge should not be called
        mock_workflow_functions['create_db'].assert_not_called()
        mock_workflow_functions['extract_tsv'].assert_not_called()
    
    def test_run_all_continue_on_error(self, mock_workflow_functions, tmp_path, monkeypatch):
        """Test workflow continues when continue_on_error is set."""
        # Make merge step fail
        mock_workflow_functions['merge'].return_value = False
        
        # Create logs directory
        (tmp_path / "logs").mkdir()
        monkeypatch.chdir(tmp_path)
        
        # Create args mock with continue_on_error
        args = Mock()
        args.skip_resource_check = True
        args.continue_on_error = True
        
        # Run workflow
        result = run_all(args)
        
        # Should complete all steps despite failure
        assert result == 0
        for name, mock in mock_workflow_functions.items():
            if name != 'check_resources':
                mock.assert_called_once()

class TestCLIMain:
    """Test the main CLI entry point."""
    
    def test_main_help(self, monkeypatch):
        """Test help command."""
        monkeypatch.setattr("sys.argv", ["cli.py", "--help"])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    
    def test_main_run_all(self, monkeypatch, tmp_path):
        """Test run-all command."""
        # Create required directories
        (tmp_path / "logs").mkdir()
        monkeypatch.chdir(tmp_path)
        
        # Mock run_all function
        mock_run_all = Mock(return_value=0)
        monkeypatch.setattr("cdm_ontologies.cli.run_all", mock_run_all)
        
        # Set argv
        monkeypatch.setattr("sys.argv", ["cli.py", "run-all"])
        
        # Run main
        result = main()
        
        assert result == 0
        mock_run_all.assert_called_once()
    
    def test_main_individual_commands(self, monkeypatch, tmp_path):
        """Test individual command execution."""
        # Create logs directory
        (tmp_path / "logs").mkdir()
        monkeypatch.chdir(tmp_path)
        
        # Mock individual functions
        mock_analyze = Mock()
        monkeypatch.setattr("cdm_ontologies.cli.analyze_core_ontologies", mock_analyze)
        
        # Test analyze-core command
        monkeypatch.setattr("sys.argv", ["cli.py", "analyze-core"])
        result = main()
        
        assert result == 0
        mock_analyze.assert_called_once()
    
    def test_main_no_command(self, monkeypatch, tmp_path):
        """Test behavior when no command is provided."""
        # Create logs directory
        (tmp_path / "logs").mkdir()
        monkeypatch.chdir(tmp_path)
        
        # Set argv with no command
        monkeypatch.setattr("sys.argv", ["cli.py"])
        
        # Run main
        result = main()
        
        # Should print help and return 1
        assert result == 1