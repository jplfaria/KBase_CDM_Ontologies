#!/usr/bin/env python3
"""
Self-contained pseudo-base ontology creator for order testing.
Creates base versions of non-base ontologies locally.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def extract_prefix_from_filename(filename):
    """Extract ontology prefix from filename."""
    # Remove extension and -base suffix if present
    base_name = filename.split('.')[0].replace('-base', '')
    # Convert to uppercase for prefix
    return f"http://purl.obolibrary.org/obo/{base_name.upper()}_"

def create_pseudo_base_version(input_file, output_file, data_dir):
    """Create a pseudo-base version of an ontology using ROBOT."""
    
    print(f"🔧 Creating base version: {os.path.basename(input_file)} → {os.path.basename(output_file)}")
    
    # Find ROBOT executable
    robot_path = shutil.which('robot')
    if not robot_path:
        print(f"❌ ROBOT executable not found in PATH")
        return False
    
    # Get base IRI from filename
    base_iri = extract_prefix_from_filename(os.path.basename(input_file))
    print(f"   Using base IRI: {base_iri}")
    
    # Build ROBOT command (matching the main pipeline approach)
    robot_command = [
        'robot', 'remove',
        '--input', input_file,
        '--base-iri', base_iri,
        '--axioms', 'external',
        '--preserve-structure', 'false',
        '--trim', 'false',
        'remove', '--select', 'imports',
        '--trim', 'false',
        '--output', output_file
    ]
    
    print(f"   Command: {' '.join(robot_command[:8])}...")
    
    try:
        result = subprocess.run(
            robot_command,
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per ontology
        )
        
        if os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"   ✅ Created: {os.path.basename(output_file)} ({size_mb:.1f} MB)")
            return True
        else:
            print(f"   ❌ Output file not created: {output_file}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Timeout after 5 minutes")
        return False
    except subprocess.CalledProcessError as e:
        print(f"   ❌ ROBOT failed:")
        if e.stderr:
            print(f"      STDERR: {e.stderr[:200]}...")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        return False

def create_all_pseudo_base_versions():
    """Create pseudo-base versions for all non-base ontologies."""
    
    # Get script directory and set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    testing_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(testing_dir, 'data')
    source_file = os.path.join(testing_dir, 'ontologies_source_full.txt')
    
    print(f"🔧 Creating Pseudo-Base Versions")
    print(f"📁 Data directory: {data_dir}")
    
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        print(f"   Run download_ontologies.py first!")
        return False
    
    # Identify non-base ontologies that need pseudo-base versions
    non_base_ontologies = [
        'bfo.owl',
        'foodon.owl', 
        'iao.owl',
        'omo.owl',
        'po.owl'
    ]
    
    print(f"\\n📋 Non-base ontologies to process:")
    for ont in non_base_ontologies:
        print(f"  • {ont}")
    
    successful = 0
    failed = 0
    
    for ontology in non_base_ontologies:
        input_path = os.path.join(data_dir, ontology)
        base_name = ontology.replace('.owl', '-base.owl')
        output_path = os.path.join(data_dir, base_name)
        
        print(f"\\n[{successful + failed + 1}/{len(non_base_ontologies)}] Processing {ontology}:")
        
        # Check if input exists
        if not os.path.exists(input_path):
            print(f"   ❌ Input file not found: {input_path}")
            failed += 1
            continue
        
        # Check if output already exists
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"   ⏭️  Base version already exists: {base_name} ({size_mb:.1f} MB)")
            successful += 1
            continue
        
        # Create pseudo-base version
        if create_pseudo_base_version(input_path, output_path, data_dir):
            successful += 1
        else:
            failed += 1
    
    # Summary
    print(f"\\n" + "=" * 60)
    print(f"🔧 PSEUDO-BASE CREATION SUMMARY")
    print(f"=" * 60)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    # List all ontology files with sizes
    print(f"\\n📋 All ontology files in data/:")
    files = []
    for filename in os.listdir(data_dir):
        if filename.endswith(('.owl', '.ofn', '.obo')):
            file_path = os.path.join(data_dir, filename)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            is_base = '-base' in filename
            files.append((filename, size_mb, is_base))
    
    # Sort by type then size
    files.sort(key=lambda x: (not x[2], -x[1]))  # Base first, then by size desc
    
    base_count = 0
    non_base_count = 0
    total_size = 0
    
    for filename, size_mb, is_base in files:
        marker = "📘" if is_base else "📗"
        print(f"  {marker} {filename:30} {size_mb:8.1f} MB")
        if is_base:
            base_count += 1
        else:
            non_base_count += 1
        total_size += size_mb
    
    print(f"\\n📊 Dataset statistics:")
    print(f"  📘 Base versions: {base_count}")
    print(f"  📗 Non-base versions: {non_base_count}")
    print(f"  📁 Total size: {total_size:.1f} MB")
    
    if failed > 0:
        print(f"\\n⚠️  {failed} pseudo-base creations failed.")
        return False
    else:
        print(f"\\n🎉 All {successful} pseudo-base versions created successfully!")
        return True

if __name__ == "__main__":
    success = create_all_pseudo_base_versions()
    sys.exit(0 if success else 1)