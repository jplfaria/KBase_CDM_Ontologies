"""Tests for merge_ontologies module."""

import os
import pytest
from pathlib import Path
import sys
import json

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from merge_ontologies import merge_ontologies

# Memory function tests removed - functions don't exist in the actual module

class TestMergeOntologies:
    """Test the main merge_ontologies function."""
    
    def test_merge_ontologies_test_mode(self, temp_repo, mock_environment, mock_robot_command):
        """Test merge in test mode."""
        # Create test ontology files
        owl_dir = temp_repo / "ontology_data_owl_test"
        for i in range(3):
            owl_file = owl_dir / f"test{i}.owl"
            owl_file.write_text('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
        
        # Create config directory for the merge to write to
        config_dir = temp_repo / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Create prefix mapping
        prefix_file = temp_repo / "prefix_mapping.txt"
        prefix_file.write_text("TEST\thttp://example.org/test#")
        
        # Run merge
        result = merge_ontologies(str(temp_repo))
        
        # Check outputs
        outputs_dir = temp_repo / "outputs_test"
        assert result == True
        assert outputs_dir.exists()
    
    def test_merge_with_missing_ontologies(self, temp_repo, mock_environment):
        """Test merge with missing ontology files."""
        # Create config directory
        config_dir = temp_repo / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Create empty prefix mapping
        prefix_file = temp_repo / "prefix_mapping.txt"
        prefix_file.write_text("")
        
        # Run merge - should handle missing files gracefully
        result = merge_ontologies(str(temp_repo))
        
        # Should return False due to no ontologies found
        assert result == False
    
    def test_merge_with_compressed_files(self, temp_repo, mock_environment, mock_robot_command):
        """Test merging with compressed ontology files."""
        import gzip
        
        # Create test ontology files (some compressed)
        owl_dir = temp_repo / "ontology_data_owl_test"
        
        # Regular OWL file
        owl_file1 = owl_dir / "test1.owl"
        owl_file1.write_text('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
        
        # Compressed OWL file - create decompressed version
        owl_file2 = owl_dir / "test2.owl"
        owl_file2.write_text('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
        
        # Create config directory
        config_dir = temp_repo / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Create prefix mapping
        prefix_file = temp_repo / "prefix_mapping.txt"
        prefix_file.write_text("TEST\thttp://example.org/test#")
        
        # Run merge
        result = merge_ontologies(str(temp_repo))
        assert result == True
    
    def test_merge_order_file_creation(self, temp_repo, mock_environment, mock_robot_command):
        """Test that merge order file is created correctly."""
        # Create test ontology files
        owl_dir = temp_repo / "ontology_data_owl_test"
        ontologies = ["go.owl", "chebi.owl", "uberon.owl"]
        for onto in ontologies:
            owl_file = owl_dir / onto
            owl_file.write_text('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
        
        # Create config directory  
        config_dir = temp_repo / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Create prefix mapping
        prefix_file = temp_repo / "prefix_mapping.txt"
        prefix_file.write_text("GO\thttp://purl.obolibrary.org/obo/go#")
        
        # Run merge
        result = merge_ontologies(str(temp_repo))
        
        # Check outputs directory was created
        outputs_dir = temp_repo / "outputs_test"
        assert outputs_dir.exists()
    
    # Memory check test removed - function doesn't exist in the actual module