import os
import json
import requests
import xml.etree.ElementTree as ET
import hashlib
from pathlib import Path
from datetime import datetime
import re

def normalize_iri(iri):
    """Normalize IRI to extract the base ontology prefix and standardize to lowercase."""
    if not iri:
        return None
    
    # Skip non-OBO IRIs
    if 'obo' not in iri:
        return None
        
    # Handle NCBITaxon special case
    if 'NCBITaxon' in iri:
        return 'http://purl.obolibrary.org/obo/ncbitaxon'
        
    # Extract ontology prefix for OBO terms
    match = re.match(r'http://purl\.obolibrary\.org/obo/([A-Za-z]+)(?:_|#|\.|$)', iri)
    if match:
        return f"http://purl.obolibrary.org/obo/{match.group(1).lower()}"
    
    return None

def download_ontology(url, output_path):
    """Download an ontology file if it doesn't exist."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Successfully downloaded: {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def check_obo_foundry_availability(filename):
    """Check if a -base version exists in OBO Foundry."""
    short_name = filename.split('.')[0].lower()
    if short_name.endswith('-base'):
        short_name = short_name[:-5]
    url = f"http://purl.obolibrary.org/obo/{short_name}/{short_name}-base.owl"
    
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return (response.status_code == 200, url)
    except requests.RequestException:
        return (False, url)

def classify_ontology(analysis, filename):
    """Classify the ontology based on analysis results."""
    if analysis is None:
        return "Unknown (analysis failed)"
    
    # First check for base version availability
    obo_foundry_available, url = check_obo_foundry_availability(filename)
    base_version_info = f" Base version available in OBO Foundry: {url}." if obo_foundry_available else " No -base version available in OBO Foundry"
    
    # If a base version exists, immediately classify as non-base
    if obo_foundry_available:
        return f"Non-Base.{base_version_info}"
    
    # Otherwise proceed with normal classification
    no_imports = not analysis['has_imports']
    more_own_terms = len(analysis['own_terms']) > len(analysis['external_terms'])
    base_hint = "base" in filename.lower()
    high_own_term_ratio = len(analysis['own_terms']) / (len(analysis['external_terms']) + 1) > 10
    
    if base_hint and no_imports:
        return f"Base.{base_version_info}"
    elif no_imports and more_own_terms and high_own_term_ratio:
        return f"Potential Base (missing -base hint in .owl file name).{base_version_info}"
    else:
        return f"Non-Base.{base_version_info}"

def analyze_ontology(file_path):
    """Analyze a single ontology file."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        namespaces = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'owl': 'http://www.w3.org/2002/07/owl#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
        }
        
        # Extract filename
        filename = os.path.basename(file_path)
        short_name = filename.split('.')[0].upper()
        
        results = {
            'file': filename,
            'has_imports': False,
            'ontology_iri': None,
            'own_terms': set(),
            'external_terms': set(),
            'external_terms_as_subjects': set()
        }
        
        # Check for imports
        imports = root.findall('.//owl:imports', namespaces)
        results['has_imports'] = len(imports) > 0
        
        # Get ontology IRI
        ontology = root.find('.//owl:Ontology', namespaces)
        if ontology is not None:
            results['ontology_iri'] = ontology.get('{' + namespaces['rdf'] + '}about')
        
        # Analyze terms
        for element in root.findall('.//*[@rdf:about]', namespaces):
            term_iri = element.get('{' + namespaces['rdf'] + '}about')
            
            # Special handling for NCBITaxon
            if short_name == 'NCBITAXON':
                if 'NCBITaxon_' in term_iri or 'NCBITaxon#' in term_iri:
                    results['own_terms'].add(term_iri)
                    continue
            
            # Regular term classification
            if f"/{short_name}_" in term_iri or f"/{short_name}#" in term_iri:
                results['own_terms'].add(term_iri)
            else:
                results['external_terms'].add(term_iri)
                if len(element) > 0:
                    results['external_terms_as_subjects'].add(term_iri)
        
        return results
    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        return None

def analyze_core_ontologies(repo_path):
    """Main function to analyze core ontologies."""
    # Setup paths
    ontologies_path = os.path.join(repo_path, 'ontologies_source.txt')
    ontology_data_path = os.path.join(repo_path, 'ontology_data_owl')
    outputs_path = os.path.join(repo_path, 'outputs')
    
    print("\nAnalysis Results:")
    
    # Process ontologies and gather results
    analysis_results = []
    all_external_terms = set()
    all_external_subjects = set()
    
    # Create necessary directories
    os.makedirs(ontology_data_path, exist_ok=True)
    os.makedirs(outputs_path, exist_ok=True)
    
    # Read core ontologies
    core_ontologies = []
    try:
        with open(ontologies_path, 'r') as f:
            in_core_section = False
            for line in f:
                line = line.strip()
                if line == "#Core Ontologies from OBO Foundry":
                    in_core_section = True
                elif line.startswith('#'):
                    in_core_section = False
                elif in_core_section and line:
                    core_ontologies.append(line)
    except Exception as e:
        print(f"Error reading ontologies.txt: {str(e)}")
        return
    
    # Process each ontology
    for url in core_ontologies:
        filename = os.path.basename(url)
        output_path = os.path.join(ontology_data_path, filename)
        
        # Check if file exists
        if os.path.exists(output_path):
            print(f"Skipping download, {filename} already present")
        else:
            print(f"Downloading {filename}...")
            if not download_ontology(url, output_path):
                continue
        
        # Analyze ontology
        result = analyze_ontology(output_path)
        if result:
            classification = classify_ontology(result, filename)
            
            # Create streamlined result for JSON
            json_result = {
                "file_name": result['file'],
                "has_imports": result['has_imports'],
                "ontology_iri": result['ontology_iri'],
                "own_terms_count": len(result['own_terms']),
                "external_terms_count": len(result['external_terms']),
                "classification": classification,
                "external_terms_as_subjects": sorted(list(result['external_terms_as_subjects']))[:5],
                "own_terms": sorted(list(result['own_terms']))[:5],
                "external_terms": sorted(list(result['external_terms']))[:5]
            }
            analysis_results.append(json_result)
            
            # Print analysis results
            print(f"\nFile: {result['file']}")
            print(f"  Has imports: {'Yes' if result['has_imports'] else 'No'}")
            print(f"  Ontology IRI: {result['ontology_iri']}")
            print(f"  Own terms: {len(result['own_terms'])}")
            print(f"  External terms: {len(result['external_terms'])}")
            print(f"  Classification: {classification}")
            
            if result['external_terms_as_subjects']:
                print("  External Terms Subject of Triples? Yes")
                print(f"  Number of external terms that are subjects of triples: {len(result['external_terms_as_subjects'])}")
                print("  First 5 external terms that are subject of triples:")
                for term in sorted(list(result['external_terms_as_subjects']))[:5]:
                    print(f"    {term}")
            else:
                print("  External Terms Subject of Triples? No")
            
            print("  First 5 own terms:")
            for term in sorted(list(result['own_terms']))[:5]:
                print(f"    {term}")
            
            print("  First 5 external terms:")
            for term in sorted(list(result['external_terms']))[:5]:
                print(f"    {term}")
            
            # Collect terms for TSV files
            all_external_terms.update(result['external_terms'])
            all_external_subjects.update(result['external_terms_as_subjects'])
    
    # Save results
    os.makedirs(outputs_path, exist_ok=True)
    
    # Save streamlined JSON results
    json_path = os.path.join(outputs_path, 'core_ontologies_analysis.json')
    with open(json_path, 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    # Save TSV files
    unique_external_terms = {normalize_iri(term) for term in all_external_terms if normalize_iri(term)}
    unique_subject_terms = {normalize_iri(term) for term in all_external_subjects if normalize_iri(term)}
    
    terms_path = os.path.join(outputs_path, 'core_onto_unique_external_terms.tsv')
    with open(terms_path, 'w') as f:
        for term in sorted(unique_external_terms):
            if term:
                f.write(f"{term}\n")
    
    subjects_path = os.path.join(outputs_path, 'core_onto_unique_external_subjects.tsv')
    with open(subjects_path, 'w') as f:
        for term in sorted(unique_subject_terms):
            if term:
                f.write(f"{term}\n")
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    # If run directly, analyze the current directory
    repo_path = os.getcwd()
    analyze_core_ontologies(repo_path)