# merge_ontologies.py
import os
import subprocess
from typing import Optional, List
from pathlib import Path

def merge_ontologies(
    repo_path: str,
    input_dir_name: str = 'ontology_data_owl',
    output_filename: str = 'CDM_merged_ontologies.owl',
    ontology_order: Optional[List[str]] = None  # New parameter for ordering
) -> bool:
    """
    Merge multiple ontology files using the ROBOT tool and remove specific axioms.
    
    Args:
        repo_path (str): Path to the repository root directory.
        input_dir_name (str): Name of input directory within repo_path.
        output_filename (str): Name of output OWL file.
        ontology_order (Optional[List[str]]): Optional list of ontology filenames (in desired order)
            to merge. Filenames should exist in the input directory.
    
    Returns:
        bool: True if merge was successful, False otherwise.
    
    Raises:
        FileNotFoundError: If input directory or specified ontology files don't exist.
        subprocess.CalledProcessError: If the ROBOT command fails.
    """
    try:
        # Set up paths relative to repo root
        input_dir = os.path.join(repo_path, input_dir_name)
        output_dir = os.path.join(repo_path, 'outputs')
        
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
        output_file = os.path.join(output_dir, output_filename)
        
        # Set Java memory arguments for ROBOT
        os.environ['ROBOT_JAVA_ARGS'] = '-Xmx4000G -XX:+UseParallelGC'
        
        # Determine the list of ontology files to merge
        if ontology_order is not None:
            # Use the specified order from the parameter
            ontology_files = []
            for filename in ontology_order:
                file_path = os.path.join(input_dir, filename)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Specified ontology file not found: {file_path}")
                if not filename.endswith(('.owl', '.ofn', '.obo')):
                    raise ValueError(f"File '{filename}' does not have a valid ontology extension")
                ontology_files.append(file_path)
        else:
            # Default: get all ontology files in the directory (order is arbitrary)
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
        
        # Write out the list of merged ontologies (in the desired order)
        merged_list_path = os.path.join(repo_path, 'ontologies_merged.txt')
        with open(merged_list_path, 'w') as f:
            # If a custom order was provided, write that order; otherwise, sort alphabetically.
            filenames_to_write = ontology_order if ontology_order is not None else sorted(
                [os.path.basename(f) for f in ontology_files]
            )
            for filename in filenames_to_write:
                f.write(f"{filename}\n")
        print(f"Created list of merged ontologies at: {merged_list_path}")
        
        # Build ROBOT command
        robot_command = ['robot', 'merge']
        robot_command.extend(['--annotate-defined-by', 'true'])
        
        # Add input files in the specified (or default) order
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
        
        try:
            # Run ROBOT command with more detailed output
            result = subprocess.run(
                robot_command,
                check=True,
                capture_output=True,
                text=True
            )
            print("\nROBOT Output:")
            if result.stdout:
                print(result.stdout)
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