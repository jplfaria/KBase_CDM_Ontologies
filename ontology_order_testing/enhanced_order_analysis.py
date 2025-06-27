#!/usr/bin/env python3
"""
Enhanced Order Analysis for 24 Ontologies

This script provides comprehensive testing of ontology merge order effects,
including tracking key terms across ontologies and comparing both merge-only
and merge+removes operations.
"""

import os
import sys
import subprocess
import json
import itertools
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

# Key terms to track across different ontologies (excluding NCBITaxon)
KEY_TERMS = {
    'upper_level': {
        'BFO:0000001': 'entity',
        'BFO:0000002': 'continuant', 
        'BFO:0000003': 'occurrent',
        'RO:0000056': 'participates in',
        'RO:0002333': 'enabled by',
        'IAO:0000030': 'information content entity'
    },
    'chemical': {
        'CHEBI:24431': 'chemical entity',
        'CHEBI:15377': 'water',
        'CHEBI:16236': 'ethanol',
        'CHEBI:17234': 'glucose',
        'CHEBI:15422': 'ATP'
    },
    'anatomical': {
        'UBERON:0000061': 'anatomical structure',
        'UBERON:0001062': 'anatomical entity',
        'UBERON:0000479': 'tissue',
        'PO:0009005': 'root',
        'CL:0000000': 'cell'
    },
    'process': {
        'GO:0008150': 'biological_process',
        'GO:0003674': 'molecular_function',
        'GO:0005575': 'cellular_component',
        'ENVO:01000254': 'environmental system',
        'PATO:0000001': 'quality'
    },
    'molecular': {
        'SO:0000704': 'gene',
        'SO:0000234': 'mRNA',
        'SO:0000110': 'sequence_feature'
    }
}

class EnhancedOrderAnalyzer:
    def __init__(self, testing_dir: str):
        self.testing_dir = Path(testing_dir)
        self.data_dir = self.testing_dir / 'data'
        self.results_dir = self.testing_dir / 'results'
        self.utils_dir = self.results_dir / 'utils'
        
        # Ensure directories exist
        self.results_dir.mkdir(exist_ok=True)
        self.utils_dir.mkdir(exist_ok=True)
        
        # Flatten key terms for easier access
        self.all_key_terms = {}
        for category, terms in KEY_TERMS.items():
            for term_id, label in terms.items():
                self.all_key_terms[term_id] = {
                    'label': label,
                    'category': category,
                    'iri': f'http://purl.obolibrary.org/obo/{term_id.replace(":", "_")}'
                }
    
    def get_ontology_files(self) -> List[str]:
        """Get list of ontology files in order specified by configs."""
        # Read from the full source list
        source_file = self.testing_dir / 'ontologies_source_full.txt'
        if not source_file.exists():
            raise FileNotFoundError(f"Ontology source file not found: {source_file}")
        
        ontologies = []
        with open(source_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    url = line.split('#')[0].strip()
                    if url.endswith('.owl') or url.endswith('.owl.gz'):
                        # Extract filename from URL
                        filename = url.split('/')[-1]
                        # Remove .gz extension if present
                        if filename.endswith('.gz'):
                            filename = filename[:-3]
                        
                        # Check if file actually exists in data directory
                        file_path = self.data_dir / filename
                        if file_path.exists():
                            ontologies.append(filename)
        
        return ontologies
    
    def run_merge_test(self, order_name: str, ontology_order: List[str], 
                      include_removes: bool = True) -> Dict:
        """Run a merge test with specified order and options."""
        
        print(f"\n🧪 Running {order_name} merge test (removes={'on' if include_removes else 'off'})...")
        
        suffix = "_with_removes" if include_removes else "_merge_only"
        output_file = self.results_dir / f'CDM_merged_{order_name}{suffix}.owl'
        
        # Build ROBOT command
        robot_command = ['robot', 'merge', '--annotate-defined-by', 'true']
        
        # Add input files in specified order
        for filename in ontology_order:
            file_path = self.data_dir / filename
            if not file_path.exists():
                print(f"  ⚠️  Missing: {filename}")
                continue
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
        
        print(f"  🚀 Running ROBOT merge...")
        
        try:
            # Run with memory monitoring if enabled
            env = os.environ.copy()
            if env.get('ENABLE_MEMORY_MONITORING', 'false').lower() == 'true':
                # Use memory monitoring
                memory_script = self.testing_dir.parent / 'scripts' / 'memory_monitor.py'
                if memory_script.exists():
                    tool_name = f"ROBOT_{order_name}{suffix}"
                    monitor_cmd = [
                        'python', str(memory_script),
                        tool_name,
                        ' '.join(robot_command),
                        str(self.utils_dir)
                    ]
                    result = subprocess.run(monitor_cmd, capture_output=True, text=True, env=env)
                else:
                    result = subprocess.run(robot_command, capture_output=True, text=True, env=env)
            else:
                result = subprocess.run(robot_command, capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                print(f"  ✅ Success: {output_file.name}")
                
                # Get file stats
                file_size = output_file.stat().st_size
                
                # Count axioms and classes
                axiom_count = self.count_axioms(output_file)
                class_count = self.count_classes(output_file)
                
                return {
                    'success': True,
                    'output_file': str(output_file),
                    'file_size': file_size,
                    'axiom_count': axiom_count,
                    'class_count': class_count,
                    'command': robot_command
                }
            else:
                print(f"  ❌ Failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'command': robot_command
                }
                
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'command': robot_command
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
        """Extract definer information for key terms."""
        definers = {}
        
        for term_id, term_info in self.all_key_terms.items():
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
                            'label': term_info['label'],
                            'category': term_info['category']
                        }
            except:
                continue
        
        return definers
    
    def run_comprehensive_analysis(self) -> Dict:
        """Run comprehensive analysis with different orders and remove options."""
        
        print("🔍 Enhanced Order Analysis - 24 Ontologies")
        print("=" * 60)
        
        # Get ontology list
        ontologies = self.get_ontology_files()
        print(f"📊 Testing with {len(ontologies)} ontologies")
        
        # Define test orders
        orders = {
            'alphabetical': sorted(ontologies),
            'hierarchy': self.get_hierarchy_order(ontologies),
            'size': self.get_size_order(ontologies)
        }
        
        results = {}
        
        # Test each order with and without removes
        for order_name, ontology_order in orders.items():
            results[order_name] = {}
            
            # Test merge only
            merge_result = self.run_merge_test(order_name, ontology_order, include_removes=False)
            results[order_name]['merge_only'] = merge_result
            
            if merge_result['success']:
                # Extract key term definers for merge-only
                owl_file = Path(merge_result['output_file'])
                results[order_name]['merge_only']['key_term_definers'] = self.extract_key_term_definers(owl_file)
            
            # Test merge with removes  
            full_result = self.run_merge_test(order_name, ontology_order, include_removes=True)
            results[order_name]['with_removes'] = full_result
            
            if full_result['success']:
                # Extract key term definers for full merge
                owl_file = Path(full_result['output_file'])
                results[order_name]['with_removes']['key_term_definers'] = self.extract_key_term_definers(owl_file)
        
        # Analyze differences
        analysis = self.analyze_results(results)
        
        # Save comprehensive results
        output_file = self.results_dir / 'enhanced_analysis_results.json'
        with open(output_file, 'w') as f:
            json.dump({
                'results': results,
                'analysis': analysis,
                'key_terms_tested': self.all_key_terms
            }, f, indent=2)
        
        print(f"\n📋 Results saved to: {output_file}")
        
        return {'results': results, 'analysis': analysis}
    
    def get_hierarchy_order(self, ontologies: List[str]) -> List[str]:
        """Get hierarchical order (foundational -> domain -> reference)."""
        # Read from existing hierarchy config
        hierarchy_file = self.testing_dir / 'configs' / 'order_hierarchy.txt'
        if hierarchy_file.exists():
            hierarchy_order = []
            with open(hierarchy_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        filename = line.split('#')[0].strip()
                        if filename in ontologies:
                            hierarchy_order.append(filename)
            return hierarchy_order
        
        # Fallback: basic hierarchy
        return sorted(ontologies)
    
    def get_size_order(self, ontologies: List[str]) -> List[str]:
        """Get size-based order (largest first)."""
        # Read from existing size config
        size_file = self.testing_dir / 'configs' / 'order_size.txt'
        if size_file.exists():
            size_order = []
            with open(size_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        filename = line.split('#')[0].strip()
                        if filename in ontologies:
                            size_order.append(filename)
            return size_order
        
        # Fallback: basic size order
        return sorted(ontologies)
    
    def analyze_results(self, results: Dict) -> Dict:
        """Analyze differences between orders and remove operations."""
        analysis = {
            'order_differences': {},
            'remove_operation_impact': {},
            'key_term_attribution_differences': {},
            'summary': {}
        }
        
        # Compare orders for merge-only
        orders = list(results.keys())
        for i, order1 in enumerate(orders):
            for order2 in orders[i+1:]:
                if (results[order1].get('merge_only', {}).get('success') and 
                    results[order2].get('merge_only', {}).get('success')):
                    
                    comparison = self.compare_merge_results(
                        results[order1]['merge_only'], 
                        results[order2]['merge_only'],
                        f"{order1}_vs_{order2}_merge_only"
                    )
                    analysis['order_differences'][f"{order1}_vs_{order2}"] = comparison
        
        # Compare remove operation impact for each order
        for order in orders:
            if (results[order].get('merge_only', {}).get('success') and 
                results[order].get('with_removes', {}).get('success')):
                
                impact = self.compare_merge_results(
                    results[order]['merge_only'],
                    results[order]['with_removes'],
                    f"{order}_remove_impact"
                )
                analysis['remove_operation_impact'][order] = impact
        
        # Analyze key term attribution differences
        analysis['key_term_attribution_differences'] = self.analyze_key_term_differences(results)
        
        # Create summary
        analysis['summary'] = self.create_analysis_summary(analysis)
        
        return analysis
    
    def compare_merge_results(self, result1: Dict, result2: Dict, comparison_name: str) -> Dict:
        """Compare two merge results."""
        comparison = {
            'file_size_diff': result2['file_size'] - result1['file_size'],
            'axiom_count_diff': result2['axiom_count'] - result1['axiom_count'],
            'class_count_diff': result2['class_count'] - result1['class_count']
        }
        
        # Compare key term definers if available
        definers1 = result1.get('key_term_definers', {})
        definers2 = result2.get('key_term_definers', {})
        
        different_definers = {}
        for term_id in set(definers1.keys()) | set(definers2.keys()):
            def1 = definers1.get(term_id, {}).get('definer', 'missing')
            def2 = definers2.get(term_id, {}).get('definer', 'missing')
            
            if def1 != def2:
                different_definers[term_id] = {
                    'result1': def1,
                    'result2': def2,
                    'label': definers1.get(term_id, definers2.get(term_id, {})).get('label', 'unknown')
                }
        
        comparison['different_definers'] = different_definers
        comparison['definer_differences_count'] = len(different_definers)
        
        return comparison
    
    def analyze_key_term_differences(self, results: Dict) -> Dict:
        """Analyze key term attribution differences across all tests."""
        term_analysis = {}
        
        for term_id, term_info in self.all_key_terms.items():
            term_analysis[term_id] = {
                'label': term_info['label'],
                'category': term_info['category'],
                'definers_across_tests': {}
            }
            
            # Collect definers across all tests
            for order in results:
                for test_type in ['merge_only', 'with_removes']:
                    test_key = f"{order}_{test_type}"
                    definers = results[order].get(test_type, {}).get('key_term_definers', {})
                    
                    if term_id in definers:
                        definer = definers[term_id]['definer']
                        term_analysis[term_id]['definers_across_tests'][test_key] = definer
            
            # Check if there are differences
            unique_definers = set(term_analysis[term_id]['definers_across_tests'].values())
            term_analysis[term_id]['has_differences'] = len(unique_definers) > 1
            term_analysis[term_id]['unique_definers'] = list(unique_definers)
        
        return term_analysis
    
    def create_analysis_summary(self, analysis: Dict) -> Dict:
        """Create a high-level summary of the analysis."""
        summary = {
            'orders_tested': [],
            'tests_with_differences': 0,
            'terms_with_different_definers': 0,
            'remove_operations_impact': False,
            'key_findings': []
        }
        
        # Count differences
        for comparison in analysis['order_differences'].values():
            if comparison['definer_differences_count'] > 0:
                summary['tests_with_differences'] += 1
        
        # Count terms with differences
        for term_data in analysis['key_term_attribution_differences'].values():
            if term_data['has_differences']:
                summary['terms_with_different_definers'] += 1
        
        # Check remove operation impact
        for impact in analysis['remove_operation_impact'].values():
            if (impact['file_size_diff'] != 0 or 
                impact['axiom_count_diff'] != 0 or 
                impact['definer_differences_count'] > 0):
                summary['remove_operations_impact'] = True
                break
        
        # Generate key findings
        if summary['terms_with_different_definers'] > 0:
            summary['key_findings'].append(f"Order affects term attribution for {summary['terms_with_different_definers']} key terms")
        
        if summary['remove_operations_impact']:
            summary['key_findings'].append("Remove operations impact varies with order")
        
        if summary['tests_with_differences'] == 0:
            summary['key_findings'].append("No significant differences found between orders")
        
        return summary

def main():
    """Main function for enhanced order analysis."""
    # Get the testing directory
    script_dir = Path(__file__).parent
    
    analyzer = EnhancedOrderAnalyzer(str(script_dir))
    
    try:
        results = analyzer.run_comprehensive_analysis()
        
        print("\n" + "=" * 60)
        print("🏁 ENHANCED ANALYSIS SUMMARY")
        print("=" * 60)
        
        summary = results['analysis']['summary']
        print(f"Terms with different definers: {summary['terms_with_different_definers']}")
        print(f"Tests with differences: {summary['tests_with_differences']}")
        print(f"Remove operations impact: {summary['remove_operations_impact']}")
        
        print("\nKey findings:")
        for finding in summary['key_findings']:
            print(f"  • {finding}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())