# create_pseudo_base_ontology.py
import os
import subprocess
from pathlib import Path
import re

def extract_prefix_from_filename(filename):
    """Extract ontology prefix from filename."""
    # Remove extension and -base suffix if present
    base_name = filename.split('.')[0].replace('-base', '')
    # Convert to uppercase for prefix
    return f"http://purl.obolibrary.org/obo/{base_name.upper()}_"

def is_pyobo_ontology(filename, repo_path):
    """Check if the ontology is from PyOBO section."""
    ontologies_txt = os.path.join(repo_path, 'ontologies_source.txt')
    try:
        with open(ontologies_txt, 'r') as f:
            in_pyobo_section = False
            for line in f:
                if line.strip() == "#PyOBO Controlled Vocabularies and Ontologies":
                    in_pyobo_section = True
                elif line.startswith('#'):
                    in_pyobo_section = False
                elif in_pyobo_section and line.strip():
                    if filename in line:
                        return True
    except Exception as e:
        print(f"Error checking PyOBO status: {str(e)}")
    return False

def create_pseudo_base_ontologies(repo_path):
    """Create pseudo base versions of non-base ontologies."""
    try:
        # Setup paths
        non_base_dir = os.path.join(repo_path, 'ontology_data_owl', 'non-base-ontologies')
        owl_dir = os.path.join(repo_path, 'ontology_data_owl')
        os.makedirs(non_base_dir, exist_ok=True)
        
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
        
        # Set Java memory arguments for ROBOT
        os.environ['ROBOT_JAVA_ARGS'] = '-Xmx180G -XX:+UseParallelGC'
        
        # Process each non-base ontology
        for filename in os.listdir(non_base_dir):
            # Skip non-ontology files
            if not filename.endswith(('.owl', '.ofn', '.obo')):
                continue
                
            # Skip if already a base version
            if '-base' in filename:
                continue
                
            input_path = os.path.join(non_base_dir, filename)
            
            # Handle PyOBO ontologies
            if is_pyobo_ontology(filename, repo_path):
                print(f"Copying PyOBO ontology to main directory: {filename}")
                output_path = os.path.join(owl_dir, filename)
                if not os.path.exists(output_path):
                    import shutil
                    shutil.copy2(input_path, output_path)
                continue
            
            # For non-PyOBO ontologies, create base version
            base_filename = f"{filename.rsplit('.', 1)[0]}-base.owl"
            output_path = os.path.join(owl_dir, base_filename)
            
            # Check if base version already exists
            if os.path.exists(output_path):
                print(f"Base version already exists for {filename}, skipping...")
                continue
                
            # Get base IRI from filename
            base_iri = extract_prefix_from_filename(filename)
            
            print(f"Processing {filename}...")
            print(f"Using base IRI: {base_iri}")
            
            # Build ROBOT command with improved parameters matching the Makefile approach
            robot_command = [
                'robot', 'remove',
                '--input', input_path,
                '--base-iri', base_iri,
                '--axioms', 'external',
                '--preserve-structure', 'false',
                '--trim', 'false',
                'remove', '--select', 'imports',
                '--trim', 'false',
                '--output', output_path
            ]
            
            print(f"Executing command:\n{' '.join(robot_command)}")
            
            # Run ROBOT command
            try:
                result = subprocess.run(
                    robot_command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"Created base version for {filename}: {base_filename}")
                if result.stdout:
                    print("STDOUT:", result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"Error processing {filename}:")
                print("STDERR:", e.stderr)
                print("STDOUT:", e.stdout)
                print("\nFull command that failed:")
                print(' '.join(robot_command))
        
        print("\nProcessing complete!")
        return True
        
    except Exception as e:
        print(f"\nUnexpected error occurred:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    repo_path = os.getcwd()
    create_pseudo_base_ontologies(repo_path)