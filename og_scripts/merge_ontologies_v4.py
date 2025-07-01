import os
import subprocess
import json
from typing import Optional, List
from pathlib import Path

def create_prefix_mapping(repo_path: str) -> str:
    """Create JSON-LD prefix mapping file for ROBOT."""
    prefix_mappings = {
        "@context": {
            # Standard ontology prefixes
            "obo": "http://purl.obolibrary.org/obo/",
            "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            
            # External resource prefixes
            "credit": {
                "@id": "https://credit.niso.org/contributor-roles/",
                "@prefix": true
            },
            "Pfam": {
                "@id": "https://www.ebi.ac.uk/interpro/entry/pfam/",
                "@prefix": true
            },
            "Pfam.clan": {
                "@id": "https://www.ebi.ac.uk/interpro/set/pfam/",
                "@prefix": true
            },
            "GTDB": {
                "@id": "https://gtdb.ecogenomic.org/tree?r=",
                "@prefix": true
            },
            "InterPro": {
                "@id": "https://www.ebi.ac.uk/interpro/entry/InterPro/",
                "@prefix": true
            },
            "ROR": {
                "@id": "https://ror.org/",
                "@prefix": true
            },
            "EC": {
                "@id": "https://bioregistry.io/eccode:",
                "@prefix": true
            },
            "RHEA": {
                "@id": "https://www.rhea-db.org/rhea/",
                "@prefix": true
            },
            "UP": {
                "@id": "https://bioregistry.io/uniprot:",
                "@prefix": true
            },
            "MetaCyc.pathway": {
                "@id": "http://purl.obolibrary.org/obo/metacyc.pathway_",
                "@prefix": true
            },
            "Seed.compound": {
                "@id": "http://purl.obolibrary.org/obo/seed.compound_",
                "@prefix": true
            },
            "Seed.reaction": {
                "@id": "http://purl.obolibrary.org/obo/seed.reaction_",
                "@prefix": true
            },
            "KEGG.rn": {
                "@id": "http://purl.obolibrary.org/obo/kegg_",
                "@prefix": true
            }
        }
    }
    
    mapping_file = os.path.join(repo_path, 'prefix_context.jsonld')
    with open(mapping_file, 'w') as f:
        json.dump(prefix_mappings, f, indent=2)
    return mapping_file

def merge_ontologies(
    repo_path: str,
    input_dir_name: str = 'ontology_data_owl',
    output_filename: str = 'CDM_merged_ontologies.owl'
) -> bool:
    """
    Merge multiple ontology files using ROBOT tool with prefix standardization.
    """
    try:
        # Set up paths
        input_dir = os.path.join(repo_path, input_dir_name)
        output_dir = os.path.join(repo_path, 'outputs')
        intermediate_dir = os.path.join(output_dir, 'intermediary_ontology')
        
        # Create directories
        os.makedirs(intermediate_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup ROBOT path
        robot_path = os.path.join(
            os.path.dirname(repo_path),
            'install_stuff',
            'robot',
            'robot'
        )
        
        if not os.path.exists(robot_path):
            raise FileNotFoundError(f"ROBOT executable not found at: {robot_path}")
        
        robot_dir = os.path.dirname(robot_path)
        os.environ['PATH'] = f"{robot_dir}:{os.environ['PATH']}"
        
        # Get ontology files
        ontology_files = [
            os.path.join(input_dir, f) 
            for f in os.listdir(input_dir) 
            if f.endswith(('.owl', '.ofn', '.obo'))
        ]
        
        # Verify files
        if not ontology_files:
            raise FileNotFoundError(f"No ontology files found in '{input_dir}'")
            
        print(f"Found {len(ontology_files)} ontology files:")
        for f in ontology_files:
            print(f"  - {f}")
            if not os.path.exists(f):
                raise FileNotFoundError(f"Ontology file not found: {f}")
            if not os.access(f, os.R_OK):
                raise PermissionError(f"Cannot read ontology file: {f}")
        
        # Create merged list file
        ontology_filenames = [os.path.basename(f) for f in ontology_files]
        merged_list_path = os.path.join(repo_path, 'ontologies_merged.txt')
        with open(merged_list_path, 'w') as f:
            for filename in sorted(ontology_filenames):
                f.write(f"{filename}\n")
        print(f"Created list of merged ontologies at: {merged_list_path}")
        
        # Set memory
        os.environ['ROBOT_JAVA_ARGS'] = '-Xmx4000G -XX:+UseParallelGC'
        
        # Create paths for intermediate files
        intermediate_file1 = os.path.join(intermediate_dir, 'merged_intermediate.owl')
        output_file = os.path.join(output_dir, output_filename)
        
        # Create JSON-LD prefix mapping
        prefix_file = create_prefix_mapping(repo_path)
        
        # Step 1: Merge with prefix handling
        merge_command = ['robot', 'merge']
        
        # Add prefixes from JSON-LD file
        merge_command.extend(['--prefixes', prefix_file])
        
        # Add inputs and other parameters
        merge_command.extend(['--annotate-defined-by', 'true'])
        
        for ontology_file in ontology_files:
            merge_command.extend(['--input', ontology_file])
        
        # Add removal operations
        merge_command.extend([
            'remove', '--axioms', 'disjoint',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        merge_command.extend([
            'remove', '--term', 'owl:Nothing',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        merge_command.extend(['--output', output_file])
        
        print("\nExecuting merge command:")
        print(f"{' '.join(merge_command)}")
        
        # Run the command
        result = subprocess.run(
            merge_command,
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"\nSuccessfully merged ontologies into {output_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\nError executing ROBOT command:")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
        
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    repo_path = "."  # Replace with actual path
    success = merge_ontologies(repo_path)
    print(f"Merge {'succeeded' if success else 'failed'}")