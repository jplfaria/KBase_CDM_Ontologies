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
from run_summary import get_summary


def setup_logging(verbose=False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
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
    
    # Create a single output directory for this entire run
    from enhanced_download import is_test_mode
    test_mode = is_test_mode()
    
    # Use timestamp from environment if available (for consistent logging)
    timestamp = os.environ.get('WORKFLOW_TIMESTAMP')
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.environ['WORKFLOW_TIMESTAMP'] = timestamp
    
    outputs_base = os.path.join(repo_path, 'outputs_test' if test_mode else 'outputs')
    run_output_dir = os.path.join(outputs_base, f'run_{timestamp}')
    os.makedirs(run_output_dir, exist_ok=True)
    
    # Set environment variables
    os.environ['WORKFLOW_OUTPUT_DIR'] = run_output_dir
    
    print(f"📁 All outputs will be saved to: {run_output_dir}")
    
    # Get summary instance if available
    summary = get_summary()
    
    # Step 1: Analyze Core Ontologies
    timestamp_print("Step 1: Analyzing Core Ontologies...")
    if summary:
        summary.start_step("Analyze Core Ontologies", 1)
    try:
        analyze_core_ontologies(str(repo_path))
        timestamp_print("Step 1: Completed analyzing core ontologies")
        if summary:
            summary.end_step("Analyze Core Ontologies", "SUCCESS")
    except Exception as e:
        logging.error(f"Failed to analyze core ontologies: {e}")
        timestamp_print(f"Step 1: Failed - {e}")
        if summary:
            summary.end_step("Analyze Core Ontologies", "FAILED")
            summary.add_error(str(e))
        if not args.continue_on_error:
            return 1
    
    # Step 2: Analyze Non-Core Ontologies (can be skipped)
    skip_non_core = os.environ.get('SKIP_NON_CORE_ANALYSIS', 'false').lower() == 'true'
    if skip_non_core:
        timestamp_print("Step 2: Skipping Non-Core Ontology Analysis (SKIP_NON_CORE_ANALYSIS=true)")
    else:
        timestamp_print("Step 2: Analyzing Non-Core Ontologies...")
        if summary:
            summary.start_step("Analyze Non-Core Ontologies", 2)
        try:
            analyze_non_core_ontologies(str(repo_path))
            timestamp_print("Step 2: Completed analyzing non-core ontologies")
            if summary:
                summary.end_step("Analyze Non-Core Ontologies", "SUCCESS")
        except Exception as e:
            logging.error(f"Failed to analyze non-core ontologies: {e}")
            timestamp_print(f"Step 2: Failed - {e}")
            if summary:
                summary.end_step("Analyze Non-Core Ontologies", "FAILED")
                summary.add_error(str(e))
            if not args.continue_on_error:
                return 1
    
    # Step 3: Create Pseudo Base Ontologies
    timestamp_print("Step 3: Creating Pseudo Base Ontologies...")
    if summary:
        summary.start_step("Create Pseudo Base Ontologies", 3)
    try:
        create_pseudo_base_ontologies(str(repo_path))
        timestamp_print("Step 3: Completed creating pseudo base ontologies")
        if summary:
            summary.end_step("Create Pseudo Base Ontologies", "SUCCESS")
    except Exception as e:
        logging.error(f"Failed to create pseudo base ontologies: {e}")
        timestamp_print(f"Step 3: Failed - {e}")
        if summary:
            summary.end_step("Create Pseudo Base Ontologies", "FAILED")
            summary.add_error(str(e))
        if not args.continue_on_error:
            return 1
    
    # Step 4: Merge Ontologies
    timestamp_print("Step 4: Merging Ontologies...")
    if summary:
        summary.start_step("Merge Ontologies", 4)
    try:
        if not merge_ontologies(str(repo_path)):
            raise Exception("Ontology merge failed")
        timestamp_print("Step 4: Completed merging ontologies")
        if summary:
            summary.end_step("Merge Ontologies", "SUCCESS")
    except Exception as e:
        logging.error(f"Failed to merge ontologies: {e}")
        timestamp_print(f"Step 4: Failed - {e}")
        if summary:
            summary.end_step("Merge Ontologies", "FAILED")
            summary.add_error(str(e))
        if not args.continue_on_error:
            return 1
    
    # Step 5: Create Semantic SQL Database
    timestamp_print("Step 5: Creating Semantic SQL Database...")
    if summary:
        summary.start_step("Create Semantic SQL Database", 5)
    try:
        if not create_semantic_sql_db(str(repo_path)):
            raise Exception("Database creation failed")
        timestamp_print("Step 5: Completed creating semantic SQL database")
        if summary:
            summary.end_step("Create Semantic SQL Database", "SUCCESS")
    except Exception as e:
        logging.error(f"Failed to create database: {e}")
        timestamp_print(f"Step 5: Failed - {e}")
        if summary:
            summary.end_step("Create Semantic SQL Database", "FAILED")
            summary.add_error(str(e))
        if not args.continue_on_error:
            return 1
    
    # Step 6: Extract SQL Tables to TSV
    timestamp_print("Step 6: Extracting SQL Tables to TSV...")
    if summary:
        summary.start_step("Extract SQL Tables to TSV", 6)
    try:
        if not extract_sql_tables_to_tsv(str(repo_path)):
            raise Exception("TSV extraction failed")
        timestamp_print("Step 6: Completed extracting SQL tables to TSV")
        if summary:
            summary.end_step("Extract SQL Tables to TSV", "SUCCESS")
    except Exception as e:
        logging.error(f"Failed to extract tables: {e}")
        timestamp_print(f"Step 6: Failed - {e}")
        if summary:
            summary.end_step("Extract SQL Tables to TSV", "FAILED")
            summary.add_error(str(e))
        if not args.continue_on_error:
            return 1
    
    # Step 7: Create Parquet Files
    timestamp_print("Step 7: Creating Parquet Files...")
    if summary:
        summary.start_step("Create Parquet Files", 7)
    try:
        if not create_parquet_files(str(repo_path)):
            raise Exception("Parquet creation failed")
        timestamp_print("Step 7: Completed creating parquet files")
        if summary:
            summary.end_step("Create Parquet Files", "SUCCESS")
    except Exception as e:
        logging.error(f"Failed to create parquet files: {e}")
        timestamp_print(f"Step 7: Failed - {e}")
        if summary:
            summary.end_step("Create Parquet Files", "FAILED")
            summary.add_error(str(e))
        if not args.continue_on_error:
            return 1
    
    # Fix Docker permissions if running outside Docker
    if 'DOCKER_CONTAINER' not in os.environ:
        fix_docker_permissions()
    
    # Create symlink to latest run
    latest_link = os.path.join(outputs_base, 'latest')
    if os.path.islink(latest_link):
        os.unlink(latest_link)
    elif os.path.exists(latest_link):
        if os.path.isdir(latest_link):
            import shutil
            shutil.rmtree(latest_link)
        else:
            os.remove(latest_link)
    os.symlink(os.path.basename(run_output_dir), latest_link)
    
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
    else:
        # For individual commands, ensure we have a consistent output directory
        # if not already set by a parent process
        if 'WORKFLOW_OUTPUT_DIR' not in os.environ:
            from enhanced_download import is_test_mode
            test_mode = is_test_mode()
            
            # Use timestamp from environment if available
            timestamp = os.environ.get('WORKFLOW_TIMESTAMP')
            if not timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                os.environ['WORKFLOW_TIMESTAMP'] = timestamp
            
            outputs_base = os.path.join(repo_path, 'outputs_test' if test_mode else 'outputs')
            run_output_dir = os.path.join(outputs_base, f'run_{timestamp}')
            os.makedirs(run_output_dir, exist_ok=True)
            os.environ['WORKFLOW_OUTPUT_DIR'] = run_output_dir
            
            print(f"📁 Output directory: {run_output_dir}")
        
        # Now execute the command
        if args.command == 'analyze-core':
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