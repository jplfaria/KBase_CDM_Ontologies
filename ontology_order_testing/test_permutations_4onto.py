#!/usr/bin/env python3
"""
Test All Permutations of 4 Ontologies

This script tests all 24 permutations of CHEBI, FOODON, GO, and ENVO
to definitively determine if merge order affects term attribution.
"""

import os
import sys
import subprocess
import json
import itertools
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

# Import enhanced metrics collector
sys.path.insert(0, os.path.dirname(__file__))
from enhanced_metrics import EnhancedMetricsCollector

# The 4 ontologies with known relationships
TEST_ONTOLOGIES = [
    'chebi.owl',        # Base chemical ontology (783MB)
    'foodon-base.owl',  # Imports CHEBI terms
    'go.owl',           # Also imports CHEBI (121MB)  
    'envo.owl'          # References both CHEBI and GO
]

# Key CHEBI terms that should be present in multiple ontologies
KEY_CHEBI_TERMS = {
    'CHEBI:24431': 'chemical entity',      # Top-level chemical
    'CHEBI:15377': 'water',               # Referenced in ENVO, GO, FOODON
    'CHEBI:16236': 'ethanol',             # In FOODON, GO, CHEBI
    'CHEBI:17234': 'glucose',             # Metabolic pathways
    'CHEBI:15422': 'ATP',                 # Energy metabolism
    'CHEBI:36080': 'protein',             # Referenced across ontologies
    'CHEBI:33697': 'ribonucleic acid',    # RNA terms
    'CHEBI:16541': 'protein polypeptide chain'
}

class PermutationTester:
    def __init__(self, testing_dir: str):
        self.testing_dir = Path(testing_dir)
        self.data_dir = self.testing_dir / 'data'
        self.results_dir = self.testing_dir / 'results'
        self.perm_results_dir = self.results_dir / 'permutation_tests'
        self.utils_dir = self.results_dir / 'utils'
        
        # Ensure directories exist
        self.results_dir.mkdir(exist_ok=True)
        self.perm_results_dir.mkdir(exist_ok=True)
        self.utils_dir.mkdir(exist_ok=True)
        
        # Initialize metrics collector
        self.metrics_collector = EnhancedMetricsCollector()
        
        # Convert key terms to IRI format
        self.key_term_iris = {}
        for term_id, label in KEY_CHEBI_TERMS.items():
            self.key_term_iris[term_id] = {
                'iri': f'http://purl.obolibrary.org/obo/{term_id.replace(":", "_")}',
                'label': label
            }
    
    def verify_ontologies_exist(self) -> bool:
        """Verify all test ontologies exist."""
        missing = []
        for onto in TEST_ONTOLOGIES:
            if not (self.data_dir / onto).exists():
                missing.append(onto)
        
        if missing:
            print(f"❌ Missing ontologies: {missing}")
            return False
        
        print(f"✅ All {len(TEST_ONTOLOGIES)} test ontologies found")
        return True
    
    def run_merge_permutation(self, perm_num: int, ontology_order: List[str], 
                             include_removes: bool = True) -> Dict:
        """Run merge test for a specific permutation."""
        
        suffix = "_with_removes" if include_removes else "_merge_only"
        output_file = self.perm_results_dir / f'perm_{perm_num:02d}{suffix}.owl'
        
        # Build ROBOT command
        robot_command = ['robot', 'merge', '--annotate-defined-by', 'true']
        
        # Add input files in specified order
        for filename in ontology_order:
            file_path = self.data_dir / filename
            robot_command.extend(['--input', str(file_path)])
        
        # Add remove operations if requested
        if include_removes:
            robot_command.extend([
                'remove', '--axioms', 'disjoint',
                '--trim', 'true', '--preserve-structure', 'false'
            ])
            robot_command.extend([
                'remove', '--term', 'owl:Nothing',
                '--trim', 'true', '--preserve-structure', 'false'
            ])
        
        # Add output
        robot_command.extend(['--output', str(output_file)])
        
        try:
            # Run with environment variables
            env = os.environ.copy()
            result = subprocess.run(robot_command, capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                # Get file stats
                file_size = output_file.stat().st_size
                
                # Collect enhanced metrics
                metrics = self.metrics_collector.collect_all_metrics(output_file)
                
                # Extract key counts
                basic_counts = metrics.get('basic_counts', {})
                axiom_count = basic_counts.get('total_axioms', 0)
                class_count = basic_counts.get('total_classes', 0)
                
                # Extract key term definers
                definers = self.extract_key_term_definers(output_file)
                
                return {
                    'success': True,
                    'permutation': perm_num,
                    'order': ontology_order,
                    'output_file': str(output_file),
                    'file_size': file_size,
                    'axiom_count': axiom_count,
                    'class_count': class_count,
                    'key_term_definers': definers,
                    'enhanced_metrics': metrics,
                    'include_removes': include_removes
                }
            else:
                print(f"  ❌ ROBOT failed: {result.stderr[:200]}...")
                return {
                    'success': False,
                    'permutation': perm_num,
                    'order': ontology_order,
                    'error': result.stderr,
                    'include_removes': include_removes
                }
                
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
            return {
                'success': False,
                'permutation': perm_num,
                'order': ontology_order,
                'error': str(e),
                'include_removes': include_removes
            }
    
    def count_axioms(self, owl_file: Path) -> int:
        """Count total axioms in OWL file."""
        try:
            result = subprocess.run([
                'robot', 'measure',
                '--input', str(owl_file),
                '--metric', 'Axiom count'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return int(result.stdout.strip())
        except:
            pass
        return 0
    
    def count_classes(self, owl_file: Path) -> int:
        """Count classes in OWL file."""
        try:
            query = '''
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                SELECT (COUNT(DISTINCT ?s) as ?count)
                WHERE { ?s a owl:Class }
            '''
            
            result = subprocess.run([
                'robot', 'query',
                '--input', str(owl_file),
                '--query', query,
                '--format', 'csv'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return int(lines[1])
        except:
            pass
        return 0
    
    def extract_key_term_definers(self, owl_file: Path) -> Dict:
        """Extract definer information for key CHEBI terms."""
        definers = {}
        
        for term_id, term_info in self.key_term_iris.items():
            query = f'''
                PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
                SELECT ?definer
                WHERE {{
                    <{term_info['iri']}> oboInOwl:isDefinedBy ?definer .
                }}
            '''
            
            try:
                result = subprocess.run([
                    'robot', 'query',
                    '--input', str(owl_file),
                    '--query', query,
                    '--format', 'csv'
                ], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1 and lines[1]:
                        definers[term_id] = {
                            'definer': lines[1],
                            'label': term_info['label']
                        }
            except:
                continue
        
        return definers
    
    def run_all_permutations(self) -> Dict:
        """Run all 24 permutations of the 4 ontologies."""
        
        print("🧪 4-Ontology Permutation Testing")
        print("=" * 50)
        print(f"📊 Testing ontologies: {TEST_ONTOLOGIES}")
        print(f"🔢 Total permutations: {len(list(itertools.permutations(TEST_ONTOLOGIES)))}")
        
        if not self.verify_ontologies_exist():
            return {'error': 'Missing ontologies'}
        
        results = {
            'merge_only': {},
            'with_removes': {},
            'metadata': {
                'test_ontologies': TEST_ONTOLOGIES,
                'key_terms_tested': KEY_CHEBI_TERMS,
                'total_permutations': 24
            }
        }
        
        # Generate all permutations
        permutations = list(itertools.permutations(TEST_ONTOLOGIES))
        
        print(f"\n🚀 Running permutation tests...")
        
        for perm_num, ontology_order in enumerate(permutations, 1):
            print(f"\n📋 Permutation {perm_num:2d}/24: {' → '.join(ontology_order)}")
            
            # Test merge only
            print("  🔄 Testing merge-only...")
            merge_result = self.run_merge_permutation(perm_num, list(ontology_order), include_removes=False)
            results['merge_only'][perm_num] = merge_result
            
            if merge_result['success']:
                print(f"    ✅ Success: {merge_result['file_size']:,} bytes, {merge_result['axiom_count']} axioms")
            else:
                print(f"    ❌ Failed")
            
            # Test merge with removes
            print("  🔄 Testing merge+removes...")
            remove_result = self.run_merge_permutation(perm_num, list(ontology_order), include_removes=True)
            results['with_removes'][perm_num] = remove_result
            
            if remove_result['success']:
                print(f"    ✅ Success: {remove_result['file_size']:,} bytes, {remove_result['axiom_count']} axioms")
            else:
                print(f"    ❌ Failed")
        
        # Analyze results
        analysis = self.analyze_permutation_results(results)
        results['analysis'] = analysis
        
        # Save results
        output_file = self.results_dir / 'permutation_test_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📋 Results saved to: {output_file}")
        
        return results
    
    def analyze_permutation_results(self, results: Dict) -> Dict:
        """Analyze differences across all permutations."""
        analysis = {
            'merge_only_analysis': {},
            'with_removes_analysis': {},
            'remove_operation_impact': {},
            'term_attribution_analysis': {},
            'summary': {}
        }
        
        # Analyze merge-only results
        merge_results = [r for r in results['merge_only'].values() if r['success']]
        if merge_results:
            analysis['merge_only_analysis'] = self.analyze_result_set(merge_results, 'merge_only')
        
        # Analyze with-removes results
        remove_results = [r for r in results['with_removes'].values() if r['success']]
        if remove_results:
            analysis['with_removes_analysis'] = self.analyze_result_set(remove_results, 'with_removes')
        
        # Analyze remove operation impact for each permutation
        for perm_num in range(1, 25):
            merge_result = results['merge_only'].get(perm_num, {})
            remove_result = results['with_removes'].get(perm_num, {})
            
            if merge_result.get('success') and remove_result.get('success'):
                impact = {
                    'permutation': perm_num,
                    'order': merge_result['order'],
                    'file_size_diff': remove_result['file_size'] - merge_result['file_size'],
                    'axiom_count_diff': remove_result['axiom_count'] - merge_result['axiom_count'],
                    'class_count_diff': remove_result['class_count'] - merge_result['class_count']
                }
                analysis['remove_operation_impact'][perm_num] = impact
        
        # Analyze term attribution patterns
        analysis['term_attribution_analysis'] = self.analyze_term_attribution(results)
        
        # Create summary
        analysis['summary'] = self.create_permutation_summary(analysis)
        
        return analysis
    
    def analyze_result_set(self, results: List[Dict], test_type: str) -> Dict:
        """Analyze a set of results for patterns."""
        if not results:
            return {}
        
        # Collect metrics
        file_sizes = [r['file_size'] for r in results]
        axiom_counts = [r['axiom_count'] for r in results]
        class_counts = [r['class_count'] for r in results]
        
        # Check for variations
        unique_file_sizes = set(file_sizes)
        unique_axiom_counts = set(axiom_counts)
        unique_class_counts = set(class_counts)
        
        analysis = {
            'total_permutations': len(results),
            'file_size_range': {
                'min': min(file_sizes),
                'max': max(file_sizes),
                'unique_values': len(unique_file_sizes)
            },
            'axiom_count_range': {
                'min': min(axiom_counts),
                'max': max(axiom_counts),
                'unique_values': len(unique_axiom_counts)
            },
            'class_count_range': {
                'min': min(class_counts),
                'max': max(class_counts),
                'unique_values': len(unique_class_counts)
            },
            'has_variations': (len(unique_file_sizes) > 1 or 
                             len(unique_axiom_counts) > 1 or 
                             len(unique_class_counts) > 1)
        }
        
        return analysis
    
    def analyze_term_attribution(self, results: Dict) -> Dict:
        """Analyze how term attribution varies across permutations."""
        attribution_analysis = {}
        
        for term_id, term_info in self.key_term_iris.items():
            attribution_analysis[term_id] = {
                'label': term_info['label'],
                'definers_merge_only': {},
                'definers_with_removes': {},
                'varies_with_order': False
            }
            
            # Collect definers for merge-only
            for perm_num, result in results['merge_only'].items():
                if result.get('success') and 'key_term_definers' in result:
                    definers = result['key_term_definers']
                    if term_id in definers:
                        definer = definers[term_id]['definer']
                        order_str = ' → '.join(result['order'])
                        attribution_analysis[term_id]['definers_merge_only'][order_str] = definer
            
            # Collect definers for with-removes
            for perm_num, result in results['with_removes'].items():
                if result.get('success') and 'key_term_definers' in result:
                    definers = result['key_term_definers']
                    if term_id in definers:
                        definer = definers[term_id]['definer']
                        order_str = ' → '.join(result['order'])
                        attribution_analysis[term_id]['definers_with_removes'][order_str] = definer
            
            # Check if attribution varies
            merge_definers = set(attribution_analysis[term_id]['definers_merge_only'].values())
            remove_definers = set(attribution_analysis[term_id]['definers_with_removes'].values())
            
            attribution_analysis[term_id]['varies_with_order'] = (
                len(merge_definers) > 1 or len(remove_definers) > 1
            )
            attribution_analysis[term_id]['unique_definers_merge'] = list(merge_definers)
            attribution_analysis[term_id]['unique_definers_removes'] = list(remove_definers)
        
        return attribution_analysis
    
    def create_permutation_summary(self, analysis: Dict) -> Dict:
        """Create a high-level summary of permutation testing."""
        summary = {
            'total_permutations_tested': 24,
            'successful_merge_only': 0,
            'successful_with_removes': 0,
            'merge_only_has_variations': False,
            'with_removes_has_variations': False,
            'terms_with_order_dependent_attribution': 0,
            'remove_operations_vary_by_order': False,
            'key_findings': []
        }
        
        # Count successful tests
        if 'merge_only_analysis' in analysis:
            summary['successful_merge_only'] = analysis['merge_only_analysis'].get('total_permutations', 0)
            summary['merge_only_has_variations'] = analysis['merge_only_analysis'].get('has_variations', False)
        
        if 'with_removes_analysis' in analysis:
            summary['successful_with_removes'] = analysis['with_removes_analysis'].get('total_permutations', 0)
            summary['with_removes_has_variations'] = analysis['with_removes_analysis'].get('has_variations', False)
        
        # Count terms with order-dependent attribution
        for term_data in analysis.get('term_attribution_analysis', {}).values():
            if term_data.get('varies_with_order', False):
                summary['terms_with_order_dependent_attribution'] += 1
        
        # Check if remove operations vary by order
        remove_impacts = analysis.get('remove_operation_impact', {})
        if remove_impacts:
            file_size_diffs = set(impact['file_size_diff'] for impact in remove_impacts.values())
            axiom_diffs = set(impact['axiom_count_diff'] for impact in remove_impacts.values())
            summary['remove_operations_vary_by_order'] = (len(file_size_diffs) > 1 or len(axiom_diffs) > 1)
        
        # Generate key findings
        if summary['terms_with_order_dependent_attribution'] > 0:
            summary['key_findings'].append(
                f"Order affects term attribution for {summary['terms_with_order_dependent_attribution']} key terms"
            )
        
        if summary['merge_only_has_variations']:
            summary['key_findings'].append("Merge order affects final results even without remove operations")
        
        if summary['remove_operations_vary_by_order']:
            summary['key_findings'].append("Remove operations impact varies depending on merge order")
        
        if not summary['key_findings']:
            summary['key_findings'].append("No significant order-dependent differences detected")
        
        return summary

def main():
    """Main function for permutation testing."""
    # Get the testing directory
    script_dir = Path(__file__).parent
    
    tester = PermutationTester(str(script_dir))
    
    try:
        results = tester.run_all_permutations()
        
        if 'error' in results:
            print(f"❌ Testing failed: {results['error']}")
            return 1
        
        print("\n" + "=" * 50)
        print("🏁 PERMUTATION TESTING SUMMARY")
        print("=" * 50)
        
        summary = results['analysis']['summary']
        print(f"Successful tests (merge-only): {summary['successful_merge_only']}/24")
        print(f"Successful tests (with-removes): {summary['successful_with_removes']}/24")
        print(f"Terms with order-dependent attribution: {summary['terms_with_order_dependent_attribution']}")
        print(f"Remove operations vary by order: {summary['remove_operations_vary_by_order']}")
        
        print("\nKey findings:")
        for finding in summary['key_findings']:
            print(f"  • {finding}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())