import os
import subprocess
import re
import gzip
import tempfile
import shutil
from collections import defaultdict
from typing import Dict, Set, List, Tuple

def decompress_if_needed(file_path: str) -> str:
    """
    If file is gzipped, decompress it to a temporary file and return the path.
    Otherwise, return the original path.
    """
    if file_path.endswith('.gz'):
        temp_path = os.path.join(
            tempfile.gettempdir(),
            os.path.basename(file_path)[:-3]  # Remove .gz extension
        )
        with gzip.open(file_path, 'rb') as f_in:
            with open(temp_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return temp_path
    return file_path

def get_robot_path(repo_path: str) -> str:
    """Get the full path to the ROBOT executable."""
    robot_path = shutil.which('robot')
    if not robot_path:
        raise FileNotFoundError("ROBOT executable not found. Please ensure ROBOT is installed and in your PATH.")
    return robot_path

def extract_prefix_from_iri(iri: str) -> Tuple[str, str]:
    """
    Extract prefix and base IRI from a full IRI.
    Returns (prefix, base_iri)
    """
    # Try to extract prefix from IRI path
    path_match = re.match(r'.*[/#]([^/#_]+)[_/#]', iri)
    if path_match:
        prefix = path_match.group(1).upper()
        base_iri = iri[:path_match.end(1)]
        return prefix, base_iri
    
    # If no match, try to get the last meaningful part of the URL
    parts = re.split(r'[/#]', iri)
    meaningful_parts = [p for p in parts if p and not p.isdigit()]
    if meaningful_parts:
        prefix = meaningful_parts[-1].upper()
        base_iri = iri[:iri.rfind(meaningful_parts[-1])]
        return prefix, base_iri
    
    return "", iri

def analyze_ontology_prefixes(file_path: str, robot_path: str) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """
    Analyze an ontology file for prefixes and IRIs using ROBOT.
    """
    try:
        # Decompress if needed
        actual_path = decompress_if_needed(file_path)
        
        prefixes = set()
        prefix_to_iris = defaultdict(set)
        
        # Query for all IRIs used in the ontology
        cmd = [
            robot_path, 'query',
            '--input', actual_path,
            '--query', '''
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                SELECT DISTINCT ?s
                WHERE {
                    { ?s ?p ?o }
                    UNION
                    { ?x ?s ?o }
                    UNION
                    { ?x ?p ?s }
                    FILTER(isIRI(?s))
                }
            ''',
            '--format', 'csv'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Process each IRI found
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if line.strip():
                    iri = line.strip().strip('"')
                    if iri.startswith('http'):
                        prefix, base_iri = extract_prefix_from_iri(iri)
                        if prefix:
                            prefixes.add(prefix)
                            prefix_to_iris[prefix].add(base_iri)
        
        # Also try to get explicit prefix declarations from the ontology
        cmd_ttl = [
            robot_path, 'convert',
            '--input', actual_path,
            '--format', 'ttl',
            '--output', '-'
        ]
        
        ttl_result = subprocess.run(cmd_ttl, capture_output=True, text=True)
        
        if ttl_result.returncode == 0:
            # Look for explicit prefix declarations in Turtle format
            prefix_pattern = re.compile(r'@prefix\s+(\w+:)\s+<([^>]+)>')
            for match in prefix_pattern.finditer(ttl_result.stdout):
                prefix, iri = match.groups()
                prefix = prefix.rstrip(':').upper()
                prefixes.add(prefix)
                prefix_to_iris[prefix].add(iri)
        
        # Clean up temporary file if one was created
        if actual_path != file_path:
            try:
                os.remove(actual_path)
            except OSError:
                pass
                
        return prefixes, prefix_to_iris
        
    except subprocess.CalledProcessError as e:
        print(f"Error analyzing {file_path}: {e.stderr}")
        return set(), defaultdict(set)

def analyze_all_ontologies(input_dir: str, repo_path: str) -> Dict[str, Dict[str, Set[str]]]:
    """
    Analyze all ontologies in a directory for their prefixes.
    
    Args:
        input_dir: Directory containing ontology files
        repo_path: Repository root path (for finding ROBOT)
    
    Returns:
        Dictionary with analysis results per file
    """
    robot_path = get_robot_path(repo_path)
    results = {}
    
    # Get all ontology files, including gzipped ones
    ontology_files = [
        f for f in os.listdir(input_dir)
        if f.endswith(('.owl', '.ofn', '.obo', '.owl.gz', '.ofn.gz', '.obo.gz'))
    ]
    
    for filename in ontology_files:
        file_path = os.path.join(input_dir, filename)
        print(f"\nAnalyzing {filename}...")
        
        prefixes, prefix_to_iris = analyze_ontology_prefixes(file_path, robot_path)
        results[filename] = {
            'prefixes': prefixes,
            'prefix_to_iris': prefix_to_iris
        }
        
        print(f"Found {len(prefixes)} declared prefixes:")
        for prefix in sorted(prefixes):
            print(f"  - {prefix}: {next(iter(prefix_to_iris[prefix]), 'N/A')}")
        
        additional = set(prefix_to_iris.keys()) - prefixes
        if additional:
            print(f"Potential additional prefixes found:")
            for prefix in sorted(additional):
                print(f"  - {prefix}: {next(iter(prefix_to_iris[prefix]), 'N/A')}")
    
    return results

def generate_prefix_mapping(analysis_results: Dict[str, Dict[str, Set[str]]]) -> str:
    """Generate prefix mapping file content based on analysis."""
    all_prefixes = defaultdict(set)
    
    # Collect all prefixes and their IRIs
    for file_results in analysis_results.values():
        for prefix, iris in file_results['prefix_to_iris'].items():
            all_prefixes[prefix].update(iris)
    
    # Generate mapping content
    mapping_content = "# Automatically generated prefix mapping\n"
    for prefix, iris in sorted(all_prefixes.items()):
        if prefix and len(iris) > 0:
            base_iri = next(iter(iris))
            mapping_content += f"{base_iri} {prefix}:\n"
    
    return mapping_content

if __name__ == "__main__":
    # Example usage
    repo_path = "."  # Replace with actual path
    input_dir = "ontology_data_owl"  # Replace with your input directory
    
    print("Starting ontology prefix analysis...")
    results = analyze_all_ontologies(input_dir, repo_path)
    
    # Generate and save prefix mapping
    mapping_content = generate_prefix_mapping(results)
    with open("prefix_mapping.txt", "w") as f:
        f.write(mapping_content)
    
    print("\nPrefix mapping file generated: prefix_mapping.txt")