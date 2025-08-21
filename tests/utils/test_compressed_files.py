"""Tests for compressed file handling in version tracking."""

import os
import json
import gzip
import pytest
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from enhanced_download import download_ontology_with_versioning
from version_tracker import should_download, update_version_info, load_version_info


class TestCompressedFileHandling:
    """Test version tracking for compressed (.gz) files."""
    
    def test_compressed_file_version_tracking(self, tmp_path, mocker):
        """Test that compressed files are tracked correctly."""
        # Setup
        version_dir = tmp_path / "ontology_versions_test"
        version_dir.mkdir(parents=True)
        version_file = version_dir / "ontology_versions.json"
        ontology_dir = tmp_path / "ontology_data_owl_test"
        ontology_dir.mkdir(parents=True)
        
        # Create a mock compressed file
        test_content = b"test ontology content"
        compressed_content = gzip.compress(test_content)
        
        # Mock the download response
        mock_response = mocker.Mock()
        mock_response.content = compressed_content
        mock_response.headers = {
            'ETag': '"test-etag"',
            'Content-Length': str(len(compressed_content)),
            'Last-Modified': 'Mon, 01 Jan 2024 00:00:00 GMT'
        }
        mock_response.raise_for_status = mocker.Mock()
        
        mocker.patch('enhanced_download.download_with_retry', return_value=mock_response)
        # Mock test mode
        mocker.patch.dict('os.environ', {'ONTOLOGIES_SOURCE_FILE': 'ontologies_source_test.txt'})
        
        # Mock HEAD request to return same metadata
        mock_head_response = mocker.Mock()
        mock_head_response.headers = {
            'ETag': '"test-etag"',
            'Content-Length': str(len(compressed_content)),
            'Last-Modified': 'Mon, 01 Jan 2024 00:00:00 GMT'
        }
        mock_head_response.raise_for_status = mocker.Mock()
        mocker.patch('requests.head', return_value=mock_head_response)
        
        # Test downloading a .gz file
        url = "http://example.org/test.owl.gz"
        output_path = str(ontology_dir / "test.owl.gz")
        
        success, status, message = download_ontology_with_versioning(
            url, output_path, str(tmp_path), force_download=True
        )
        
        assert success is True
        assert status == "new"
        
        # Check that the decompressed file exists
        decompressed_path = str(ontology_dir / "test.owl")
        assert os.path.exists(decompressed_path)
        assert not os.path.exists(output_path)  # .gz file should be removed
        
        # Check version tracking
        version_info = load_version_info(str(version_file))
        assert "test.owl" in version_info  # Should use decompressed filename
        assert version_info["test.owl"]["url"] == url
        
        # Verify version info has correct structure
        stored_info = version_info["test.owl"]
        assert stored_info["url"] == url
        assert "checksum" in stored_info
        assert "remote_etag" in stored_info
        assert stored_info["remote_etag"] == "test-etag"
        
        # The key point is that version tracking is using the decompressed filename
        # even though the URL points to a .gz file
    
    def test_should_download_compressed_file(self, tmp_path):
        """Test should_download logic for compressed files."""
        version_file = tmp_path / "versions.json"
        
        # Create a decompressed file
        test_file = tmp_path / "test.owl"
        test_file.write_text("test content")
        
        # Update version info as if it was downloaded from a .gz URL
        update_version_info(
            str(version_file),
            "test.owl",  # Use decompressed filename
            "http://example.org/test.owl.gz",  # But track the .gz URL
            None,
            "abc123def456"
        )
        
        # Test should_download with the decompressed file path
        needs_download, reason = should_download(
            str(test_file),
            "http://example.org/test.owl.gz",
            str(version_file),
            check_remote=False
        )
        
        # Should not need download if checksum matches
        assert needs_download is True  # Will be true because checksums don't match
        assert reason == "checksum_mismatch"
        
        # Update with correct checksum
        import hashlib
        correct_checksum = hashlib.sha256(b"test content").hexdigest()
        update_version_info(
            str(version_file),
            "test.owl",
            "http://example.org/test.owl.gz",
            "abc123def456",
            correct_checksum
        )
        
        # Now should not need download
        needs_download2, reason2 = should_download(
            str(test_file),
            "http://example.org/test.owl.gz",
            str(version_file),
            check_remote=False
        )
        
        assert needs_download2 is False
        assert reason2 == "up_to_date"
    
    def test_mixed_compressed_uncompressed_files(self, tmp_path, mocker):
        """Test handling of both compressed and uncompressed files."""
        version_dir = tmp_path / "ontology_versions_test"
        version_dir.mkdir(parents=True)
        version_file = version_dir / "ontology_versions.json"
        ontology_dir = tmp_path / "ontology_data_owl_test"
        ontology_dir.mkdir(parents=True)
        
        # Mock responses
        def mock_download(url):
            response = mocker.Mock()
            if url.endswith('.gz'):
                response.content = gzip.compress(b"compressed content")
            else:
                response.content = b"uncompressed content"
            response.headers = {'ETag': '"etag"', 'Content-Length': '100'}
            response.raise_for_status = mocker.Mock()
            return response
        
        mocker.patch('enhanced_download.download_with_retry', side_effect=mock_download)
        # Mock test mode
        mocker.patch.dict('os.environ', {'ONTOLOGIES_SOURCE_FILE': 'ontologies_source_test.txt'})
        
        # Test compressed file
        success1, _, _ = download_ontology_with_versioning(
            "http://example.org/compressed.owl.gz",
            str(ontology_dir / "compressed.owl.gz"),
            str(tmp_path),
            force_download=True
        )
        
        # Test uncompressed file
        success2, _, _ = download_ontology_with_versioning(
            "http://example.org/uncompressed.owl",
            str(ontology_dir / "uncompressed.owl"),
            str(tmp_path),
            force_download=True
        )
        
        assert success1 is True
        assert success2 is True
        
        # Check files exist
        assert os.path.exists(str(ontology_dir / "compressed.owl"))  # Decompressed
        assert not os.path.exists(str(ontology_dir / "compressed.owl.gz"))  # Removed
        assert os.path.exists(str(ontology_dir / "uncompressed.owl"))
        
        # Check version tracking
        version_info = load_version_info(str(version_file))
        assert "compressed.owl" in version_info
        assert "uncompressed.owl" in version_info
        assert version_info["compressed.owl"]["url"] == "http://example.org/compressed.owl.gz"
        assert version_info["uncompressed.owl"]["url"] == "http://example.org/uncompressed.owl"