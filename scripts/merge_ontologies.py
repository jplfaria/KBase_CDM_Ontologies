# merge_ontologies.py
import os
import subprocess
from typing import Optional, List
from pathlib import Path
from enhanced_download import get_output_directories, is_test_mode

def merge_ontologies(
    repo_path: str,
    input_dir_name: str = 'ontology_data_owl',
    output_filename: str = 'CDM_merged_ontologies.owl'
) -> bool:
    """
    Merge multiple ontology files using ROBOT tool and remove specific axioms.
    
    Args:
        repo_path (str): Path to the repository root directory
        input_dir_name (str): Name of input directory within repo_path
        output_filename (str): Name of output OWL file
    
    Returns:
        bool: True if merge was successful, False otherwise
    
    Raises:
        FileNotFoundError: If input directory doesn't exist
        subprocess.CalledProcessError: If ROBOT command fails
    """
    try:
        # Setup paths - support test configuration
        test_mode = is_test_mode()
        ontology_data_path, _, outputs_path, version_dir = get_output_directories(repo_path, test_mode)
        
        input_dir = ontology_data_path
        output_dir = outputs_path
        
        print(f"🔧 Mode: {'TEST' if test_mode else 'PRODUCTION'}")
        print(f"📁 Input directory: {input_dir}")
        print(f"📁 Output directory: {output_dir}")
        
        # Find ROBOT executable in PATH
        import shutil
        robot_path = shutil.which('robot')
        if not robot_path:
            raise FileNotFoundError("ROBOT executable not found. Please ensure ROBOT is installed and in your PATH.")
        
        print(f"Using ROBOT at: {robot_path}")
        print(f"Looking for ontology files in: {input_dir}")
        
        # Validate input directory exists
        if not os.path.isdir(input_dir):
            raise FileNotFoundError(f"Input directory '{input_dir}' not found")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create full output path
        output_file = os.path.join(output_dir, output_filename)
        
        # Set Java memory arguments for ROBOT
        os.environ['ROBOT_JAVA_ARGS'] = '-Xmx4000G -XX:+UseParallelGC'
        
        # Get list of ontology files with full paths
        ontology_files = [
            os.path.join(input_dir, f) 
            for f in os.listdir(input_dir) 
            if f.endswith(('.owl', '.ofn', '.obo'))
        ]
        
        print(f"Found {len(ontology_files)} ontology files:")
        for f in ontology_files:
            print(f"  - {f}")
            # Verify each file exists and is readable
            if not os.path.exists(f):
                raise FileNotFoundError(f"Ontology file not found: {f}")
            if not os.access(f, os.R_OK):
                raise PermissionError(f"Cannot read ontology file: {f}")
            
        if not ontology_files:
            raise FileNotFoundError(f"No ontology files found in '{input_dir}'")
            
        # Get just the filenames and create merged list
        ontology_filenames = [os.path.basename(f) for f in ontology_files]
        # Use test-specific filename in test mode
        merged_filename = 'ontologies_merged_test.txt' if test_mode else 'ontologies_merged.txt'
        merged_list_path = os.path.join(repo_path, 'config', merged_filename)
        with open(merged_list_path, 'w') as f:
            for filename in sorted(ontology_filenames):
                f.write(f"{filename}\n")
        print(f"Created list of merged ontologies at: {merged_list_path}")
        
        # Build ROBOT command
        robot_command = ['robot', 'merge']
        
        # Add annotate-defined-by parameter
        robot_command.extend(['--annotate-defined-by', 'true'])
        
        # Add input files
        for ontology_file in ontology_files:
            robot_command.extend(['--input', ontology_file])
        
        # Remove disjoint axioms
        robot_command.extend([
            'remove', '--axioms', 'disjoint',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        # Remove 'owl:Nothing' term
        robot_command.extend([
            'remove', '--term', 'owl:Nothing',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        # Add output file
        robot_command.extend(['--output', output_file])
        
        print(f"Saving output to: {output_file}")
        print(f"\nExecuting command:\n{' '.join(robot_command)}")
        
        # Check if memory monitoring is enabled
        enable_monitoring = os.getenv('ENABLE_MEMORY_MONITORING', 'false').lower() == 'true'
        
        try:
            if enable_monitoring:
                # Use memory monitor
                print("🔍 Memory monitoring enabled - tracking ROBOT memory usage")
                monitor_script = os.path.join(os.path.dirname(__file__), 'memory_monitor.py')
                monitor_command = [
                    'python3', monitor_script,
                    'ROBOT_merge',
                    ' '.join(robot_command),
                    repo_path,
                    str(os.getenv('MEMORY_MONITOR_INTERVAL', '15'))
                ]
                result = subprocess.run(monitor_command, check=True)
                return_code = result.returncode
            else:
                # Run ROBOT command normally with more detailed output
                result = subprocess.run(
                    robot_command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                print("\nROBOT Output:")
                if result.stdout:
                    print(result.stdout)
                return_code = result.returncode
            
            print(f"Successfully merged ontologies into {output_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            print("\nError occurred during ROBOT execution:")
            print(f"Return code: {e.returncode}")
            print("\nCommand output:")
            if e.stdout:
                print("STDOUT:")
                print(e.stdout)
            if e.stderr:
                print("STDERR:")
                print(e.stderr)
            print("\nFull command that failed:")
            print(' '.join(robot_command))
            return False
            
    except Exception as e:
        print(f"\nUnexpected error occurred:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    # If run directly, merge ontologies from the current directory
    repo_path = os.getcwd()
    success = merge_ontologies(repo_path)
    if success:
        print("✅ Merge completed successfully!")
    else:
        print("❌ Merge failed!")
        exit(1)