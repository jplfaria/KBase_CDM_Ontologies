import os
import subprocess
from typing import Optional, List
from pathlib import Path

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
        intermediate_file2 = os.path.join(intermediate_dir, 'prefix_fixed.owl')
        output_file = os.path.join(output_dir, output_filename)
        
        # Create prefix mapping file
        mapping_file = os.path.join(intermediate_dir, 'prefix_mapping.txt')
        prefix_mappings = {
            'https://credit.niso.org/contributor-roles/': 'credit:',
            'https://www.ebi.ac.uk/interpro/entry/pfam/': 'Pfam:',
            'https://www.ebi.ac.uk/interpro/set/pfam/': 'Pfam.clan:',
            'https://gtdb.ecogenomic.org/tree?r=': 'GTDB:',
            'https://www.ebi.ac.uk/interpro/entry/InterPro/': 'InterPro:',
            'https://ror.org/': 'ror:',
            'https://bioregistry.io/eccode:': 'EC:',
            'https://www.rhea-db.org/rhea/': 'RHEA:',
            'https://bioregistry.io/uniprot:': 'UniProt:',
            'http://purl.obolibrary.org/obo/metacyc.pathway_': 'MetaCyc.pathway:',
            'http://purl.obolibrary.org/obo/seed.compound_': 'Seed.compound:',
            'http://purl.obolibrary.org/obo/seed.reaction_': 'Seed.reaction:',
            'http://purl.obolibrary.org/obo/kegg_': 'KEGG.rn:'
        }
        
        with open(mapping_file, 'w') as f:
            for uri, prefix in prefix_mappings.items():
                f.write(f'{uri} {prefix}\n')
        
        # Step 1: Initial merge with all original parameters
        merge_command = ['robot', 'merge']
        merge_command.extend(['--annotate-defined-by', 'true'])
        
        for ontology_file in ontology_files:
            merge_command.extend(['--input', ontology_file])
            
        # Add the original remove operations
        merge_command.extend([
            'remove', '--axioms', 'disjoint',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        merge_command.extend([
            'remove', '--term', 'owl:Nothing',
            '--trim', 'true', '--preserve-structure', 'false'
        ])
        
        merge_command.extend(['--output', intermediate_file1])
        
        print("\nExecuting initial merge command:")
        print(f"{' '.join(merge_command)}")
        subprocess.run(merge_command, check=True, capture_output=True, text=True)
        
        # Step 2: Transform URIs using annotate
        annotate_command = [
            'robot', 'annotate',
            '--input', intermediate_file1,
            '--annotation-file', mapping_file
        ]
        
        # Add all prefix definitions
        for prefix, uri in prefix_mappings.items():
            annotate_command.extend(['--prefix', f'{uri} {prefix}'])
            
        annotate_command.extend(['--output', intermediate_file2])
        
        print("\nExecuting annotate command:")
        print(f"{' '.join(annotate_command)}")
        subprocess.run(annotate_command, check=True, capture_output=True, text=True)
        
        # Step 3: Remove annotations using filter
        filter_command = [
            'robot', 'remove',
            '--input', intermediate_file2,
            '--term', 'oio:id',
            '--select', 'annotation-properties',
            '--output', output_file
        ]
        
        print("\nExecuting remove command:")
        print(f"{' '.join(filter_command)}")
        subprocess.run(filter_command, check=True, capture_output=True, text=True)
        
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