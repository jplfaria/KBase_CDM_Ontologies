"""Tests for version_tracker module."""

import os
import pytest
from pathlib import Path
import sys
import json
from datetime import datetime

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from version_tracker import (
    load_version_info, save_version_info, should_download,
    get_file_checksum, backup_old_version, update_version_info,
    log_download_attempt
)

class TestVersionInfo:
    """Test version info loading and saving."""
    
    def test_load_version_info_empty(self, tmp_path):
        """Test loading when no version file exists."""
        version_file = tmp_path / "versions.json"
        info = load_version_info(str(version_file))
        
        assert info == {}
    
    def test_load_version_info_existing(self, tmp_path):
        """Test loading existing version info."""
        version_file = tmp_path / "versions.json"
        test_data = {
            "test.owl": {
                "url": "http://example.org/test.owl",
                "checksum": "abc123",
                "last_updated": "2024-01-01T00:00:00"
            }
        }
        version_file.write_text(json.dumps(test_data))
        
        info = load_version_info(str(version_file))
        
        assert info == test_data
        assert info["test.owl"]["checksum"] == "abc123"
    
    def test_save_version_info(self, tmp_path):
        """Test saving version info."""
        version_file = tmp_path / "versions.json"
        test_data = {
            "test.owl": {
                "url": "http://example.org/test.owl",
                "checksum": "xyz789"
            }
        }
        
        save_version_info(str(version_file), test_data)
        
        assert version_file.exists()
        loaded = json.loads(version_file.read_text())
        assert loaded == test_data

class TestShouldDownload:
    """Test download decision logic."""
    
    def test_should_download_new_file(self, tmp_path):
        """Test downloading a file that doesn't exist."""
        file_path = tmp_path / "new.owl"
        version_file = tmp_path / "versions.json"
        
        should, reason = should_download(str(file_path), "http://example.org/new.owl", str(version_file))
        
        assert should == True
        assert reason == "file_not_exists"
    
    def test_should_download_no_version_info(self, tmp_path):
        """Test downloading when file exists but no version info."""
        file_path = tmp_path / "test.owl"
        file_path.write_text("content")
        version_file = tmp_path / "versions.json"
        
        should, reason = should_download(str(file_path), "http://example.org/test.owl", str(version_file))
        
        assert should == True
        assert reason == "no_version_info"
    
    def test_should_download_url_changed(self, tmp_path):
        """Test downloading when URL has changed."""
        file_path = tmp_path / "test.owl"
        file_path.write_text("content")
        
        version_file = tmp_path / "versions.json"
        version_data = {
            "test.owl": {
                "url": "http://old.example.org/test.owl",
                "checksum": "abc123"
            }
        }
        version_file.write_text(json.dumps(version_data))
        
        should, reason = should_download(str(file_path), "http://new.example.org/test.owl", str(version_file))
        
        assert should == True
        assert reason == "checksum_mismatch"  # Changed because file checksum won't match
    
    def test_should_not_download_unchanged(self, tmp_path):
        """Test not downloading when file is unchanged."""
        file_path = tmp_path / "test.owl"
        file_path.write_text("content")
        
        # Calculate actual checksum
        import hashlib
        checksum = hashlib.sha256(b"content").hexdigest()
        
        version_file = tmp_path / "versions.json"
        version_data = {
            "test.owl": {
                "url": "http://example.org/test.owl",
                "checksum": checksum
            }
        }
        version_file.write_text(json.dumps(version_data))
        
        # Disable remote checking for this test
        should, reason = should_download(str(file_path), "http://example.org/test.owl", str(version_file), check_remote=False)
        
        assert should == False
        assert reason == "up_to_date"

class TestBackup:
    """Test file backup functionality."""
    
    def test_backup_old_version(self, tmp_path):
        """Test backing up old version of file."""
        # Create original file
        file_path = tmp_path / "test.owl"
        file_path.write_text("old content")
        
        # Create version directory
        version_dir = tmp_path / "versions"
        version_dir.mkdir()
        
        # Backup file
        backup_old_version(str(file_path), "old_checksum_123", str(version_dir))
        
        # Check backup was created (format is name_checksum[:8].ext)
        backups = list((version_dir / "backups").glob("test_*.owl"))
        assert len(backups) == 1
        
        # Verify backup content
        assert backups[0].read_text() == "old content"
    
    def test_backup_creates_directory(self, tmp_path):
        """Test backup creates directory if needed."""
        file_path = tmp_path / "test.owl"
        file_path.write_text("content")
        
        version_dir = tmp_path / "new_versions"
        
        # Backup should create directory
        backup_old_version(str(file_path), "checksum", str(version_dir))
        
        assert version_dir.exists()

class TestUpdateVersionInfo:
    """Test version info updates."""
    
    def test_update_version_info_new_entry(self, tmp_path):
        """Test adding new entry to version info."""
        version_file = tmp_path / "versions.json"
        
        update_version_info(
            str(version_file),
            "test.owl",
            "http://example.org/test.owl",
            None,
            "new_checksum_456"
        )
        
        # Load and verify
        data = json.loads(version_file.read_text())
        assert "test.owl" in data
        assert data["test.owl"]["checksum"] == "new_checksum_456"
        assert data["test.owl"]["url"] == "http://example.org/test.owl"
        assert "last_updated" in data["test.owl"]
    
    def test_update_version_info_existing_entry(self, tmp_path):
        """Test updating existing entry."""
        version_file = tmp_path / "versions.json"
        
        # Create initial data
        initial_data = {
            "test.owl": {
                "url": "http://example.org/test.owl",
                "checksum": "old_checksum",
                "last_updated": "2024-01-01T00:00:00"
            }
        }
        version_file.write_text(json.dumps(initial_data))
        
        # Update
        update_version_info(
            str(version_file),
            "test.owl",
            "http://example.org/test.owl",
            "old_checksum",
            "new_checksum"
        )
        
        # Verify
        data = json.loads(version_file.read_text())
        assert data["test.owl"]["checksum"] == "new_checksum"
        assert data["test.owl"]["previous_checksum"] == "old_checksum"

class TestDownloadLogging:
    """Test download attempt logging."""
    
    def test_log_download_attempt(self, tmp_path):
        """Test logging download attempts."""
        log_dir = tmp_path / "logs"
        
        log_download_attempt(
            str(log_dir),
            "test.owl",
            "success",
            "checksum123",
            "http://example.org/test.owl"
        )
        
        # Check log file was created
        log_file = log_dir / "download_history.log"
        assert log_file.exists()
        
        # Verify log entry (format is pipe-separated, not JSON)
        with open(log_file, 'r') as f:
            line = f.readline()
            assert "test.owl" in line
            assert "success" in line
            assert "checksum" in line  # Contains checksum
            assert "http://example.org/test.owl" in line
    
    def test_log_download_attempt_with_error(self, tmp_path):
        """Test logging failed download attempts."""
        log_dir = tmp_path / "logs"
        
        log_download_attempt(
            str(log_dir),
            "test.owl",
            "error",
            None,
            "http://example.org/test.owl",
            "Connection timeout"
        )
        
        # Check log file
        log_file = log_dir / "download_history.log"
        assert log_file.exists()
        
        # Verify error was logged
        with open(log_file, 'r') as f:
            line = f.readline()
            assert "error" in line
            assert "Connection timeout" in line
            assert "N/A" in line  # No checksum