"""Tests for memory_monitor module."""

import os
import pytest
from pathlib import Path
import sys
import json
from unittest.mock import Mock, patch

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from memory_monitor import (
    get_memory_info, get_java_processes_memory, monitor_tool_execution,
    setup_logging, create_utils_directory
)

class TestMemoryInfo:
    """Test memory information retrieval."""
    
    def test_get_memory_info(self, monkeypatch):
        """Test getting system memory information."""
        # Mock psutil
        mock_memory = Mock()
        mock_memory.total = 16 * 1024**3  # 16GB
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_memory.used = 8 * 1024**3  # 8GB
        mock_memory.percent = 50.0
        
        mock_swap = Mock()
        mock_swap.total = 8 * 1024**3  # 8GB
        mock_swap.used = 2 * 1024**3  # 2GB
        mock_swap.percent = 25.0
        
        monkeypatch.setattr("psutil.virtual_memory", lambda: mock_memory)
        monkeypatch.setattr("psutil.swap_memory", lambda: mock_swap)
        
        info = get_memory_info()
        
        assert info['total_memory_gb'] == 16.0
        assert info['available_memory_gb'] == 8.0
        assert info['used_memory_gb'] == 8.0
        assert info['memory_percent'] == 50.0
        assert info['swap_total_gb'] == 8.0
        assert info['swap_used_gb'] == 2.0
        assert info['swap_percent'] == 25.0
        assert 'timestamp' in info

class TestJavaProcesses:
    """Test Java process memory tracking."""
    
    def test_get_java_processes_memory(self, monkeypatch):
        """Test getting memory usage of Java processes."""
        # Mock process info
        mock_processes = [
            Mock(info={
                'pid': 1234,
                'name': 'java',
                'cmdline': ['java', '-jar', 'robot.jar', 'merge'],
                'memory_info': Mock(rss=2 * 1024**3),  # 2GB
                'username': 'testuser',
                'exe': '/usr/bin/java'
            }),
            Mock(info={
                'pid': 5678,
                'name': 'java',
                'cmdline': ['java', '-jar', 'relation-graph.jar'],
                'memory_info': Mock(rss=1 * 1024**3),  # 1GB
                'username': 'testuser',
                'exe': '/usr/bin/java'
            }),
            Mock(info={
                'pid': 9999,
                'name': 'python',
                'cmdline': ['python', 'script.py'],
                'memory_info': Mock(rss=500 * 1024**2),  # 500MB
                'username': 'testuser',
                'exe': '/usr/bin/python'
            })
        ]
        
        monkeypatch.setattr("psutil.process_iter", lambda attrs: mock_processes)
        
        java_procs = get_java_processes_memory()
        
        # Should only return Java processes
        assert len(java_procs) == 2
        
        # Check ROBOT process - now classified as ROBOT-merge
        robot_proc = next(p for p in java_procs if p['type'] == 'ROBOT-merge')
        assert robot_proc['pid'] == 1234
        assert robot_proc['memory_gb'] == 2.0
        
        # Check relation-graph process
        rg_proc = next(p for p in java_procs if p['type'] == 'relation-graph')
        assert rg_proc['pid'] == 5678
        assert rg_proc['memory_gb'] == 1.0
    
    def test_get_java_processes_none_cmdline(self, monkeypatch):
        """Test handling processes with None cmdline."""
        # Mock process with None cmdline
        mock_processes = [
            Mock(info={
                'pid': 1234,
                'name': 'java',
                'cmdline': None,  # This was causing the TypeError
                'memory_info': Mock(rss=1024**3),
                'username': 'testuser',
                'exe': '/usr/bin/java'
            })
        ]
        
        monkeypatch.setattr("psutil.process_iter", lambda attrs: mock_processes)
        
        # Should not raise TypeError
        java_procs = get_java_processes_memory()
        
        assert len(java_procs) == 1
        assert java_procs[0]['type'] == 'unknown'
        assert java_procs[0]['cmdline_snippet'] == ''

class TestMonitorToolExecution:
    """Test tool execution monitoring."""
    
    def test_monitor_tool_execution_success(self, tmp_path, monkeypatch):
        """Test successful tool monitoring."""
        # Mock subprocess.Popen
        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, 0]  # Running, running, done
        mock_process.wait.return_value = 0
        
        monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: mock_process)
        
        # Mock memory functions
        monkeypatch.setattr("memory_monitor.get_memory_info", lambda: {
            'used_memory_gb': 4.0,
            'available_memory_gb': 12.0,
            'total_memory_gb': 16.0,
            'memory_percent': 25.0,
            'swap_total_gb': 0.0,
            'swap_used_gb': 0.0,
            'swap_percent': 0.0,
            'timestamp': '2024-01-01T00:00:00'
        })
        monkeypatch.setattr("memory_monitor.get_java_processes_memory", lambda: [])
        
        # Mock time.sleep to speed up test
        monkeypatch.setattr("time.sleep", lambda x: None)
        
        # Mock USER environment variable
        monkeypatch.setenv("USER", "testuser")
        
        log_dir = tmp_path / "logs"
        return_code, summary = monitor_tool_execution(
            "test_tool",
            "echo test",
            str(log_dir),
            interval=1
        )
        
        assert return_code == 0
        assert summary is not None
        assert summary['tool_name'] == "test_tool"
        assert summary['return_code'] == 0
        
        # Check log files were created
        assert (log_dir / "test_tool_memory_log.json").exists()
        assert (log_dir / "test_tool_memory_summary.txt").exists()
    
    def test_monitor_tool_execution_keyboard_interrupt(self, tmp_path, monkeypatch):
        """Test handling keyboard interrupt during monitoring."""
        # Mock subprocess.Popen
        mock_process = Mock()
        mock_process.poll.side_effect = KeyboardInterrupt()
        mock_process.terminate = Mock()
        
        monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: mock_process)
        
        log_dir = tmp_path / "logs"
        return_code, summary = monitor_tool_execution(
            "test_tool",
            "long_running_command",
            str(log_dir)
        )
        
        assert return_code == -1
        assert summary is None
        mock_process.terminate.assert_called_once()

class TestUtilsDirectory:
    """Test utils directory creation."""
    
    def test_create_utils_directory_test_mode(self, temp_repo, monkeypatch):
        """Test creating utils directory in test mode."""
        monkeypatch.setenv("ONTOLOGIES_SOURCE_FILE", "ontologies_source_test.txt")
        
        utils_dir = create_utils_directory(str(temp_repo))
        
        assert "outputs_test/run_" in str(utils_dir)  # Check for timestamped directory
        assert "/utils" in str(utils_dir)
        assert Path(utils_dir).exists()
    
    def test_create_utils_directory_production(self, temp_repo, monkeypatch):
        """Test creating utils directory in production mode."""
        monkeypatch.setenv("ONTOLOGIES_SOURCE_FILE", "ontologies_source.txt")
        monkeypatch.delenv("WORKFLOW_OUTPUT_DIR", raising=False)
        
        utils_dir = create_utils_directory(str(temp_repo))
        
        assert "outputs/run_" in str(utils_dir)  # Check for timestamped directory
        assert "/utils" in str(utils_dir)
        assert "outputs_test" not in str(utils_dir)
        assert Path(utils_dir).exists()