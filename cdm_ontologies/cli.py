#!/usr/bin/env python3
"""Command-line interface for CDM Ontologies Pipeline."""

import sys
import os
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
repo_path = Path(__file__).parent.parent
scripts_path = repo_path / "scripts"
sys.path.insert(0, str(scripts_path))

# Import workflow functions
from analyze_core_ontologies import analyze_core_ontologies
from analyze_non_core_ontologies import analyze_non_core_ontologies
from create_pseudo_base_ontology import create_pseudo_base_ontologies
from merge_ontologies import merge_ontologies
from create_semantic_sql_db import create_semantic_sql_db
from extract_sql_tables_to_tsv import extract_sql_tables_to_tsv
from create_parquet_files import create_parquet_files
from resource_check import check_system_resources


def setup_logging(verbose=False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/cdm_ontologies.log'),
            logging.StreamHandler()
        ]
    )


def timestamp_print(message):
    """Print a message with timestamp prefix."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def fix_docker_permissions():
    """Fix permissions for Docker-created files."""
    try:
        uid = os.getuid()
        gid = os.getgid()
        
        # Directories to fix
        dirs_to_fix = [
            'outputs', 'outputs_test',
            'ontology_data_owl', 'ontology_data_owl_test',
            'logs', 'results', 'data'
        ]
        
        # Build the chown command
        dirs_str = ' '.join(f'/workspace/{d}' for d in dirs_to_fix)
        
        # Run Docker to fix permissions
        cmd = [
            'docker', 'run', '--rm',
            '-v', f'{os.getcwd()}:/workspace',
            '--user', 'root',
            'alpine:latest',
            'sh', '-c',
            f'chown -R {uid}:{gid} {dirs_str} 2>/dev/null || true'
        ]
        
        subprocess.run(cmd, capture_output=True)
        logging.debug("Fixed Docker file permissions")
    except Exception as e:
        logging.debug(f"Permission fix skipped: {e}")


def run_all(args):
    """Run the complete workflow."""
    timestamp_print("Starting CDM Ontologies Workflow...")
    
    # Resource check
    if not args.skip_resource_check and not os.getenv('SKIP_RESOURCE_CHECK', '').lower() == 'true':
        timestamp_print("🔍 Checking system resources...")
        success, message = check_system_resources()
        print(message)
        if not success:
            timestamp_print("⚠️  Resource check failed. Use --skip-resource-check to override.")
            return 1
    
    # Step 1: Analyze Core Ontologies
    timestamp_print("Step 1: Analyzing Core Ontologies...")
    try:
        analyze_core_ontologies(str(repo_path))
        timestamp_print("Step 1: Completed analyzing core ontologies")
    except Exception as e:
        logging.error(f"Failed to analyze core ontologies: {e}")
        timestamp_print(f"Step 1: Failed - {e}")
        if not args.continue_on_error:
            return 1
    
    # Step 2: Analyze Non-Core Ontologies
    timestamp_print("Step 2: Analyzing Non-Core Ontologies...")
    try:
        analyze_non_core_ontologies(str(repo_path))
        timestamp_print("Step 2: Completed analyzing non-core ontologies")
    except Exception as e:
        logging.error(f"Failed to analyze non-core ontologies: {e}")
        timestamp_print(f"Step 2: Failed - {e}")
        if not args.continue_on_error:
            return 1
    
    # Step 3: Create Pseudo Base Ontologies
    timestamp_print("Step 3: Creating Pseudo Base Ontologies...")
    try:
        create_pseudo_base_ontologies(str(repo_path))
        timestamp_print("Step 3: Completed creating pseudo base ontologies")
    except Exception as e:
        logging.error(f"Failed to create pseudo base ontologies: {e}")
        timestamp_print(f"Step 3: Failed - {e}")
        if not args.continue_on_error:
            return 1
    
    # Step 4: Merge Ontologies
    timestamp_print("Step 4: Merging Ontologies...")
    try:
        if not merge_ontologies(str(repo_path)):
            raise Exception("Ontology merge failed")
        timestamp_print("Step 4: Completed merging ontologies")
    except Exception as e:
        logging.error(f"Failed to merge ontologies: {e}")
        timestamp_print(f"Step 4: Failed - {e}")
        if not args.continue_on_error:
            return 1
    
    # Step 5: Create Semantic SQL Database
    timestamp_print("Step 5: Creating Semantic SQL Database...")
    try:
        if not create_semantic_sql_db(str(repo_path)):
            raise Exception("Database creation failed")
        timestamp_print("Step 5: Completed creating semantic SQL database")
    except Exception as e:
        logging.error(f"Failed to create database: {e}")
        timestamp_print(f"Step 5: Failed - {e}")
        if not args.continue_on_error:
            return 1
    
    # Step 6: Extract SQL Tables to TSV
    timestamp_print("Step 6: Extracting SQL Tables to TSV...")
    try:
        if not extract_sql_tables_to_tsv(str(repo_path)):
            raise Exception("TSV extraction failed")
        timestamp_print("Step 6: Completed extracting SQL tables to TSV")
    except Exception as e:
        logging.error(f"Failed to extract tables: {e}")
        timestamp_print(f"Step 6: Failed - {e}")
        if not args.continue_on_error:
            return 1
    
    # Step 7: Create Parquet Files
    timestamp_print("Step 7: Creating Parquet Files...")
    try:
        if not create_parquet_files(str(repo_path)):
            raise Exception("Parquet creation failed")
        timestamp_print("Step 7: Completed creating parquet files")
    except Exception as e:
        logging.error(f"Failed to create parquet files: {e}")
        timestamp_print(f"Step 7: Failed - {e}")
        if not args.continue_on_error:
            return 1
    
    # Fix Docker permissions if running outside Docker
    if 'DOCKER_CONTAINER' not in os.environ:
        fix_docker_permissions()
    
    timestamp_print("Workflow completed successfully!")
    return 0


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='CDM Ontologies Pipeline - Process and merge biological ontologies',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--continue-on-error', action='store_true',
                        help='Continue workflow even if a step fails')
    parser.add_argument('--skip-resource-check', action='store_true',
                        help='Skip system resource validation before running')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run all command
    parser_run_all = subparsers.add_parser('run-all', help='Run the complete workflow')
    
    # Individual step commands
    parser_analyze_core = subparsers.add_parser('analyze-core', 
                                                 help='Analyze core ontologies')
    parser_analyze_non_core = subparsers.add_parser('analyze-non-core', 
                                                     help='Analyze non-core ontologies')
    parser_create_base = subparsers.add_parser('create-base', 
                                                help='Create pseudo-base ontologies')
    parser_merge = subparsers.add_parser('merge', help='Merge ontologies')
    parser_create_db = subparsers.add_parser('create-db', 
                                              help='Create semantic SQL database')
    parser_extract = subparsers.add_parser('extract-tables', 
                                           help='Extract SQL tables to TSV')
    parser_parquet = subparsers.add_parser('create-parquet', 
                                           help='Create Parquet files from database')
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Execute the appropriate command
    if args.command == 'run-all':
        return run_all(args)
    elif args.command == 'analyze-core':
        analyze_core_ontologies(str(repo_path))
    elif args.command == 'analyze-non-core':
        analyze_non_core_ontologies(str(repo_path))
    elif args.command == 'create-base':
        create_pseudo_base_ontologies(str(repo_path))
    elif args.command == 'merge':
        if not merge_ontologies(str(repo_path)):
            return 1
    elif args.command == 'create-db':
        if not create_semantic_sql_db(str(repo_path)):
            return 1
    elif args.command == 'extract-tables':
        if not extract_sql_tables_to_tsv(str(repo_path)):
            return 1
    elif args.command == 'create-parquet':
        if not create_parquet_files(str(repo_path)):
            return 1
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())