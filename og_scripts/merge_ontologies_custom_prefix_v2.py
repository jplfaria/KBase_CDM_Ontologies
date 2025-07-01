import os
import subprocess
from typing import Optional, List

def merge_ontologies(
    repo_path: str,
    input_dir_name: str = 'ontology_data_owl_core',
    output_filename: str = 'CDM_merged_ontologies.owl',
    input_prefixes_dir_name: str = 'custom_prefixes',
    prefixes_file: Optional[str] = None,
    add_prefixes: bool = False,
    ontology_files_to_merge: Optional[List[str]] = None
) -> bool:
    """
    Merge multiple ontology files using ROBOT tool and optionally add custom prefixes.
    
    Args:
        repo_path (str): Path to the repository root directory
        input_dir_name (str): Name of input directory within repo_path
        output_filename (str): Name of output OWL file
        input_prefixes_dir_name (str): Name of directory containing custom prefixes
        prefixes_file (Optional[str]): Name of the JSON file containing custom prefixes
        add_prefixes (bool): Whether to add custom prefixes from the prefixes_file
        ontology_files_to_merge (Optional[List[str]]): List of specific ontology files to merge
    
    Returns:
        bool: True if merge was successful, False otherwise
    
    Raises:
        FileNotFoundError: If input directory or prefixes file doesn't exist
        subprocess.CalledProcessError: If ROBOT command fails
    """
    try:
        # Set up paths relative to repo root
        input_dir = os.path.join(repo_path, input_dir_name)
        output_dir = os.path.join(repo_path, 'outputs')
        input_prefixes_dir = os.path.join(repo_path, input_prefixes_dir_name)
        
        # Construct default path to robot executable
        robot_path = os.path.join(
            os.path.dirname(repo_path),
            'install_stuff',
            'robot',
            'robot'
        )
        
        # Verify robot exists
        if not os.path.exists(robot_path):
            raise FileNotFoundError(f"ROBOT executable not found at: {robot_path}")
        
        # Print ROBOT version for debugging
        try:
            robot_version_result = subprocess.run(
                [robot_path, '--version'],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Using ROBOT version: {robot_version_result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            print("Failed to retrieve ROBOT version.")
            print(f"Error: {e.stderr}")
        
        # Add robot to PATH
        robot_dir = os.path.dirname(robot_path)
        os.environ['PATH'] = f"{robot_dir}:{os.environ['PATH']}"
        
        print(f"Using ROBOT at: {robot_path}")
        print(f"Looking for ontology files in: {input_dir}")
        
        # Validate input directory exists
        if not os.path.isdir(input_dir):
            raise FileNotFoundError(f"Input directory '{input_dir}' not found")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create full output path
        intermediate_file = os.path.join(output_dir, "intermediate.owl")  # Intermediate OWL file
        output_file = os.path.join(output_dir, output_filename)           # Final Turtle file
        
        # Set Java memory arguments for ROBOT
        os.environ['ROBOT_JAVA_ARGS'] = '-Xmx4000G -XX:+UseParallelGC'
        
        # Get list of ontology files to merge
        if ontology_files_to_merge:
            ontology_files = [
                os.path.join(input_dir, f) 
                for f in ontology_files_to_merge
            ]
        else:
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
            
        # Build ROBOT merge command
        merge_command = ['robot', 'merge']
        
        # Add annotate-defined-by parameter
        merge_command.extend(['--annotate-defined-by', 'true'])
        
        # Add custom prefixes if enabled
        if add_prefixes and prefixes_file:
            prefixes_file_path = os.path.join(input_prefixes_dir, prefixes_file)
            print(f"Looking for prefixes file at: {prefixes_file_path}")
            if not os.path.exists(prefixes_file_path):
                raise FileNotFoundError(f"Prefixes file not found: {prefixes_file_path}")
            merge_command.extend(['--add-prefixes', prefixes_file_path])
            print(f"Adding prefixes from: {prefixes_file_path}")
        
        # Add input files
        for ontology_file in ontology_files:
            merge_command.extend(['--input', ontology_file])
        
        # Remove disjoint axioms
        merge_command.extend([
            'remove', '--axioms', 'disjoint',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        # Remove 'owl:Nothing' term
        merge_command.extend([
            'remove', '--term', 'owl:Nothing',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        # Add intermediate output file
        merge_command.extend(['--output', intermediate_file])
        
        print(f"Saving intermediate OWL output to: {intermediate_file}")
        print(f"\nExecuting ROBOT merge command:\n{' '.join(merge_command)}")
        
        try:
            # Run ROBOT merge command
            result = subprocess.run(
                merge_command,
                check=True,
                capture_output=True,
                text=True
            )
            print("\nROBOT Merge Output:")
            if result.stdout:
                print(result.stdout)
            print(f"Successfully merged ontologies into {intermediate_file}")
        except subprocess.CalledProcessError as e:
            print("\nError occurred during ROBOT merge execution:")
            print(f"Return code: {e.returncode}")
            print("\nCommand output:")
            if e.stdout:
                print("STDOUT:")
                print(e.stdout)
            if e.stderr:
                print("STDERR:")
                print(e.stderr)
            print("\nFull command that failed:")
            print(' '.join(merge_command))
            return False
        
        # Build ROBOT convert command
        convert_command = ['robot', 'convert']
        convert_command.extend(['--input', intermediate_file])
        convert_command.extend(['--format', 'ttl'])  # Use 'ttl' instead of 'turtle'
        convert_command.extend(['--output', output_file])
        
        print(f"\nConverting intermediate OWL to Turtle format...")
        print(f"Saving final output to: {output_file}")
        print(f"\nExecuting ROBOT convert command:\n{' '.join(convert_command)}")
        
        try:
            # Run ROBOT convert command
            result = subprocess.run(
                convert_command,
                check=True,
                capture_output=True,
                text=True
            )
            print("\nROBOT Convert Output:")
            if result.stdout:
                print(result.stdout)
            print(f"Successfully converted intermediate file to Turtle format: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            print("\nError occurred during ROBOT convert execution:")
            print(f"Return code: {e.returncode}")
            print("\nCommand output:")
            if e.stdout:
                print("STDOUT:")
                print(e.stdout)
            if e.stderr:
                print("STDERR:")
                print(e.stderr)
            print("\nFull command that failed:")
            print(' '.join(convert_command))
            return False
            
    except Exception as e:
        print(f"\nUnexpected error occurred:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        return False