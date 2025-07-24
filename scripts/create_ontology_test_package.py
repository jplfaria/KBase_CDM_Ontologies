#!/usr/bin/env python3
"""Create a test package with seed.owl and modelseed.owl processing outputs."""

import os
import sys
import subprocess
import shutil
import tarfile
from pathlib import Path
import tempfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(cmd, cwd=None):
    """Run a shell command and return success status."""
    logging.info(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            logging.error(f"Command failed: {result.stderr}")
            return False
        return True
    except Exception as e:
        logging.error(f"Error running command: {e}")
        return False

def download_ontology(url, output_path):
    """Download an ontology file."""
    cmd = f"curl -L -o {output_path} {url}"
    return run_command(cmd)

def create_semsql_db(owl_file, db_file, prefixes_file=None):
    """Create SemanticSQL database from OWL file."""
    cmd = f"semsql make {db_file} -i {owl_file}"
    if prefixes_file and os.path.exists(prefixes_file):
        cmd += f" -P {prefixes_file}"
    return run_command(cmd)

def extract_table(db_file, table_name, output_format, output_path):
    """Extract a table from SemanticSQL database."""
    if output_format == "tsv":
        cmd = f"sqlite3 -header -separator '\t' {db_file} 'SELECT * FROM {table_name}' > {output_path}"
    elif output_format == "parquet":
        # First extract to TSV, then convert to parquet
        tsv_path = output_path.replace('.parquet', '.tsv')
        if extract_table(db_file, table_name, "tsv", tsv_path):
            cmd = f"""python -c "
import pandas as pd
df = pd.read_csv('{tsv_path}', sep='\\t')
df.to_parquet('{output_path}', index=False)
print(f'Created {output_path} with {{len(df)}} rows')
" """
            success = run_command(cmd)
            # Clean up TSV if parquet conversion succeeded
            if success and os.path.exists(tsv_path) and tsv_path != output_path.replace('.parquet', '.tsv'):
                os.remove(tsv_path)
            return success
    return run_command(cmd)

def convert_to_json(owl_file, json_file):
    """Convert OWL to JSON using ROBOT."""
    cmd = f"robot convert --input {owl_file} --output {json_file}"
    return run_command(cmd)

def merge_ontologies(owl1, owl2, output):
    """Merge two OWL files using ROBOT."""
    cmd = f"robot merge --input {owl1} --input {owl2} --output {output}"
    return run_command(cmd)

def process_ontology(name, owl_path, output_dir, prefixes_file=None):
    """Process a single ontology: create DB, extract tables, convert to JSON."""
    logging.info(f"Processing {name}...")
    
    # Create SemanticSQL database
    db_path = os.path.join(output_dir, f"{name}.db")
    if not create_semsql_db(owl_path, db_path, prefixes_file):
        logging.error(f"Failed to create database for {name}")
        return False
    
    # Extract tables
    tables = ["statements", "entailed_edge"]
    for table in tables:
        # TSV format
        tsv_path = os.path.join(output_dir, f"{name}_{table}.tsv")
        if not extract_table(db_path, table, "tsv", tsv_path):
            logging.warning(f"Failed to extract {table} table as TSV for {name}")
        
        # Parquet format
        parquet_path = os.path.join(output_dir, f"{name}_{table}.parquet")
        if not extract_table(db_path, table, "parquet", parquet_path):
            logging.warning(f"Failed to extract {table} table as Parquet for {name}")
    
    # Convert to JSON (only for seed.owl)
    if name == "seed":
        json_path = os.path.join(output_dir, f"{name}.json")
        if not convert_to_json(owl_path, json_path):
            logging.warning(f"Failed to convert {name} to JSON")
    
    return True

def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python create_ontology_test_package.py <output_directory>")
        print("Example: python create_ontology_test_package.py /scratch/jplfaria/ontologies_play")
        sys.exit(1)
    
    output_base = sys.argv[1]
    
    # Create working directory
    work_dir = os.path.join(output_base, "ontology_test_package")
    os.makedirs(work_dir, exist_ok=True)
    os.chdir(work_dir)
    
    logging.info(f"Working directory: {work_dir}")
    
    # URLs for ontologies
    seed_url = "https://raw.githubusercontent.com/Knowledge-Graph-Hub/semantic-units/main/seed.owl"
    modelseed_url = "https://raw.githubusercontent.com/ModelSEED/ModelSEEDDatabase/master/Biochemistry/Ontologies/modelseed_ontology.owl"
    
    # Check for custom prefixes file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    prefixes_file = os.path.join(repo_root, "semsql_custom_prefixes", "prefixes.yaml")
    if not os.path.exists(prefixes_file):
        prefixes_file = None
        logging.warning("Custom prefixes file not found, using defaults")
    
    # Download ontologies
    logging.info("Downloading ontologies...")
    if not download_ontology(seed_url, "seed.owl"):
        logging.error("Failed to download seed.owl")
        return 1
    
    if not download_ontology(modelseed_url, "modelseed.owl"):
        logging.error("Failed to download modelseed.owl")
        return 1
    
    # Process individual ontologies
    if not process_ontology("seed", "seed.owl", work_dir, prefixes_file):
        return 1
    
    if not process_ontology("modelseed", "modelseed.owl", work_dir, prefixes_file):
        return 1
    
    # Create merged ontology
    logging.info("Creating merged ontology...")
    merged_owl = "modelseed_unified.owl"
    if not merge_ontologies("seed.owl", "modelseed.owl", merged_owl):
        logging.error("Failed to merge ontologies")
        return 1
    
    # Process merged ontology
    if not process_ontology("modelseed_unified", merged_owl, work_dir, prefixes_file):
        return 1
    
    # Create package
    package_name = "ontology_test_package.tar.gz"
    package_path = os.path.join(output_base, package_name)
    
    logging.info(f"Creating package: {package_path}")
    
    # List all files to include
    files_to_package = []
    for ext in ['.owl', '.db', '.tsv', '.parquet', '.json']:
        files_to_package.extend(Path(work_dir).glob(f"*{ext}"))
    
    # Create tar.gz archive
    with tarfile.open(package_path, "w:gz") as tar:
        for file_path in files_to_package:
            arcname = os.path.basename(file_path)
            logging.info(f"Adding {arcname} to package")
            tar.add(file_path, arcname=arcname)
    
    # Create a summary file
    summary_path = os.path.join(output_base, "package_contents.txt")
    with open(summary_path, 'w') as f:
        f.write("Ontology Test Package Contents\n")
        f.write("=" * 50 + "\n\n")
        f.write("OWL Files:\n")
        f.write("- seed.owl\n")
        f.write("- modelseed.owl\n")
        f.write("- modelseed_unified.owl (merged)\n\n")
        f.write("For each ontology:\n")
        f.write("- {name}.db (SemanticSQL database)\n")
        f.write("- {name}_statements.tsv\n")
        f.write("- {name}_statements.parquet\n")
        f.write("- {name}_entailed_edge.tsv\n")
        f.write("- {name}_entailed_edge.parquet\n\n")
        f.write("Additional:\n")
        f.write("- seed.json (ROBOT conversion of seed.owl)\n\n")
        f.write(f"Package location: {package_path}\n")
        f.write(f"Package size: {os.path.getsize(package_path) / (1024*1024):.2f} MB\n")
    
    logging.info(f"Package created successfully: {package_path}")
    logging.info(f"Summary written to: {summary_path}")
    
    # Clean up working directory (optional)
    # shutil.rmtree(work_dir)
    
    print(f"\n✅ Success! Package created at: {package_path}")
    print(f"📄 See summary at: {summary_path}")
    print(f"\nTo download to your local machine:")
    print(f"  scp jplfaria@poplar:{package_path} .")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())