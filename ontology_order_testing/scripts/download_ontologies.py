#!/usr/bin/env python3
"""
Self-contained ontology downloader for order testing.
Downloads all ontologies to local data/ directory.
"""

import os
import sys
import requests
import gzip
import shutil
import time
from urllib.parse import urlparse
from pathlib import Path

def download_with_retry(url, max_retries=3, timeout=120):
    """Download with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"  Attempting download {attempt + 1}/{max_retries}: {url}")
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"  ⚠️  Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
            else:
                print(f"  ❌ All attempts failed for {url}: {str(e)}")
                raise e

def handle_compressed_file(response, output_path, url):
    """Handle compressed (.gz) file downloads."""
    if url.endswith('.gz'):
        # Save compressed file temporarily
        gz_path = output_path + '.gz'
        with open(gz_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Decompress
        print(f"    Decompressing {os.path.basename(gz_path)}...")
        with gzip.open(gz_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove compressed file
        os.remove(gz_path)
        print(f"    ✅ Decompressed to {os.path.basename(output_path)}")
    else:
        # Regular file download
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"    ✅ Downloaded {os.path.basename(output_path)}")

def download_ontology(url, data_dir):
    """Download a single ontology to the data directory."""
    
    # Extract filename from URL
    parsed_url = urlparse(url)
    if url.endswith('.gz'):
        filename = os.path.basename(parsed_url.path)[:-3]  # Remove .gz extension
    else:
        filename = os.path.basename(parsed_url.path)
    
    # Handle GitHub raw URLs
    if 'github.com' in url and 'blob' in url:
        url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob', '')
        print(f"  📦 Converting GitHub URL to raw: {url}")
    
    output_path = os.path.join(data_dir, filename)
    
    # Skip if already exists
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ⏭️  Already exists: {filename} ({size_mb:.1f} MB)")
        return True
    
    try:
        print(f"📥 Downloading: {filename}")
        response = download_with_retry(url)
        
        # Get file size for progress
        total_size = int(response.headers.get('content-length', 0))
        if total_size > 0:
            size_mb = total_size / (1024 * 1024)
            print(f"    Size: {size_mb:.1f} MB")
        
        handle_compressed_file(response, output_path, url)
        
        # Verify file was created and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            final_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  ✅ Successfully downloaded: {filename} ({final_size_mb:.1f} MB)")
            return True
        else:
            print(f"  ❌ Download failed: {filename} (file empty or missing)")
            return False
            
    except Exception as e:
        print(f"  ❌ Error downloading {filename}: {str(e)}")
        return False

def download_all_ontologies():
    """Download all ontologies from the source list."""
    
    # Get script directory and set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    testing_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(testing_dir, 'data')
    source_file = os.path.join(testing_dir, 'ontologies_source_full.txt')
    
    # Create data directory
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"🔍 Ontology Order Testing - Full Dataset Download")
    print(f"📁 Data directory: {data_dir}")
    print(f"📋 Source file: {source_file}")
    
    if not os.path.exists(source_file):
        print(f"❌ Source file not found: {source_file}")
        return False
    
    # Read ontology URLs
    ontology_urls = []
    with open(source_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                ontology_urls.append(line)
    
    print(f"\\n📊 Found {len(ontology_urls)} ontologies to download:")
    for i, url in enumerate(ontology_urls, 1):
        filename = os.path.basename(urlparse(url).path)
        if url.endswith('.gz'):
            filename = filename[:-3]
        print(f"  {i:2d}. {filename}")
    
    # Download each ontology
    print(f"\\n🚀 Starting downloads...")
    successful = 0
    failed = 0
    
    for i, url in enumerate(ontology_urls, 1):
        print(f"\\n[{i}/{len(ontology_urls)}] Processing: {url}")
        
        if download_ontology(url, data_dir):
            successful += 1
        else:
            failed += 1
    
    # Summary
    print(f"\\n" + "=" * 60)
    print(f"📊 DOWNLOAD SUMMARY")
    print(f"=" * 60)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Total files in data/: {len(os.listdir(data_dir))}")
    
    # List downloaded files with sizes
    print(f"\\n📋 Downloaded files:")
    files = []
    for filename in os.listdir(data_dir):
        if filename.endswith(('.owl', '.ofn', '.obo')):
            file_path = os.path.join(data_dir, filename)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            files.append((filename, size_mb))
    
    # Sort by size (largest first)
    files.sort(key=lambda x: x[1], reverse=True)
    total_size = 0
    for filename, size_mb in files:
        print(f"  {filename:30} {size_mb:8.1f} MB")
        total_size += size_mb
    
    print(f"\\n📁 Total dataset size: {total_size:.1f} MB")
    
    if failed > 0:
        print(f"\\n⚠️  {failed} downloads failed. You may want to retry those manually.")
        return False
    else:
        print(f"\\n🎉 All {successful} ontologies downloaded successfully!")
        return True

if __name__ == "__main__":
    success = download_all_ontologies()
    sys.exit(0 if success else 1)