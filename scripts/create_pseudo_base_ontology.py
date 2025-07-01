# create_pseudo_base_ontology.py
import os
import subprocess
from pathlib import Path
import re
from enhanced_download import get_output_directories, is_test_mode

def extract_prefix_from_filename(filename):
    """Extract ontology prefix from filename."""
    # Remove extension and -base suffix if present
    base_name = filename.split('.')[0].replace('-base', '')
    # Convert to uppercase for prefix
    return f"http://purl.obolibrary.org/obo/{base_name.upper()}_"

def is_pyobo_ontology(filename, repo_path):
    """Check if the ontology is from PyOBO section."""
    source_file = os.environ.get('ONTOLOGIES_SOURCE_FILE', 'ontologies_source.txt')
    ontologies_txt = os.path.join(repo_path, source_file)
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
        # Setup paths - support test configuration
        test_mode = is_test_mode()
        ontology_data_path, _, outputs_path, version_dir = get_output_directories(repo_path, test_mode)
        
        non_base_dir = os.path.join(ontology_data_path, 'non-base-ontologies')
        owl_dir = ontology_data_path
        os.makedirs(non_base_dir, exist_ok=True)
        
        print(f"🔧 Mode: {'TEST' if test_mode else 'PRODUCTION'}")
        print(f"📁 Processing non-base ontologies from: {non_base_dir}")
        print(f"📁 Creating base versions in: {owl_dir}")
        
        # Find ROBOT executable in PATH
        import shutil
        robot_path = shutil.which('robot')
        if not robot_path:
            raise FileNotFoundError("ROBOT executable not found. Please ensure ROBOT is installed and in your PATH.")
        
        print(f"Using ROBOT at: {robot_path}")
        
        # Use environment variable for Java memory arguments or set default
        if 'ROBOT_JAVA_ARGS' not in os.environ:
            os.environ['ROBOT_JAVA_ARGS'] = '-Xmx32g -XX:MaxMetaspaceSize=4g'
        print(f"ROBOT memory settings: {os.environ['ROBOT_JAVA_ARGS']}")
        
        # Check if memory monitoring is enabled
        enable_monitoring = os.getenv('ENABLE_MEMORY_MONITORING', 'false').lower() == 'true'
        if enable_monitoring:
            print("🔍 Memory monitoring enabled for ROBOT operations")
        
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
            
            # Run ROBOT command with optional memory monitoring
            try:
                if enable_monitoring:
                    # Use memory monitor for this individual ROBOT operation
                    monitor_script = os.path.join(os.path.dirname(__file__), 'memory_monitor.py')
                    monitor_command = [
                        'python3', monitor_script,
                        f'ROBOT_base_{filename}',
                        ' '.join(robot_command),
                        repo_path,
                        str(os.getenv('MEMORY_MONITOR_INTERVAL', '15'))
                    ]
                    result = subprocess.run(monitor_command, check=True)
                else:
                    # Run ROBOT command normally
                    result = subprocess.run(
                        robot_command,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    if result.stdout:
                        print("STDOUT:", result.stdout)
                
                print(f"Created base version for {filename}: {base_filename}")
            except subprocess.CalledProcessError as e:
                print(f"Error processing {filename}:")
                if hasattr(e, 'stderr') and e.stderr:
                    print("STDERR:", e.stderr)
                if hasattr(e, 'stdout') and e.stdout:
                    print("STDOUT:", e.stdout)
                print("\nFull command that failed:")
                print(' '.join(robot_command) if not enable_monitoring else f"Memory-monitored command for {filename}")
        
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