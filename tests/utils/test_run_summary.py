"""Tests for run_summary module."""

import os
import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from run_summary import RunSummary, init_summary, get_summary


class TestRunSummary:
    """Test RunSummary class functionality."""
    
    def test_init_run_summary(self, tmp_path):
        """Test RunSummary initialization."""
        run_id = "test_run_123"
        output_dir = str(tmp_path)
        mode = "TEST"
        
        summary = RunSummary(run_id, output_dir, mode)
        
        assert summary.run_id == run_id
        assert summary.output_dir == output_dir
        assert summary.mode == mode
        assert summary.status == "RUNNING"
        assert isinstance(summary.start_time, datetime)
        assert summary.end_time is None
        
        # Check initial data structures
        assert summary.steps == {}
        assert summary.ontology_stats['total_processed'] == 0
        assert summary.ontology_stats['new_downloads'] == []
        assert summary.processing_results == {}
        assert summary.output_files == {}
    
    def test_step_tracking(self, tmp_path):
        """Test pipeline step tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        # Start a step
        summary.start_step("Analyze Core Ontologies", 1)
        assert summary.current_step == "Analyze Core Ontologies"
        assert "Analyze Core Ontologies" in summary.steps
        assert summary.steps["Analyze Core Ontologies"]['status'] == 'RUNNING'
        
        # End the step
        summary.end_step("Analyze Core Ontologies", "SUCCESS", {"files_processed": 5})
        assert summary.current_step is None
        assert summary.steps["Analyze Core Ontologies"]['status'] == 'SUCCESS'
        assert summary.steps["Analyze Core Ontologies"]['details']['files_processed'] == 5
        assert summary.steps["Analyze Core Ontologies"]['duration_seconds'] > 0
    
    def test_ontology_download_tracking(self, tmp_path):
        """Test ontology download event tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        # Add new download
        summary.add_ontology_download("bfo.owl", "new", 1024000)
        assert summary.ontology_stats['total_processed'] == 1
        assert len(summary.ontology_stats['new_downloads']) == 1
        assert summary.ontology_stats['new_downloads'][0]['filename'] == "bfo.owl"
        
        # Add updated download
        summary.add_ontology_download("iao.owl", "updated", 2048000, "old123", "new456")
        assert summary.ontology_stats['total_processed'] == 2
        assert len(summary.ontology_stats['updated']) == 1
        
        # Add skipped download
        summary.add_ontology_download("ro.owl", "skipped", 512000)
        assert summary.ontology_stats['total_processed'] == 3
        assert len(summary.ontology_stats['skipped']) == 1
        
        # Add failed download
        summary.add_ontology_download("pato.owl", "failed")
        assert summary.ontology_stats['total_processed'] == 4
        assert len(summary.ontology_stats['failed']) == 1
    
    def test_version_change_tracking(self, tmp_path):
        """Test version change tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        summary.add_version_change("test.owl", "abc123def456", "789xyz012345")
        
        assert len(summary.version_changes['files_updated']) == 1
        change = summary.version_changes['files_updated'][0]
        assert change['filename'] == "test.owl"
        assert change['old_checksum'] == "abc123de"  # First 8 chars
        assert change['new_checksum'] == "789xyz01"  # First 8 chars
    
    def test_backup_tracking(self, tmp_path):
        """Test backup creation tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        summary.add_backup(1024 * 1024 * 100)  # 100MB
        summary.add_backup(1024 * 1024 * 50)   # 50MB
        
        assert summary.version_changes['backups_created'] == 2
        assert summary.version_changes['backup_size_gb'] == pytest.approx(0.146, rel=0.01)
    
    def test_memory_usage_tracking(self, tmp_path):
        """Test memory usage tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        summary.update_memory_usage(10.5, 16.4)
        assert summary.system_info['peak_memory_usage_gb'] == 10.5
        assert summary.system_info['peak_memory_percent'] == 16.4
        
        # Update with lower value - should not change peak
        summary.update_memory_usage(8.0, 12.5)
        assert summary.system_info['peak_memory_usage_gb'] == 10.5
        
        # Update with higher value - should update peak
        summary.update_memory_usage(12.0, 18.8)
        assert summary.system_info['peak_memory_usage_gb'] == 12.0
        assert summary.system_info['peak_memory_percent'] == 18.8
    
    def test_processing_results(self, tmp_path):
        """Test processing results tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        summary.add_processing_result('database_tables', 17)
        summary.add_processing_result('total_rows', 435892)
        summary.add_processing_result('compression_ratio', '91.7%')
        
        assert summary.processing_results['database_tables'] == 17
        assert summary.processing_results['total_rows'] == 435892
        assert summary.processing_results['compression_ratio'] == '91.7%'
    
    def test_output_file_tracking(self, tmp_path):
        """Test output file tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        summary.add_output_file('merged_ontology', '/path/to/merged.owl', 1024 * 1024 * 100)
        summary.add_output_file('database', '/path/to/db.sqlite', 1024 * 1024 * 1024 * 10)
        
        assert len(summary.output_files) == 2
        assert summary.output_files['merged_ontology']['size_gb'] == pytest.approx(0.0977, rel=0.1)
        assert summary.output_files['database']['size_gb'] == pytest.approx(9.77, rel=0.1)
    
    def test_error_warning_tracking(self, tmp_path):
        """Test error and warning tracking."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        # Simulate being in a step
        summary.current_step = "Test Step"
        
        summary.add_error("Failed to download ontology")
        summary.add_warning("Ontology uses deprecated format")
        
        assert len(summary.issues['errors']) == 1
        assert summary.issues['errors'][0]['message'] == "Failed to download ontology"
        assert summary.issues['errors'][0]['step'] == "Test Step"
        
        assert len(summary.issues['warnings']) == 1
        assert summary.issues['warnings'][0]['message'] == "Ontology uses deprecated format"
    
    def test_finalize(self, tmp_path):
        """Test summary finalization."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        # Add some activity
        summary.add_processing_result('test_metric', 123)
        
        # Finalize
        summary.finalize("SUCCESS")
        
        assert summary.status == "SUCCESS"
        assert summary.end_time is not None
        assert isinstance(summary.end_time, datetime)
        assert summary.system_info['final_memory_available_gb'] > 0
        assert summary.system_info['final_disk_available_gb'] > 0
    
    def test_format_duration(self, tmp_path):
        """Test duration formatting."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        assert summary.format_duration(45) == "45s"
        assert summary.format_duration(90) == "1m 30s"
        assert summary.format_duration(3665) == "1h 1m"
        assert summary.format_duration(7325) == "2h 2m"
    
    def test_generate_summary(self, tmp_path):
        """Test summary text generation."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        # Add some data
        summary.start_step("Test Step", 1)
        summary.end_step("Test Step", "SUCCESS")
        summary.add_ontology_download("test.owl", "new", 1024000)
        summary.add_processing_result('test_metric', 42)
        summary.add_output_file('test_output', '/path/to/output', 1024 * 1024)
        
        # Generate summary
        summary_text = summary.generate_summary()
        
        # Check key components are present
        assert "CDM Ontologies Pipeline Run Summary" in summary_text
        assert "Run ID: test_run" in summary_text
        assert "Mode: TEST" in summary_text
        assert "System Resources:" in summary_text
        assert "Ontology Downloads:" in summary_text
        assert "Pipeline Steps:" in summary_text
        assert "Processing Results:" in summary_text
        assert "Output Files:" in summary_text
        assert "test_metric: 42" in summary_text
    
    def test_save_summary(self, tmp_path):
        """Test saving summary to files."""
        summary = RunSummary("test_run", str(tmp_path), "TEST")
        
        # Add some data
        summary.add_processing_result('test_metric', 42)
        summary.finalize("SUCCESS")
        
        # Save summary
        text_file, json_file = summary.save_summary()
        
        # Check files exist
        assert os.path.exists(text_file)
        assert os.path.exists(json_file)
        
        # Check text file content
        with open(text_file, 'r') as f:
            text_content = f.read()
            assert "Run ID: test_run" in text_content
            assert "Status: SUCCESS" in text_content
        
        # Check JSON file content
        with open(json_file, 'r') as f:
            json_content = json.load(f)
            assert json_content['run_id'] == "test_run"
            assert json_content['status'] == "SUCCESS"
            assert json_content['processing_results']['test_metric'] == 42
    
    def test_state_persistence(self, tmp_path):
        """Test saving and loading summary state."""
        # Create and populate a summary
        summary1 = RunSummary("test_run", str(tmp_path), "TEST")
        summary1.add_processing_result('test_metric', 42)
        summary1.add_ontology_download("test.owl", "new", 1024000)
        
        # Save state
        state_file = os.path.join(str(tmp_path), 'test_state.json')
        os.environ['RUN_SUMMARY_PATH'] = state_file
        summary1.save_state()
        
        # Load state into new instance
        summary2 = RunSummary.load_state(state_file)
        
        # Verify state was preserved
        assert summary2.run_id == "test_run"
        assert summary2.mode == "TEST"
        assert summary2.processing_results['test_metric'] == 42
        assert len(summary2.ontology_stats['new_downloads']) == 1
        assert summary2.ontology_stats['new_downloads'][0]['filename'] == "test.owl"


class TestSummaryGlobalFunctions:
    """Test global summary management functions."""
    
    def test_init_and_get_summary(self, tmp_path):
        """Test initializing and retrieving global summary."""
        # Clear any existing instance
        import run_summary
        run_summary._summary_instance = None
        
        # Initialize summary
        run_id = "test_run"
        output_dir = str(tmp_path)
        summary = init_summary(run_id, output_dir, "TEST")
        
        assert summary is not None
        assert summary.run_id == run_id
        
        # Get summary should return same instance
        retrieved = get_summary()
        assert retrieved is summary
    
    def test_get_summary_from_file(self, tmp_path, monkeypatch):
        """Test loading summary from environment path."""
        import run_summary
        
        # Clear global instance
        run_summary._summary_instance = None
        
        # Create a summary and save it
        summary1 = RunSummary("test_run", str(tmp_path), "TEST")
        summary1.add_processing_result('loaded_from_file', True)
        
        state_file = os.path.join(str(tmp_path), 'test_state.json')
        monkeypatch.setenv('RUN_SUMMARY_PATH', state_file)
        summary1.save_state()
        
        # Clear instance again
        run_summary._summary_instance = None
        
        # Get summary should load from file
        loaded = get_summary()
        assert loaded is not None
        assert loaded.run_id == "test_run"
        assert loaded.processing_results['loaded_from_file'] is True
    
    def test_get_summary_no_file(self, monkeypatch):
        """Test get_summary returns None when no file exists."""
        import run_summary
        
        # Clear instance and environment
        run_summary._summary_instance = None
        monkeypatch.setenv('RUN_SUMMARY_PATH', '/nonexistent/path.json')
        
        result = get_summary()
        assert result is None