"""Tests for resource_check module."""

import os
import pytest
from pathlib import Path
import sys
from unittest.mock import Mock

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from resource_check import (
    check_system_resources, validate_step_output
)

# Helper function tests removed - functions don't exist in the actual module

# Disk space check tests removed - function doesn't exist in the actual module

# Memory check tests removed - function doesn't exist in the actual module

class TestCheckSystemResources:
    """Test the main system resource check function."""
    
    def test_check_system_resources_basic(self, monkeypatch):
        """Test basic resource check."""
        
        # Mock disk and memory checks
        mock_disk_usage = Mock()
        mock_disk_usage.free = 50 * 1024**3  # 50GB free
        mock_disk_usage.total = 100 * 1024**3  # 100GB total
        
        mock_memory = Mock()
        mock_memory.total = 16 * 1024**3  # 16GB total
        mock_memory.available = 10 * 1024**3  # 10GB available
        
        monkeypatch.setattr("shutil.disk_usage", lambda path: mock_disk_usage)
        monkeypatch.setattr("psutil.virtual_memory", lambda: mock_memory)
        # Mock the tool availability checks
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        
        success, message = check_system_resources(min_memory_gb=2.0, min_disk_gb=5.0)
        
        assert success == True
    
    def test_check_system_resources_with_sufficient_resources(self, monkeypatch):
        """Test resource check with sufficient resources."""
        
        # Mock sufficient resources
        mock_disk_usage = Mock()
        mock_disk_usage.free = 2000 * 1024**3  # 2TB free
        mock_disk_usage.total = 4000 * 1024**3  # 4TB total
        
        mock_memory = Mock()
        mock_memory.total = 2000 * 1024**3  # 2TB total
        mock_memory.available = 1600 * 1024**3  # 1.6TB available
        
        monkeypatch.setattr("shutil.disk_usage", lambda path: mock_disk_usage)
        monkeypatch.setattr("psutil.virtual_memory", lambda: mock_memory)
        # Mock the tool availability checks
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        
        success, message = check_system_resources(min_memory_gb=1000.0, min_disk_gb=1000.0)
        
        assert success == True
    
    def test_check_system_resources_insufficient_disk(self, monkeypatch):
        """Test resource check with insufficient disk space."""
        
        # Mock insufficient disk
        mock_disk_usage = Mock()
        mock_disk_usage.free = 100 * 1024**3  # 100GB free (not enough)
        mock_disk_usage.total = 500 * 1024**3  # 500GB total
        
        mock_memory = Mock()
        mock_memory.total = 2000 * 1024**3
        mock_memory.available = 1600 * 1024**3
        
        monkeypatch.setattr("shutil.disk_usage", lambda path: mock_disk_usage)
        monkeypatch.setattr("psutil.virtual_memory", lambda: mock_memory)
        
        success, message = check_system_resources(min_memory_gb=100.0, min_disk_gb=200.0)
        
        assert success == False
    
    def test_check_system_resources_insufficient_memory(self, monkeypatch):
        """Test resource check with insufficient memory."""
        
        # Mock insufficient memory
        mock_disk_usage = Mock()
        mock_disk_usage.free = 2000 * 1024**3
        mock_disk_usage.total = 4000 * 1024**3
        
        mock_memory = Mock()
        mock_memory.total = 32 * 1024**3  # 32GB total (not enough)
        mock_memory.available = 20 * 1024**3
        
        monkeypatch.setattr("shutil.disk_usage", lambda path: mock_disk_usage)
        monkeypatch.setattr("psutil.virtual_memory", lambda: mock_memory)
        
        success, message = check_system_resources(min_memory_gb=50.0, min_disk_gb=10.0)
        
        assert success == False

class TestValidateStepOutput:
    """Test step output validation."""
    
    def test_validate_step_output_success(self, tmp_path):
        """Test successful validation when all files exist."""
        # Create test files
        file1 = tmp_path / "output1.txt"
        file2 = tmp_path / "output2.txt"
        file1.write_text("test content 1" * 100)  # Make it larger than min size
        file2.write_text("test content 2" * 100)
        
        success, message = validate_step_output(
            "Test Step",
            [str(file1), str(file2)],
            min_size_bytes=10
        )
        
        assert success == True
        assert "PASS" in message
    
    def test_validate_step_output_missing_file(self, tmp_path):
        """Test validation fails when file is missing."""
        file1 = tmp_path / "output1.txt"
        file1.write_text("test content")
        
        success, message = validate_step_output(
            "Test Step",
            [str(file1), str(tmp_path / "missing.txt")],
            min_size_bytes=1
        )
        
        assert success == False
        assert "missing" in message