"""Tests for analyze_core_ontologies module."""

import os
import json
import pytest
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from analyze_core_ontologies import (
    normalize_iri, classify_ontology, analyze_ontology,
    check_obo_foundry_availability, analyze_core_ontologies
)

class TestNormalizeIRI:
    """Test IRI normalization functionality."""
    
    def test_normalize_obo_iri(self):
        """Test normalizing standard OBO IRIs."""
        assert normalize_iri("http://purl.obolibrary.org/obo/GO_0008150") == "http://purl.obolibrary.org/obo/go"
        assert normalize_iri("http://purl.obolibrary.org/obo/CHEBI_24431") == "http://purl.obolibrary.org/obo/chebi"
        assert normalize_iri("http://purl.obolibrary.org/obo/UBERON_0000001") == "http://purl.obolibrary.org/obo/uberon"
    
    def test_normalize_ncbitaxon_special_case(self):
        """Test NCBITaxon special handling."""
        assert normalize_iri("http://purl.obolibrary.org/obo/NCBITaxon_9606") == "http://purl.obolibrary.org/obo/ncbitaxon"
    
    def test_normalize_non_obo_iri(self):
        """Test that non-OBO IRIs return None."""
        assert normalize_iri("http://example.org/ontology/term") is None
        assert normalize_iri("http://www.w3.org/2002/07/owl#Thing") is None
    
    def test_normalize_empty_iri(self):
        """Test empty/None IRI handling."""
        assert normalize_iri(None) is None
        assert normalize_iri("") is None

class TestClassifyOntology:
    """Test ontology classification logic."""
    
    def test_classify_base_ontology(self):
        """Test classification of base ontologies."""
        analysis = {
            'has_imports': False,
            'own_terms': ['term1', 'term2', 'term3'],
            'external_terms': []
        }
        result = classify_ontology(analysis, "go-base.owl")
        assert "Base" in result or "Potential Base" in result
    
    def test_classify_non_base_ontology(self):
        """Test classification of non-base ontologies."""
        analysis = {
            'has_imports': True,
            'own_terms': ['term1'],
            'external_terms': ['ext1', 'ext2', 'ext3']
        }
        result = classify_ontology(analysis, "go.owl")
        assert "Non-Base" in result
    
    def test_classify_with_base_version_available(self, monkeypatch):
        """Test classification when base version exists in OBO Foundry."""
        def mock_check_obo(*args):
            return (True, "http://purl.obolibrary.org/obo/go/go-base.owl")
        
        monkeypatch.setattr("analyze_core_ontologies.check_obo_foundry_availability", mock_check_obo)
        
        analysis = {
            'has_imports': False,
            'own_terms': ['term1', 'term2'],
            'external_terms': []
        }
        result = classify_ontology(analysis, "go.owl")
        assert "Non-Base" in result
        assert "Base version available" in result

class TestAnalyzeOntology:
    """Test ontology analysis functionality."""
    
    def test_analyze_valid_owl_file(self, tmp_path, mini_owl_file):
        """Test analyzing a valid OWL file."""
        owl_file = tmp_path / "test.owl"
        owl_file.write_text(mini_owl_file)
        
        result = analyze_ontology(str(owl_file))
        assert result is not None
        assert 'file' in result
        assert 'has_imports' in result
        assert 'ontology_iri' in result
        assert 'own_terms' in result
        assert 'external_terms' in result
    
    def test_analyze_invalid_file(self, tmp_path):
        """Test analyzing an invalid file."""
        invalid_file = tmp_path / "invalid.owl"
        invalid_file.write_text("This is not valid XML")
        
        result = analyze_ontology(str(invalid_file))
        assert result is None
    
    def test_analyze_nonexistent_file(self):
        """Test analyzing a non-existent file."""
        result = analyze_ontology("/path/that/does/not/exist.owl")
        assert result is None

class TestAnalyzeCoreOntologies:
    """Test the main analyze_core_ontologies function."""
    
    def test_analyze_core_ontologies_basic(self, temp_repo, sample_ontology_source_file, 
                                          mock_environment, monkeypatch):
        """Test basic functionality of analyze_core_ontologies."""
        # Mock download function
        def mock_download(url, output_path, repo_path):
            # Create a dummy file
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
            return True
        
        monkeypatch.setattr("analyze_core_ontologies.download_ontology", mock_download)
        
        # Run analysis
        analyze_core_ontologies(str(temp_repo))
        
        # Check outputs were created
        outputs_base = temp_repo / "outputs_test"
        # Find the timestamped run directory
        run_dirs = [d for d in outputs_base.glob("run_*") if d.is_dir()]
        assert len(run_dirs) > 0, "No run directory found"
        outputs_dir = run_dirs[0]  # Get the first (and should be only) run directory
        
        assert (outputs_dir / "core_ontologies_analysis.json").exists()
        assert (outputs_dir / "core_onto_unique_external_terms.tsv").exists()
        assert (outputs_dir / "core_onto_unique_external_subjects.tsv").exists()
    
    def test_analyze_with_local_files(self, temp_repo, mock_environment):
        """Test analyzing local ontology files."""
        # Create source file with local entries
        source_file = temp_repo / "config" / "ontologies_source_test.txt"
        source_file.write_text("seed\nmetacyc\nkegg")
        
        # Create local OWL files
        owl_dir = temp_repo / "ontology_data_owl_test"
        for name in ["seed.owl", "metacyc.owl", "kegg.owl"]:
            owl_file = owl_dir / name
            owl_file.write_text('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
        
        # Run analysis
        analyze_core_ontologies(str(temp_repo))
        
        # Check outputs
        outputs_base = temp_repo / "outputs_test"
        # Find the timestamped run directory
        run_dirs = [d for d in outputs_base.glob("run_*") if d.is_dir()]
        assert len(run_dirs) > 0, "No run directory found"
        outputs_dir = run_dirs[0]  # Get the first (and should be only) run directory
        
        assert (outputs_dir / "core_ontologies_analysis.json").exists()
    
    def test_analyze_with_compressed_files(self, temp_repo, mock_environment, monkeypatch):
        """Test handling of compressed .gz files."""
        import gzip
        
        # Mock download that creates .gz file
        def mock_download(url, output_path, repo_path):
            if url.endswith('.gz'):
                # Create compressed file
                gz_path = output_path
                decompressed_path = output_path[:-3]  # Remove .gz
                
                Path(gz_path).parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(gz_path, 'wb') as f:
                    f.write(b'<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
                
                # Simulate decompression
                Path(decompressed_path).write_bytes(b'<?xml version="1.0"?><rdf:RDF></rdf:RDF>')
            return True
        
        monkeypatch.setattr("analyze_core_ontologies.download_ontology", mock_download)
        
        # Create source file with .gz URL
        source_file = temp_repo / "config" / "ontologies_source_test.txt"
        source_file.write_text("http://example.org/test.owl.gz")
        
        # Run analysis
        analyze_core_ontologies(str(temp_repo))
        
        # Check that decompressed file was analyzed
        outputs_base = temp_repo / "outputs_test"
        # Find the timestamped run directory
        run_dirs = [d for d in outputs_base.glob("run_*") if d.is_dir()]
        assert len(run_dirs) > 0, "No run directory found"
        outputs_dir = run_dirs[0]  # Get the first (and should be only) run directory
        
        assert (outputs_dir / "core_ontologies_analysis.json").exists()