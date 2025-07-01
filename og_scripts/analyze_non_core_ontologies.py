import os
import json
import requests
import xml.etree.ElementTree as ET
import hashlib
from pathlib import Path
from datetime import datetime
import re
from urllib.parse import urlparse
import gzip
import shutil

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

def analyze_ontology(file_path):
    """Analyze a single ontology file."""
    try:
        # Remove duplicate print - we'll let the detailed results handle the output
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file is in functional syntax format
        is_functional_syntax = 'Prefix(' in content[:1000] or 'Ontology(' in content[:1000]
        
        filename = os.path.basename(file_path)
        if filename.endswith('.gz'):
            filename = filename[:-3]
        short_name = filename.split('.')[0].upper()
        
        results = {
            'file': filename,
            'has_imports': False,
            'ontology_iri': None,
            'own_terms': set(),
            'external_terms': set(),
            'external_terms_as_subjects': set()
        }
        
        if is_functional_syntax:
            # Parse functional syntax
            # Get ontology IRI
            ontology_match = re.search(r'Ontology\(<([^>]+)>', content)
            if ontology_match:
                results['ontology_iri'] = ontology_match.group(1)
            
            # Find imports if any
            import_matches = re.findall(r'Import\(<([^>]+)>', content)
            results['has_imports'] = len(import_matches) > 0
            
            # Find all declared classes
            class_matches = re.findall(r'Declaration\(Class\(<([^>]+)>', content)
            for term_iri in class_matches:
                if f"/{short_name}_" in term_iri or f"/{short_name}#" in term_iri:
                    results['own_terms'].add(term_iri)
                else:
                    results['external_terms'].add(term_iri)
            
            # Find classes that are subjects (appear in SubClassOf or other assertions)
            subject_matches = re.findall(r'SubClassOf\(<([^>]+)>', content)
            for term_iri in subject_matches:
                if term_iri in results['external_terms']:
                    results['external_terms_as_subjects'].add(term_iri)
        else:
            # Original XML parsing logic
            try:
                if file_path.endswith('.gz'):
                    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                        tree = ET.parse(f)
                else:
                    tree = ET.fromstring(content)
                
                namespaces = {
                    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'owl': 'http://www.w3.org/2002/07/owl#',
                    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
                }
                
                # Check for imports
                imports = tree.findall('.//owl:imports', namespaces)
                results['has_imports'] = len(imports) > 0
                
                # Get ontology IRI
                ontology = tree.find('.//owl:Ontology', namespaces)
                if ontology is not None:
                    results['ontology_iri'] = ontology.get('{' + namespaces['rdf'] + '}about')
                
                # Analyze terms
                for element in tree.findall('.//*[@rdf:about]', namespaces):
                    term_iri = element.get('{' + namespaces['rdf'] + '}about')
                    
                    # Special handling for NCBITaxon
                    if short_name == 'NCBITAXON':
                        if 'NCBITaxon_' in term_iri or 'NCBITaxon#' in term_iri:
                            results['own_terms'].add(term_iri)
                            continue
                    
                    if f"/{short_name}_" in term_iri or f"/{short_name}#" in term_iri:
                        results['own_terms'].add(term_iri)
                    else:
                        results['external_terms'].add(term_iri)
                        if len(element) > 0:
                            results['external_terms_as_subjects'].add(term_iri)
                            
            except ET.ParseError as e:
                print(f"XML parsing failed, trying as functional syntax...")
                return None
        
        return results
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        return None

def check_obo_foundry_base_availability(onto_name):
    """Check if ontology has a base version in OBO Foundry."""
    if not onto_name:
        return False, ""
        
    # Clean up the ontology name
    onto_name = onto_name.lower()
    if onto_name.endswith('.owl'):
        onto_name = onto_name[:-4]
    if onto_name.endswith('-base'):
        onto_name = onto_name[:-5]
    
    base_url = f"http://purl.obolibrary.org/obo/{onto_name}/{onto_name}-base.owl"
    try:
        response = requests.head(base_url, allow_redirects=True, timeout=5)
        return response.status_code == 200, base_url
    except requests.RequestException:
        return False, base_url

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

def download_and_process_ontology(url, output_path, is_base=False):
    """Download an ontology file and process it if it's gzipped."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Determine correct output directory
        if not is_base and '-base' not in os.path.basename(output_path):
            # Make sure we're not creating a nested non-base-ontologies directory
            if 'non-base-ontologies' not in output_path:
                output_dir = os.path.join(os.path.dirname(output_path), 'non-base-ontologies')
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, os.path.basename(output_path))
        
        if url.endswith('.gz'):
            # Save compressed file temporarily
            gz_path = output_path + '.gz'
            with open(gz_path, 'wb') as f:
                f.write(response.content)
            
            # Decompress
            with gzip.open(gz_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove compressed file
            os.remove(gz_path)
            print(f"Successfully downloaded and decompressed: {os.path.basename(output_path)}")
        else:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded: {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def read_core_external_terms(repo_path):
    """Read and parse the core_onto_unique_external_terms.tsv file."""
    terms_path = os.path.join(repo_path, 'outputs', 'core_onto_unique_external_terms.tsv')
    external_terms = set()
    try:
        with open(terms_path, 'r') as f:
            external_terms = {line.strip() for line in f if line.strip()}
        return external_terms
    except Exception as e:
        print(f"Error reading external terms file: {str(e)}")
        return set()

def get_core_ontologies(ontologies_txt):
    """Extract core ontology names from ontologies_source.txt."""
    core_ontos = set()
    try:
        # First try with ontologies_source.txt
        try:
            with open(ontologies_txt, 'r') as f:
                in_core_section = False
                for line in f:
                    if line.strip() == "#Core Ontologies from OBO Foundry":
                        in_core_section = True
                    elif line.startswith('#'):
                        in_core_section = False
                    elif in_core_section and line.strip():
                        # Extract ontology name from URL
                        onto_name = line.strip().split('/')[-1].split('.')[0]
                        core_ontos.add(onto_name)
        except FileNotFoundError:
            # If not found, try with ontologies.txt
            old_path = os.path.join(os.path.dirname(ontologies_txt), 'ontologies.txt')
            with open(old_path, 'r') as f:
                in_core_section = False
                for line in f:
                    if line.strip() == "#Core Ontologies from OBO Foundry":
                        in_core_section = True
                    elif line.startswith('#'):
                        in_core_section = False
                    elif in_core_section and line.strip():
                        # Extract ontology name from URL
                        onto_name = line.strip().split('/')[-1].split('.')[0]
                        core_ontos.add(onto_name)
            
            # Copy the content to the new filename
            import shutil
            shutil.copy2(old_path, ontologies_txt)
            print(f"Copied ontologies.txt to {ontologies_txt}")
            
    except Exception as e:
        print(f"Error reading ontologies file: {str(e)}")
    return core_ontos

def update_ontologies_txt(repo_path, non_base_urls, base_urls):
    """Update ontologies_source.txt with new ontology URLs."""
    ontologies_txt = os.path.join(repo_path, 'ontologies_source.txt')
    
    # Read existing content
    try:
        with open(ontologies_txt, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        # If ontologies_source.txt doesn't exist, try to read from ontologies.txt
        old_path = os.path.join(repo_path, 'ontologies.txt')
        try:
            with open(old_path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            # If neither file exists, create a basic structure
            lines = [
                "#Core Ontologies from OBO Foundry\n",
                "\n",
                "#Core closure ontologies non base version\n",
                "\n",
                "#Core closure ontologies -base version\n",
                "\n",
                "#Additional OBO Foundry ontologies\n",
                "\n",
                "#PyOBO Controlled Vocabularies and Ontologies\n",
                "\n",
                "#In-house Ontologies (manually added to ontologies_data_owl)\n"
            ]
    
    # Find sections
    non_base_section_index = -1
    base_section_index = -1
    for i, line in enumerate(lines):
        if line.strip() == "#Core closure ontologies non base version":
            non_base_section_index = i
        elif line.strip() == "#Core closure ontologies -base version":
            base_section_index = i
    
    if non_base_section_index == -1 or base_section_index == -1:
        core_section_index = -1
        for i, line in enumerate(lines):
            if line.strip() == "#Core Ontologies from OBO Foundry":
                core_section_index = i
                break
        
        if core_section_index != -1:
            insert_index = core_section_index
            while insert_index < len(lines) and not lines[insert_index].startswith('#'):
                insert_index += 1
            
            lines.insert(insert_index, "\n#Core closure ontologies non base version\n")
            lines.insert(insert_index + 1, "#Core closure ontologies -base version\n")
            non_base_section_index = insert_index
            base_section_index = insert_index + 1
    
    # Create new section contents
    non_base_lines = sorted(url + '\n' for url in non_base_urls if not '-base.owl' in url)
    base_lines = sorted(url + '\n' for url in base_urls if '-base.owl' in url)
    
    # Remove everything between sections and add new content
    new_lines = []
    current_section = None
    for line in lines:
        if line.strip() == "#Core closure ontologies non base version":
            new_lines.append(line)
            new_lines.extend(non_base_lines)
            current_section = "non_base"
        elif line.strip() == "#Core closure ontologies -base version":
            new_lines.append(line)
            new_lines.extend(base_lines)
            current_section = "base"
        elif line.startswith('#'):
            current_section = None
            new_lines.append(line)
        elif current_section is None:
            new_lines.append(line)
    
    # Write updated content
    with open(ontologies_txt, 'w') as f:
        f.writelines(new_lines)
        
def analyze_non_core_ontologies(repo_path):
    """Main function to analyze non-core ontologies."""
    # Setup paths
    ontologies_txt = os.path.join(repo_path, 'ontologies_source.txt')
    ontology_data_path = os.path.join(repo_path, 'ontology_data_owl')
    non_base_dir = os.path.join(ontology_data_path, 'non-base-ontologies')
    outputs_path = os.path.join(repo_path, 'outputs')
    
    # Create necessary directories
    os.makedirs(ontology_data_path, exist_ok=True)
    os.makedirs(non_base_dir, exist_ok=True)
    os.makedirs(outputs_path, exist_ok=True)
    
    # Read core ontologies list
    core_ontos = set()
    try:
        with open(ontologies_txt, 'r') as f:
            in_core_section = False
            for line in f:
                if line.strip() == "#Core Ontologies from OBO Foundry":
                    in_core_section = True
                elif line.startswith('#'):
                    in_core_section = False
                elif in_core_section and line.strip():
                    # Extract ontology name without extension or -base suffix
                    onto_name = os.path.basename(line.strip()).split('.')[0].replace('-base', '')
                    core_ontos.add(onto_name)
    except Exception as e:
        print(f"Error reading core ontologies: {str(e)}")

    # Read core external terms
    external_terms = read_core_external_terms(repo_path)
    
    print("\nProcessing external terms from core ontologies...")
    
    # Track URLs for ontologies.txt updates
    non_base_urls = set()
    base_urls = set()
    
    # Process external terms
    for term in external_terms:
        try:
            # Extract ontology name from IRI
            onto_name = term.split('/')[-1].lower()
            
            # Skip if it's a core ontology - handle both .owl and -base.owl versions
            onto_base = onto_name.replace('-base', '') if '-base' in onto_name else onto_name
            if onto_base in core_ontos:
                continue
            
            # Check for base version availability
            has_base, base_url = check_obo_foundry_base_availability(onto_name)
            
            if has_base:
                # Download base version
                filename = f"{onto_name}-base.owl"
                output_path = os.path.join(ontology_data_path, filename)
                if not os.path.exists(output_path):
                    print(f"Downloading base version of {onto_name}...")
                    if download_and_process_ontology(base_url, output_path, is_base=True):
                        base_urls.add(base_url)
                else:
                    print(f"Base version of {onto_name} already exists")
                    base_urls.add(base_url)
            else:
                # Download regular version
                regular_url = f"http://purl.obolibrary.org/obo/{onto_name}.owl"
                filename = f"{onto_name}.owl"
                output_path = os.path.join(ontology_data_path, filename)
                if not os.path.exists(output_path):
                    print(f"Downloading regular version of {onto_name}...")
                    if download_and_process_ontology(regular_url, output_path):
                        non_base_urls.add(regular_url)
                else:
                    print(f"Regular version of {onto_name} already exists")
                    non_base_urls.add(regular_url)
        
        except Exception as e:
            print(f"Error processing term {term}: {str(e)}")
            continue
    
    # Update ontologies.txt
    print("\nUpdating ontologies.txt...")
    update_ontologies_txt(repo_path, non_base_urls, base_urls)
    
    # Process Additional OBO Foundry, PyOBO and In-house ontologies
    print("\nProcessing Additional OBO Foundry, PyOBO and In-house ontologies...")
    additional_ontologies = []
    current_section = ""
    
    with open(ontologies_txt, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                current_section = line
            elif line and (current_section in ["#PyOBO Controlled Vocabularies and Ontologies", 
                                             "#In-house Ontologies",
                                             "#Additional OBO Foundry ontologies"]):
                additional_ontologies.append(line)
    
    # Download and verify additional ontologies
    for url in additional_ontologies:
        filename = os.path.basename(url)
        if filename.endswith('.gz'):
            output_path = os.path.join(ontology_data_path, 'non-base-ontologies', filename[:-3])
        else:
            output_path = os.path.join(ontology_data_path, 'non-base-ontologies', filename)
        
        if os.path.exists(output_path):
            print(f"Additional ontology {os.path.basename(output_path)} already exists")
        else:
            print(f"Downloading {filename}...")
            download_and_process_ontology(url, output_path)

    print("\nAnalyzing non-core ontologies...")
    analysis_results = []
    
    # Helper function to analyze and print results
    def analyze_and_print_results(file_path):
        filename = os.path.basename(file_path)
        # Skip core ontologies
        if filename in core_ontos:
            return
            
        print(f"\nFile: {filename}")
        result = analyze_ontology(file_path)
        if result:
            classification = classify_ontology(result, filename)
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
    
    # Only analyze non-base directory contents
    print("\nAnalyzing non-core ontologies:")
    if os.path.exists(non_base_dir):
        for filename in sorted(os.listdir(non_base_dir)):
            if filename.endswith(('.owl', '.ofn', '.obo')):
                file_path = os.path.join(non_base_dir, filename)
                analyze_and_print_results(file_path)
    
    # Save analysis results
    json_path = os.path.join(outputs_path, 'non_core_ontologies_analysis.json')
    with open(json_path, 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    # If run directly, analyze the current directory
    repo_path = os.getcwd()
    analyze_non_core_ontologies(repo_path)