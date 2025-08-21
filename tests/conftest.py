"""Shared fixtures and configuration for CDM Ontologies tests."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create required directories
        (repo_path / "config").mkdir()
        (repo_path / "ontology_data_owl").mkdir()
        (repo_path / "ontology_data_owl_test").mkdir()
        (repo_path / "outputs").mkdir()
        (repo_path / "outputs_test").mkdir()
        (repo_path / "logs").mkdir()
        (repo_path / "scripts").mkdir()
        
        yield repo_path

@pytest.fixture
def sample_ontology_source_file(temp_repo):
    """Create a sample ontologies source file."""
    source_file = temp_repo / "config" / "ontologies_source_test.txt"
    content = """# Test ontologies
# Core Base Version Ontologies
http://purl.obolibrary.org/obo/go/go-base.owl
http://purl.obolibrary.org/obo/chebi/chebi-base.owl

# Non Base Version Ontologies
http://purl.obolibrary.org/obo/uberon.owl
"""
    source_file.write_text(content)
    return source_file

@pytest.fixture
def mini_owl_file():
    """Create a minimal OWL file for testing."""
    content = """<?xml version="1.0"?>
<rdf:RDF xmlns="http://example.org/test#"
     xml:base="http://example.org/test"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:xml="http://www.w3.org/XML/1998/namespace"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    <owl:Ontology rdf:about="http://example.org/test"/>
    
    <!-- Test class -->
    <owl:Class rdf:about="http://example.org/test#TestClass">
        <rdfs:label xml:lang="en">Test Class</rdfs:label>
    </owl:Class>
</rdf:RDF>"""
    return content

@pytest.fixture
def mock_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("DATASET_SIZE", "test")
    monkeypatch.setenv("ONTOLOGIES_SOURCE_FILE", "config/ontologies_source_test.txt")
    monkeypatch.setenv("SKIP_NON_CORE_ANALYSIS", "true")
    monkeypatch.setenv("ROBOT_JAVA_ARGS", "-Xmx8g")
    monkeypatch.setenv("ENABLE_MEMORY_MONITORING", "false")
    
@pytest.fixture
def mock_robot_command(monkeypatch):
    """Mock ROBOT command execution."""
    def mock_run(*args, **kwargs):
        # Create a dummy output file if needed
        cmd = args[0] if args else kwargs.get('args', [])
        if isinstance(cmd, list) and 'robot' in str(cmd):
            # Find output file from command
            for i, arg in enumerate(cmd):
                if arg == '-o' and i + 1 < len(cmd):
                    output_file = cmd[i + 1]
                    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_file).write_text('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
        
        # Return successful result
        class MockResult:
            returncode = 0
            stdout = b"Success"
            stderr = b""
        
        return MockResult()
    
    # Mock shutil.which to find robot
    def mock_which(cmd):
        if cmd == 'robot':
            return '/usr/bin/robot'
        return None
    
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: type('MockPopen', (), {
        'poll': lambda self: 0,
        'wait': lambda self: 0,
        'returncode': 0
    })())
    monkeypatch.setattr("shutil.which", mock_which)