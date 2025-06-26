#!/usr/bin/env python3
"""
Compare merge results from different ontology orders.

This script analyzes the differences between merges created with different
ontology ordering strategies, focusing on annotation differences.
"""

import os
import sys
import subprocess
import shutil
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import json

def parse_owl_file(owl_file: str) -> Dict[str, Dict[str, str]]:
    """
    Parse OWL file and extract term annotations.
    
    Returns:
        Dictionary mapping term IRI -> annotation type -> annotation value
    """
    try:
        tree = ET.parse(owl_file)
        root = tree.getroot()
        
        namespaces = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'owl': 'http://www.w3.org/2002/07/owl#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'obo': 'http://purl.obolibrary.org/obo/',
            'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#'
        }
        
        terms = {}
        
        # Find all classes and their annotations
        for element in root.findall('.//*[@rdf:about]', namespaces):
            term_iri = element.get('{' + namespaces['rdf'] + '}about')
            
            annotations = {}
            
            # Check for rdfs:label
            label_elem = element.find('rdfs:label', namespaces)
            if label_elem is not None:
                annotations['label'] = label_elem.text
            
            # Check for defined-by annotation (key for our testing)
            defined_by_elem = element.find('.//oboInOwl:hasOBONamespace', namespaces)
            if defined_by_elem is not None:
                annotations['defined_by'] = defined_by_elem.text
            
            # Check for alternative defined-by annotation
            alt_defined_by = element.find('.//oboInOwl:hasDbXref', namespaces)
            if alt_defined_by is not None and not annotations.get('defined_by'):
                annotations['alt_defined_by'] = alt_defined_by.text
                
            # Only store terms that have annotations
            if annotations:
                terms[term_iri] = annotations
        
        return terms
        
    except Exception as e:
        print(f"Error parsing {owl_file}: {str(e)}")
        return {}

def compare_annotations(file1: str, file2: str, name1: str, name2: str) -> Dict:
    """
    Compare annotations between two OWL files.
    
    Returns:
        Dictionary with comparison results
    """
    print(f"\\n🔍 Comparing {name1} vs {name2}...")
    
    terms1 = parse_owl_file(file1)
    terms2 = parse_owl_file(file2)
    
    # Find common terms
    common_terms = set(terms1.keys()) & set(terms2.keys())
    only_in_1 = set(terms1.keys()) - set(terms2.keys())
    only_in_2 = set(terms2.keys()) - set(terms1.keys())
    
    print(f"📊 Terms in {name1}: {len(terms1)}")
    print(f"📊 Terms in {name2}: {len(terms2)}")
    print(f"📊 Common terms: {len(common_terms)}")
    print(f"📊 Only in {name1}: {len(only_in_1)}")
    print(f"📊 Only in {name2}: {len(only_in_2)}")
    
    # Compare annotations for common terms
    annotation_differences = []
    defined_by_differences = []
    
    for term_iri in common_terms:
        ann1 = terms1[term_iri]
        ann2 = terms2[term_iri]
        
        # Check for defined_by differences (most important)
        def_by_1 = ann1.get('defined_by') or ann1.get('alt_defined_by')
        def_by_2 = ann2.get('defined_by') or ann2.get('alt_defined_by')
        
        if def_by_1 != def_by_2:
            defined_by_differences.append({
                'term': term_iri,
                'label': ann1.get('label', 'No label'),
                name1: def_by_1,
                name2: def_by_2
            })
        
        # Check for other annotation differences
        for ann_type in set(ann1.keys()) | set(ann2.keys()):
            if ann1.get(ann_type) != ann2.get(ann_type):
                if ann_type not in ['defined_by', 'alt_defined_by']:  # Already handled above
                    annotation_differences.append({
                        'term': term_iri,
                        'annotation_type': ann_type,
                        name1: ann1.get(ann_type),
                        name2: ann2.get(ann_type)
                    })
    
    return {
        'comparison': f"{name1} vs {name2}",
        'total_terms': {name1: len(terms1), name2: len(terms2)},
        'common_terms': len(common_terms),
        'unique_terms': {name1: len(only_in_1), name2: len(only_in_2)},
        'defined_by_differences': defined_by_differences,
        'annotation_differences': annotation_differences
    }

def robot_diff_analysis(file1: str, file2: str, name1: str, name2: str) -> Optional[str]:
    """
    Use ROBOT diff command to compare two OWL files.
    
    Returns:
        Diff output as string, or None if diff failed
    """
    try:
        robot_path = shutil.which('robot')
        if not robot_path:
            print("⚠️  ROBOT not found, skipping structural diff analysis")
            return None
        
        print(f"\\n🤖 Running ROBOT diff: {name1} vs {name2}...")
        
        # Create temporary diff file
        diff_file = f"/tmp/diff_{name1}_vs_{name2}.txt"
        
        result = subprocess.run([
            'robot', 'diff',
            '--left', file1,
            '--right', file2,
            '--output', diff_file
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            with open(diff_file, 'r') as f:
                diff_content = f.read()
            os.remove(diff_file)
            return diff_content
        else:
            print(f"⚠️  ROBOT diff failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"⚠️  ROBOT diff error: {str(e)}")
        return None

def analyze_order_impact(results_dir: str) -> Dict:
    """
    Analyze the impact of different ordering strategies.
    
    Returns:
        Analysis results
    """
    merge_files = {
        'alphabetical': os.path.join(results_dir, 'CDM_merged_alphabetical.owl'),
        'hierarchy': os.path.join(results_dir, 'CDM_merged_hierarchy.owl'),
        'size': os.path.join(results_dir, 'CDM_merged_size.owl')
    }
    
    # Check which files exist
    existing_files = {name: path for name, path in merge_files.items() if os.path.exists(path)}
    
    if len(existing_files) < 2:
        print("❌ Need at least 2 merge files to compare")
        return {}
    
    print(f"📁 Found {len(existing_files)} merge files to compare:")
    for name, path in existing_files.items():
        size = os.path.getsize(path) / (1024 * 1024)  # MB
        print(f"  {name:12}: {os.path.basename(path)} ({size:.1f} MB)")
    
    # Perform pairwise comparisons
    comparisons = []
    file_list = list(existing_files.items())
    
    for i in range(len(file_list)):
        for j in range(i + 1, len(file_list)):
            name1, file1 = file_list[i]
            name2, file2 = file_list[j]
            
            # Compare annotations
            comparison = compare_annotations(file1, file2, name1, name2)
            comparisons.append(comparison)
            
            # ROBOT structural diff
            robot_diff = robot_diff_analysis(file1, file2, name1, name2)
            if robot_diff:
                comparison['robot_diff'] = robot_diff[:1000]  # Truncate for summary
    
    return {
        'merge_files': existing_files,
        'comparisons': comparisons
    }

def generate_report(analysis: Dict, results_dir: str):
    """Generate a comprehensive comparison report."""
    
    report_file = os.path.join(results_dir, 'comparison_report.json')
    summary_file = os.path.join(results_dir, 'comparison_summary.txt')
    
    # Save detailed JSON report
    with open(report_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # Generate human-readable summary
    with open(summary_file, 'w') as f:
        f.write("ONTOLOGY ORDER COMPARISON SUMMARY\\n")
        f.write("=" * 50 + "\\n\\n")
        
        f.write(f"Generated files: {len(analysis.get('merge_files', {}))}\\n")
        for name, path in analysis.get('merge_files', {}).items():
            size = os.path.getsize(path) / (1024 * 1024)
            f.write(f"  {name:12}: {size:.1f} MB\\n")
        
        f.write(f"\\nComparisons performed: {len(analysis.get('comparisons', []))}\\n")
        
        for comp in analysis.get('comparisons', []):
            f.write(f"\\n{comp['comparison']}:\\n")
            f.write(f"  Common terms: {comp['common_terms']}\\n")
            f.write(f"  Defined-by differences: {len(comp['defined_by_differences'])}\\n")
            f.write(f"  Other annotation differences: {len(comp['annotation_differences'])}\\n")
            
            # Show some examples of defined-by differences
            if comp['defined_by_differences']:
                f.write(f"\\n  Key defined-by differences:\\n")
                for diff in comp['defined_by_differences'][:5]:  # Show first 5
                    f.write(f"    {diff['term']}:\\n")
                    f.write(f"      Label: {diff['label']}\\n")
                    names = [k for k in diff.keys() if k not in ['term', 'label']]
                    for name in names:
                        f.write(f"      {name}: {diff[name]}\\n")
                
                if len(comp['defined_by_differences']) > 5:
                    f.write(f"    ... and {len(comp['defined_by_differences']) - 5} more\\n")
    
    print(f"\\n📋 Reports generated:")
    print(f"  📄 Detailed: {report_file}")
    print(f"  📝 Summary: {summary_file}")

def main():
    """Main comparison function."""
    
    # Setup paths - self-contained in testing directory
    script_dir = os.path.dirname(__file__)
    results_dir = os.path.join(script_dir, 'results')
    
    if not os.path.exists(results_dir):
        print("❌ Results directory not found. Run test_merge_orders.py first.")
        return 1
    
    print("🔍 Ontology Order Comparison Analysis")
    print("=" * 50)
    
    # Analyze order impact
    analysis = analyze_order_impact(results_dir)
    
    if not analysis:
        print("❌ No analysis could be performed")
        return 1
    
    # Generate reports
    generate_report(analysis, results_dir)
    
    # Summary findings
    print("\\n" + "=" * 50)
    print("🏁 COMPARISON SUMMARY")
    print("=" * 50)
    
    total_diffs = 0
    for comp in analysis.get('comparisons', []):
        defined_by_diffs = len(comp['defined_by_differences'])
        total_diffs += defined_by_diffs
        
        if defined_by_diffs > 0:
            print(f"⚠️  {comp['comparison']}: {defined_by_diffs} defined-by differences")
        else:
            print(f"✅ {comp['comparison']}: No defined-by differences")
    
    if total_diffs == 0:
        print("\\n🎉 All merge orders produce identical term attribution!")
    else:
        print(f"\\n⚠️  Found {total_diffs} total defined-by differences across orders")
        print("💡 This suggests ontology order matters for term attribution")
    
    print("\\n📋 Check comparison_summary.txt for detailed findings")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())