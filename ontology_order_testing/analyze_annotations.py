#!/usr/bin/env python3
"""
Analyze --annotate-defined-by behavior in merged ontologies.

This script examines which ontologies are marked as definers for shared terms,
helping understand the impact of merge order.
"""

import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
import json

def extract_term_definers(owl_file: str) -> Dict[str, str]:
    """
    Extract term -> definer mappings from OWL file.
    
    Returns:
        Dictionary mapping term IRI -> defining ontology
    """
    try:
        tree = ET.parse(owl_file)
        root = tree.getroot()
        
        namespaces = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#'
        }
        
        term_definers = {}
        
        # Find all terms with hasOBONamespace annotation
        for element in root.findall('.//*[@rdf:about]', namespaces):
            term_iri = element.get('{' + namespaces['rdf'] + '}about')
            
            # Look for the defining namespace annotation
            namespace_elem = element.find('.//oboInOwl:hasOBONamespace', namespaces)
            if namespace_elem is not None:
                definer = namespace_elem.text
                term_definers[term_iri] = definer
        
        return term_definers
        
    except Exception as e:
        print(f"Error parsing {owl_file}: {str(e)}")
        return {}

def analyze_term_patterns(term_definers: Dict[str, str]) -> Dict:
    """
    Analyze patterns in term -> definer mappings.
    
    Returns:
        Analysis results
    """
    # Count definitions by ontology
    definer_counts = Counter(term_definers.values())
    
    # Group terms by ontology prefix
    prefix_patterns = defaultdict(set)
    cross_definitions = []
    
    for term_iri, definer in term_definers.items():
        # Extract term prefix (e.g., "BFO" from "http://purl.obolibrary.org/obo/BFO_0000001")
        if '/obo/' in term_iri:
            try:
                term_part = term_iri.split('/obo/')[-1]
                if '_' in term_part:
                    term_prefix = term_part.split('_')[0].upper()
                elif '#' in term_part:
                    term_prefix = term_part.split('#')[0].upper()
                else:
                    term_prefix = "UNKNOWN"
                
                prefix_patterns[term_prefix].add(definer)
                
                # Check for cross-definitions (term from one ontology defined by another)
                if term_prefix.lower() != definer.lower():
                    cross_definitions.append({
                        'term': term_iri,
                        'term_prefix': term_prefix,
                        'definer': definer
                    })
                    
            except Exception:
                continue
    
    return {
        'total_defined_terms': len(term_definers),
        'definer_counts': dict(definer_counts),
        'prefix_patterns': {k: list(v) for k, v in prefix_patterns.items()},
        'cross_definitions': cross_definitions
    }

def compare_definer_patterns(files: Dict[str, str]) -> Dict:
    """
    Compare term definer patterns across different merge orders.
    
    Args:
        files: Dictionary mapping order name -> file path
    
    Returns:
        Comparison results
    """
    print("\\n🔍 Analyzing term definer patterns across merge orders...")
    
    all_analyses = {}
    
    for order_name, file_path in files.items():
        if os.path.exists(file_path):
            print(f"📊 Analyzing {order_name} order...")
            
            term_definers = extract_term_definers(file_path)
            analysis = analyze_term_patterns(term_definers)
            
            all_analyses[order_name] = {
                'file_path': file_path,
                'term_definers': term_definers,
                'analysis': analysis
            }
            
            print(f"  ✓ {analysis['total_defined_terms']} terms with definers")
            print(f"  ✓ {len(analysis['definer_counts'])} defining ontologies")
            print(f"  ✓ {len(analysis['cross_definitions'])} cross-definitions")
    
    # Compare patterns between orders
    comparisons = {}
    order_names = list(all_analyses.keys())
    
    for i in range(len(order_names)):
        for j in range(i + 1, len(order_names)):
            name1, name2 = order_names[i], order_names[j]
            
            definers1 = all_analyses[name1]['term_definers']
            definers2 = all_analyses[name2]['term_definers']
            
            # Find terms with different definers
            common_terms = set(definers1.keys()) & set(definers2.keys())
            definer_differences = []
            
            for term in common_terms:
                if definers1[term] != definers2[term]:
                    definer_differences.append({
                        'term': term,
                        name1: definers1[term],
                        name2: definers2[term]
                    })
            
            comparison_key = f"{name1}_vs_{name2}"
            comparisons[comparison_key] = {
                'common_terms': len(common_terms),
                'definer_differences': definer_differences
            }
    
    return {
        'order_analyses': all_analyses,
        'comparisons': comparisons
    }

def generate_definer_report(results: Dict, output_dir: str):
    """Generate detailed report on term definer analysis."""
    
    report_file = os.path.join(output_dir, 'definer_analysis.json')
    summary_file = os.path.join(output_dir, 'definer_summary.txt')
    
    # Save detailed JSON
    # Remove term_definers from JSON to keep file manageable
    json_data = {}
    for order_name, data in results['order_analyses'].items():
        json_data[order_name] = {
            'file_path': data['file_path'],
            'analysis': data['analysis']
        }
    json_data['comparisons'] = results['comparisons']
    
    with open(report_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    # Generate summary
    with open(summary_file, 'w') as f:
        f.write("TERM DEFINER ANALYSIS SUMMARY\\n")
        f.write("=" * 40 + "\\n\\n")
        
        # Per-order analysis
        for order_name, data in results['order_analyses'].items():
            analysis = data['analysis']
            f.write(f"{order_name.upper()} ORDER:\\n")
            f.write(f"  Total defined terms: {analysis['total_defined_terms']}\\n")
            f.write(f"  Defining ontologies: {len(analysis['definer_counts'])}\\n")
            f.write(f"  Cross-definitions: {len(analysis['cross_definitions'])}\\n")
            
            f.write(f"\\n  Definer distribution:\\n")
            for definer, count in sorted(analysis['definer_counts'].items(), key=lambda x: x[1], reverse=True):
                f.write(f"    {definer:12}: {count:4d} terms\\n")
            
            if analysis['cross_definitions']:
                f.write(f"\\n  Cross-definition examples:\\n")
                for cd in analysis['cross_definitions'][:5]:
                    f.write(f"    {cd['term_prefix']} term defined by {cd['definer']}\\n")
            
            f.write("\\n")
        
        # Comparison analysis
        f.write("CROSS-ORDER COMPARISONS:\\n")
        for comp_name, comp_data in results['comparisons'].items():
            f.write(f"\\n{comp_name.replace('_', ' vs ').upper()}:\\n")
            f.write(f"  Common terms: {comp_data['common_terms']}\\n")
            f.write(f"  Definer differences: {len(comp_data['definer_differences'])}\\n")
            
            if comp_data['definer_differences']:
                f.write(f"\\n  Examples of different attribution:\\n")
                for diff in comp_data['definer_differences'][:5]:
                    f.write(f"    {diff['term']}:\\n")
                    names = [k for k in diff.keys() if k != 'term']
                    for name in names:
                        f.write(f"      {name}: {diff[name]}\\n")
    
    print(f"\\n📋 Definer analysis reports:")
    print(f"  📄 Detailed: {report_file}")
    print(f"  📝 Summary: {summary_file}")

def main():
    """Main analysis function."""
    
    script_dir = os.path.dirname(__file__)
    results_dir = os.path.join(script_dir, 'results')
    
    if not os.path.exists(results_dir):
        print("❌ Results directory not found. Run test_merge_orders.py first.")
        return 1
    
    print("🔍 Term Definer Analysis")
    print("=" * 30)
    
    # Find merge files
    merge_files = {
        'alphabetical': os.path.join(results_dir, 'CDM_merged_alphabetical.owl'),
        'hierarchy': os.path.join(results_dir, 'CDM_merged_hierarchy.owl'),
        'size': os.path.join(results_dir, 'CDM_merged_size.owl')
    }
    
    existing_files = {name: path for name, path in merge_files.items() if os.path.exists(path)}
    
    if not existing_files:
        print("❌ No merge files found. Run test_merge_orders.py first.")
        return 1
    
    print(f"📁 Found {len(existing_files)} merge files")
    
    # Analyze definer patterns
    results = compare_definer_patterns(existing_files)
    
    # Generate report
    generate_definer_report(results, results_dir)
    
    # Summary
    print("\\n" + "=" * 30)
    print("🏁 DEFINER ANALYSIS SUMMARY")
    print("=" * 30)
    
    for comp_name, comp_data in results['comparisons'].items():
        diff_count = len(comp_data['definer_differences'])
        if diff_count > 0:
            print(f"⚠️  {comp_name.replace('_', ' vs ')}: {diff_count} different attributions")
        else:
            print(f"✅ {comp_name.replace('_', ' vs ')}: Identical attributions")
    
    print("\\n📋 Check definer_summary.txt for detailed findings")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())