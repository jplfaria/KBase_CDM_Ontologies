import os
import subprocess
import json
from pathlib import Path

def export_all_prefixes(
    repo_path: str,
    input_dir_name: str = 'ontology_data_owl',
    output_dir_name: str = 'exported_prefixes'
) -> bool:
    """
    Export prefixes from all ontology files in the specified directory using ROBOT.
    
    Args:
        repo_path (str): Path to the repository root directory
        input_dir_name (str): Name of input directory containing ontology files
        output_dir_name (str): Name of directory to store exported prefix files
    
    Returns:
        bool: True if all exports were successful, False if any failed
    """
    try:
        # Set up paths
        input_dir = os.path.join(repo_path, input_dir_name)
        output_dir = os.path.join(repo_path, output_dir_name)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Find ROBOT executable in PATH
        import shutil
        robot_path = shutil.which('robot')
        if not robot_path:
            raise FileNotFoundError("ROBOT executable not found. Please ensure ROBOT is installed and in your PATH.")
        
        print(f"Using ROBOT at: {robot_path}")
        print(f"Looking for ontology files in: {input_dir}")
        
        # Get list of ontology files
        ontology_files = [
            f for f in os.listdir(input_dir) 
            if f.endswith(('.owl', '.ofn', '.obo'))
        ]
        
        if not ontology_files:
            raise FileNotFoundError(f"No ontology files found in {input_dir}")
        
        print(f"Found {len(ontology_files)} ontology files")
        
        # Dictionary to store all prefixes
        all_prefixes = {}
        
        # Process each ontology file
        for ontology_file in ontology_files:
            input_path = os.path.join(input_dir, ontology_file)
            output_path = os.path.join(output_dir, f"{ontology_file}_prefixes.json")
            
            print(f"\nProcessing {ontology_file}...")
            
            # Build ROBOT command with corrected syntax
            robot_command = [
                'robot',
                'export-prefixes',
                '--input', input_path,  # Using --input instead of -i
                '--output', output_path
            ]
            
            try:
                # Run ROBOT command
                result = subprocess.run(
                    robot_command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                # Read the exported prefixes
                try:
                    with open(output_path) as f:
                        prefixes = json.load(f)
                        
                    # Add to combined prefixes
                    if "@context" in prefixes:
                        all_prefixes.update(prefixes["@context"])
                    print(f"Successfully exported prefixes to {output_path}")
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON from {output_path}")
                except FileNotFoundError:
                    print(f"Warning: Output file {output_path} was not created")
                
            except subprocess.CalledProcessError as e:
                print(f"\nError processing {ontology_file}:")
                print(f"Return code: {e.returncode}")
                if e.stdout:
                    print("STDOUT:", e.stdout)
                if e.stderr:
                    print("STDERR:", e.stderr)
                continue
                
        # Save combined prefixes
        if all_prefixes:
            combined_output = os.path.join(output_dir, "all_prefixes_combined.json")
            with open(combined_output, 'w') as f:
                json.dump({"@context": all_prefixes}, f, indent=2, sort_keys=True)
                
            print(f"\nSuccessfully exported all prefixes!")
            print(f"Combined prefixes saved to: {combined_output}")
            return True
        else:
            print("\nWarning: No prefixes were collected from any ontology")
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
    repo_path = "/scratch/jplfaria/KBase_CDM_Ontologies"
    success = export_all_prefixes(repo_path)