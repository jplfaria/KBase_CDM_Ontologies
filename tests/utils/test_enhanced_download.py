"""Tests for enhanced_download module."""

import os
import pytest
from pathlib import Path
import sys
import json
import gzip
from unittest.mock import Mock, patch

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from enhanced_download import (
    get_output_directories, is_test_mode, download_with_retry,
    handle_compressed_file, download_ontology_with_versioning,
    download_ontology_safe, get_file_checksum
)

class TestOutputDirectories:
    """Test directory management functions."""
    
    def test_get_output_directories_production(self, temp_repo, monkeypatch):
        """Test getting production directories."""
        # Ensure we're not in test mode
        monkeypatch.delenv("ONTOLOGIES_SOURCE_FILE", raising=False)
        monkeypatch.delenv("WORKFLOW_OUTPUT_DIR", raising=False)
        ontology_data, non_base, outputs, version = get_output_directories(str(temp_repo), test_mode=False)
        
        assert "ontology_data_owl_test" not in str(ontology_data)
        assert "outputs_test" not in str(outputs)
        assert str(ontology_data).endswith("ontology_data_owl")
        assert "/outputs/run_" in str(outputs)  # Check for timestamped directory
        assert str(version).endswith("ontology_versions")
        
        # Check directories were created
        assert Path(ontology_data).exists()
        assert Path(non_base).exists()
        assert Path(outputs).exists()
        assert Path(version).exists()
    
    def test_get_output_directories_test(self, temp_repo):
        """Test getting test directories."""
        ontology_data, non_base, outputs, version = get_output_directories(str(temp_repo), test_mode=True)
        
        assert str(ontology_data).endswith("ontology_data_owl_test")
        assert "/outputs_test/run_" in str(outputs)  # Check for timestamped directory
        assert str(version).endswith("ontology_versions_test")
        
        # Check directories were created
        assert Path(ontology_data).exists()
        assert Path(non_base).exists()
        assert Path(outputs).exists()
        assert Path(version).exists()
    
    def test_is_test_mode(self, monkeypatch):
        """Test test mode detection."""
        # Test mode when source file contains 'test'
        monkeypatch.setenv("ONTOLOGIES_SOURCE_FILE", "ontologies_source_test.txt")
        assert is_test_mode() == True
        
        # Production mode
        monkeypatch.setenv("ONTOLOGIES_SOURCE_FILE", "ontologies_source.txt")
        assert is_test_mode() == False
        
        # Default (no env var)
        monkeypatch.delenv("ONTOLOGIES_SOURCE_FILE", raising=False)
        assert is_test_mode() == False

class TestDownloadFunctions:
    """Test download functionality."""
    
    def test_download_with_retry_success(self, monkeypatch):
        """Test successful download with retry."""
        mock_response = Mock()
        mock_response.content = b"test content"
        mock_response.raise_for_status = Mock()
        
        mock_get = Mock(return_value=mock_response)
        monkeypatch.setattr("requests.get", mock_get)
        
        result = download_with_retry("http://example.org/test.owl")
        
        assert result == mock_response
        mock_get.assert_called_once()
    
    def test_download_with_retry_failure_then_success(self, monkeypatch):
        """Test retry logic on failure."""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.content = b"test content"
        mock_response.raise_for_status = Mock()
        
        # Create an exception that requests would raise
        import requests
        mock_get = Mock(side_effect=[requests.exceptions.RequestException("Network error"), mock_response])
        monkeypatch.setattr("requests.get", mock_get)
        monkeypatch.setattr("time.sleep", Mock())  # Skip sleep in tests
        
        result = download_with_retry("http://example.org/test.owl", max_retries=2)
        
        assert result == mock_response
        assert mock_get.call_count == 2
    
    def test_download_with_retry_all_fail(self, monkeypatch):
        """Test when all retries fail."""
        import requests
        mock_get = Mock(side_effect=requests.exceptions.RequestException("Network error"))
        monkeypatch.setattr("requests.get", mock_get)
        monkeypatch.setattr("time.sleep", Mock())
        
        with pytest.raises(requests.exceptions.RequestException, match="Network error"):
            download_with_retry("http://example.org/test.owl", max_retries=2)
        
        assert mock_get.call_count == 2

class TestCompressedFileHandling:
    """Test compressed file handling."""
    
    def test_handle_compressed_gz_file(self, tmp_path):
        """Test handling .gz compressed files."""
        # Create mock response with gzipped content
        test_content = b'<?xml version="1.0"?><rdf:RDF></rdf:RDF>'
        compressed_content = gzip.compress(test_content)
        
        mock_response = Mock()
        mock_response.content = compressed_content
        
        output_path = tmp_path / "test.owl"
        
        # Handle compressed file
        handle_compressed_file(mock_response, str(output_path), "http://example.org/test.owl.gz")
        
        # Check decompressed file exists and has correct content
        assert output_path.exists()
        assert output_path.read_bytes() == test_content
        
        # Check .gz file was removed
        assert not (tmp_path / "test.owl.gz").exists()
    
    def test_handle_uncompressed_file(self, tmp_path):
        """Test handling regular uncompressed files."""
        test_content = b'<?xml version="1.0"?><rdf:RDF></rdf:RDF>'
        
        mock_response = Mock()
        mock_response.content = test_content
        
        output_path = tmp_path / "test.owl"
        
        # Handle uncompressed file
        handle_compressed_file(mock_response, str(output_path), "http://example.org/test.owl")
        
        # Check file exists with correct content
        assert output_path.exists()
        assert output_path.read_bytes() == test_content

class TestVersioning:
    """Test version tracking functionality."""
    
    def test_download_ontology_with_versioning_new_file(self, temp_repo, monkeypatch):
        """Test downloading a new file with versioning."""
        # Mock requests
        mock_response = Mock()
        mock_response.content = b"test content"
        mock_response.raise_for_status = Mock()
        mock_response.headers = {
            'ETag': '"test-etag"',
            'Content-Length': '12',
            'Last-Modified': 'Mon, 01 Jan 2024 00:00:00 GMT'
        }
        
        mock_get = Mock(return_value=mock_response)
        monkeypatch.setattr("requests.get", mock_get)
        
        # Mock version checking
        monkeypatch.setattr("enhanced_download.should_download", lambda *args: (True, "New file"))
        
        output_path = temp_repo / "test.owl"
        
        success, status, message = download_ontology_with_versioning(
            "http://example.org/test.owl",
            str(output_path),
            str(temp_repo)
        )
        
        assert success == True
        assert status == "new"
        assert output_path.exists()
    
    def test_download_ontology_safe_problematic_files(self, temp_repo):
        """Test skipping known problematic files."""
        # Test problematic patterns
        problematic_urls = [
            "http://example.org/cp.owl",
            "http://example.org/has.owl",
            "http://example.org/is.owl",
            "http://example.org/apollo.owl"
        ]
        
        for url in problematic_urls:
            filename = os.path.basename(url)
            output_path = temp_repo / filename
            
            result = download_ontology_safe(url, str(output_path), str(temp_repo))
            
            assert result == False
            assert not output_path.exists()

class TestChecksum:
    """Test checksum calculation."""
    
    def test_get_file_checksum_from_content(self):
        """Test checksum from byte content."""
        content = b"test content"
        checksum = get_file_checksum(content)
        
        assert len(checksum) == 64  # SHA256 hex digest length
        assert checksum == "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
    
    def test_get_file_checksum_from_file(self, tmp_path):
        """Test checksum from file path."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")
        
        checksum = get_file_checksum(str(test_file))
        
        assert len(checksum) == 64
        assert checksum == "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"