"""Test memory monitor improvements for better Java process detection."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from memory_monitor import get_java_processes_memory


class TestImprovedMemoryMonitor(unittest.TestCase):
    """Test improved Java process detection."""
    
    @patch('psutil.process_iter')
    def test_detect_java_by_name_variations(self, mock_process_iter):
        """Test detection of Java processes with various name patterns."""
        # Create mock processes with different Java name patterns
        mock_procs = [
            # Standard java process
            MagicMock(info={
                'pid': 1001,
                'name': 'java',
                'cmdline': ['/usr/bin/java', '-jar', 'robot.jar'],
                'memory_info': MagicMock(rss=1024**3),  # 1GB
                'username': 'testuser',
                'exe': '/usr/bin/java'
            }),
            # Java with different case
            MagicMock(info={
                'pid': 1002,
                'name': 'Java',
                'cmdline': ['Java', '-cp', 'semsql.jar'],
                'memory_info': MagicMock(rss=2*1024**3),  # 2GB
                'username': 'testuser',
                'exe': '/usr/bin/Java'
            }),
            # Process with java in name
            MagicMock(info={
                'pid': 1003,
                'name': 'javaw',
                'cmdline': ['javaw.exe', '-jar', 'app.jar'],
                'memory_info': MagicMock(rss=512*1024**2),  # 512MB
                'username': 'testuser',
                'exe': 'C:\\Program Files\\Java\\bin\\javaw.exe'
            }),
            # Non-java process
            MagicMock(info={
                'pid': 1004,
                'name': 'python',
                'cmdline': ['python', 'script.py'],
                'memory_info': MagicMock(rss=256*1024**2),  # 256MB
                'username': 'testuser',
                'exe': '/usr/bin/python'
            })
        ]
        
        mock_process_iter.return_value = mock_procs
        
        java_procs = get_java_processes_memory()
        
        # Should find 3 Java processes
        self.assertEqual(len(java_procs), 3)
        
        # Check process types
        types = {p['type'] for p in java_procs}
        self.assertIn('ROBOT', types)
        self.assertIn('SemanticSQL', types)
        
        # Check memory values
        memory_values = sorted([p['memory_gb'] for p in java_procs])
        self.assertAlmostEqual(memory_values[0], 0.5, places=1)  # 512MB
        self.assertAlmostEqual(memory_values[1], 1.0, places=1)  # 1GB
        self.assertAlmostEqual(memory_values[2], 2.0, places=1)  # 2GB
    
    @patch('psutil.process_iter')
    def test_detect_java_by_exe_path(self, mock_process_iter):
        """Test detection of Java processes by executable path."""
        # Create processes where name isn't 'java' but exe path contains java
        mock_procs = [
            # Process started from JDK
            MagicMock(info={
                'pid': 2001,
                'name': 'robot',
                'cmdline': ['robot', 'merge', 'file.owl'],
                'memory_info': MagicMock(rss=3*1024**3),  # 3GB
                'username': 'testuser',
                'exe': '/opt/jdk-11/bin/java'
            }),
            # Process from JRE
            MagicMock(info={
                'pid': 2002,
                'name': 'app',
                'cmdline': ['app', '--semantic-sql'],
                'memory_info': MagicMock(rss=1.5*1024**3),  # 1.5GB
                'username': 'testuser',
                'exe': '/usr/lib/jvm/jre-8/bin/java'
            })
        ]
        
        mock_process_iter.return_value = mock_procs
        
        java_procs = get_java_processes_memory()
        
        # Should find both processes
        self.assertEqual(len(java_procs), 2)
        
        # Check detection worked
        pids = {p['pid'] for p in java_procs}
        self.assertEqual(pids, {2001, 2002})
    
    @patch('psutil.process_iter')
    def test_detect_java_by_cmdline(self, mock_process_iter):
        """Test detection of Java processes by command line patterns."""
        # Processes that don't have 'java' in name but have it in cmdline
        mock_procs = [
            # Docker container process
            MagicMock(info={
                'pid': 3001,
                'name': 'docker-java',
                'cmdline': ['/usr/local/bin/java', '-jar', '/app/robot.jar', 'query'],
                'memory_info': MagicMock(rss=4*1024**3),  # 4GB
                'username': 'root',
                'exe': None  # Docker might not expose exe
            }),
            # Process with semantic-sql in cmdline
            MagicMock(info={
                'pid': 3002,
                'name': 'sh',
                'cmdline': ['sh', '-c', 'semantic-sql-runner /data/ontology.db'],
                'memory_info': MagicMock(rss=800*1024**2),  # 800MB
                'username': 'testuser',
                'exe': '/bin/sh'
            })
        ]
        
        mock_process_iter.return_value = mock_procs
        
        java_procs = get_java_processes_memory()
        
        # Should find both processes
        self.assertEqual(len(java_procs), 2)
        
        # Check process types
        types = {p['type'] for p in java_procs}
        self.assertIn('ROBOT-query', types)  # docker-java process with robot.jar query
        self.assertIn('SemanticSQL', types)
    
    @patch('psutil.process_iter')
    def test_process_type_detection(self, mock_process_iter):
        """Test correct identification of process types."""
        mock_procs = [
            # ROBOT merge
            MagicMock(info={
                'pid': 4001,
                'name': 'java',
                'cmdline': ['java', '-jar', 'robot.jar', 'merge', '--input', 'file.owl'],
                'memory_info': MagicMock(rss=2*1024**3),
                'username': 'testuser',
                'exe': '/usr/bin/java'
            }),
            # ROBOT query
            MagicMock(info={
                'pid': 4002,
                'name': 'java',
                'cmdline': ['java', '-jar', 'robot.jar', 'query', '--query', 'SELECT *'],
                'memory_info': MagicMock(rss=1*1024**3),
                'username': 'testuser',
                'exe': '/usr/bin/java'
            }),
            # Relation graph
            MagicMock(info={
                'pid': 4003,
                'name': 'java',
                'cmdline': ['java', '-cp', 'relation-graph.jar', 'Main'],
                'memory_info': MagicMock(rss=1.5*1024**3),
                'username': 'testuser',
                'exe': '/usr/bin/java'
            }),
            # SemanticSQL
            MagicMock(info={
                'pid': 4004,
                'name': 'java',
                'cmdline': ['java', '-jar', 'semsql.jar', 'create', 'ontology.db'],
                'memory_info': MagicMock(rss=3*1024**3),
                'username': 'testuser',
                'exe': '/usr/bin/java'
            }),
            # Generic ontology processing
            MagicMock(info={
                'pid': 4005,
                'name': 'java',
                'cmdline': ['java', '-Xmx8g', 'ProcessOntology', 'CDM_merged.owl'],
                'memory_info': MagicMock(rss=5*1024**3),
                'username': 'testuser',
                'exe': '/usr/bin/java'
            })
        ]
        
        mock_process_iter.return_value = mock_procs
        
        java_procs = get_java_processes_memory()
        
        # Check all process types are correctly identified
        type_map = {p['pid']: p['type'] for p in java_procs}
        
        # Check ROBOT sub-command detection
        self.assertEqual(type_map[4001], 'ROBOT-merge')
        self.assertEqual(type_map[4002], 'ROBOT-query')
        self.assertEqual(type_map[4003], 'relation-graph')
        self.assertEqual(type_map[4004], 'SemanticSQL')
        self.assertEqual(type_map[4005], 'ROBOT')  # Generic ontology processing


if __name__ == '__main__':
    unittest.main()