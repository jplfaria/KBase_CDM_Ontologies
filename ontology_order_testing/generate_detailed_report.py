#!/usr/bin/env python3
"""
Generate Detailed Comparison Report

Creates in-depth analysis of differences between merge orders.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

# Import enhanced metrics
sys.path.insert(0, os.path.dirname(__file__))
from enhanced_metrics import EnhancedMetricsCollector

class DetailedReportGenerator:
    def __init__(self, testing_dir: str):
        self.testing_dir = Path(testing_dir)
        self.results_dir = self.testing_dir / 'results'
        self.metrics_collector = EnhancedMetricsCollector()
        
    def generate_detailed_comparison(self) -> str:
        """Generate detailed comparison report from test results."""
        
        report_lines = []
        report_lines.append("DETAILED ORDER COMPARISON REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Load enhanced analysis results
        enhanced_file = self.results_dir / 'enhanced_analysis_results.json'
        if enhanced_file.exists():
            with open(enhanced_file, 'r') as f:
                enhanced_data = json.load(f)
            
            report_lines.extend(self.analyze_enhanced_results(enhanced_data))
        
        # Load permutation test results  
        perm_file = self.results_dir / 'permutation_test_results.json'
        if perm_file.exists():
            with open(perm_file, 'r') as f:
                perm_data = json.load(f)
            
            report_lines.extend(self.analyze_permutation_results(perm_data))
        
        return '\n'.join(report_lines)
    
    def analyze_enhanced_results(self, data: Dict) -> List[str]:
        """Analyze enhanced test results in detail."""
        lines = []
        lines.append("=" * 80)
        lines.append("24-ONTOLOGY ENHANCED ANALYSIS - DETAILED FINDINGS")
        lines.append("=" * 80)
        
        results = data.get('results', {})
        
        # Collect successful results
        successful_tests = []
        for order, order_results in results.items():
            for test_type in ['merge_only', 'with_removes']:
                test_data = order_results.get(test_type, {})
                if test_data.get('success'):
                    successful_tests.append({
                        'order': order,
                        'test_type': test_type,
                        'data': test_data
                    })
        
        if len(successful_tests) < 2:
            lines.append("⚠️  Not enough successful tests for comparison")
            return lines
        
        # Compare each pair of successful tests
        lines.append("\n📊 PAIRWISE COMPARISONS")
        lines.append("-" * 60)
        
        for i, test1 in enumerate(successful_tests):
            for test2 in successful_tests[i+1:]:
                lines.extend(self.compare_test_pair(test1, test2))
        
        # Analyze definer patterns
        lines.append("\n🏷️  TERM ATTRIBUTION ANALYSIS")
        lines.append("-" * 60)
        
        definer_patterns = self.analyze_definer_patterns(successful_tests)
        for pattern, info in definer_patterns.items():
            lines.append(f"\n{pattern}:")
            for key, value in info.items():
                lines.append(f"  {key}: {value}")
        
        return lines
    
    def compare_test_pair(self, test1: Dict, test2: Dict) -> List[str]:
        """Compare two test results in detail."""
        lines = []
        
        label1 = f"{test1['order']}_{test1['test_type']}"
        label2 = f"{test2['order']}_{test2['test_type']}"
        
        lines.append(f"\n🔍 Comparing: {label1} vs {label2}")
        
        # Basic comparisons
        data1 = test1['data']
        data2 = test2['data']
        
        size_diff = data2['file_size'] - data1['file_size']
        size_pct = (size_diff / data1['file_size']) * 100 if data1['file_size'] > 0 else 0
        
        lines.append(f"  File size difference: {size_diff:,} bytes ({size_pct:+.2f}%)")
        
        # Enhanced metrics comparison
        if 'enhanced_metrics' in data1 and 'enhanced_metrics' in data2:
            metrics1 = data1['enhanced_metrics']
            metrics2 = data2['enhanced_metrics']
            
            comparison = self.metrics_collector.compare_metrics(
                metrics1, metrics2, label1, label2
            )
            
            # Show count differences
            if comparison['basic_count_diffs']:
                lines.append(f"  Count differences:")
                for metric, diff in comparison['basic_count_diffs'].items():
                    lines.append(f"    {metric}: {diff[label1]:,} → {diff[label2]:,} ({diff['difference']:+,})")
            
            # Show axiom type differences
            if comparison['axiom_type_diffs']:
                lines.append(f"  Axiom type differences:")
                for axiom_type, diff in comparison['axiom_type_diffs'].items():
                    lines.append(f"    {axiom_type}: {diff[label1]:,} → {diff[label2]:,} ({diff['difference']:+,})")
            
            # Show definer differences
            if comparison['definer_differences']:
                lines.append(f"  Term attribution differences:")
                for definer, diff in sorted(comparison['definer_differences'].items())[:10]:
                    lines.append(f"    {definer}: {diff[label1]:,} → {diff[label2]:,} ({diff['difference']:+,})")
                
                if len(comparison['definer_differences']) > 10:
                    lines.append(f"    ... and {len(comparison['definer_differences']) - 10} more differences")
        
        return lines
    
    def analyze_definer_patterns(self, tests: List[Dict]) -> Dict:
        """Analyze patterns in term attribution across tests."""
        patterns = {}
        
        # Collect all definer data
        all_definers = {}
        for test in tests:
            test_id = f"{test['order']}_{test['test_type']}"
            if 'enhanced_metrics' in test['data']:
                metrics = test['data']['enhanced_metrics']
                definers = metrics.get('annotation_properties', {}).get('defined_by_counts', {})
                all_definers[test_id] = definers
        
        # Find ontologies that change definers based on order
        volatile_ontologies = set()
        stable_ontologies = set()
        
        for onto in ['CHEBI', 'GO', 'UBERON', 'ENVO', 'FOODON']:
            onto_url = f"http://purl.obolibrary.org/obo/{onto.lower()}.owl"
            counts = [definers.get(onto_url, 0) for definers in all_definers.values()]
            
            if len(set(counts)) > 1:
                volatile_ontologies.add(onto)
                patterns[f"{onto} Attribution Volatility"] = {
                    'status': 'VOLATILE',
                    'unique_counts': len(set(counts)),
                    'count_range': f"{min(counts):,} - {max(counts):,}",
                    'variation': f"{max(counts) - min(counts):,}"
                }
            else:
                stable_ontologies.add(onto)
        
        patterns['Summary'] = {
            'volatile_ontologies': list(volatile_ontologies),
            'stable_ontologies': list(stable_ontologies),
            'total_tested': len(all_definers)
        }
        
        return patterns
    
    def analyze_permutation_results(self, data: Dict) -> List[str]:
        """Analyze permutation test results in detail."""
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("4-ONTOLOGY PERMUTATION TESTS - DETAILED FINDINGS")
        lines.append("=" * 80)
        
        merge_only = data.get('merge_only', {})
        with_removes = data.get('with_removes', {})
        
        # Find permutations with extreme values
        lines.append("\n📈 EXTREME VALUES ANALYSIS")
        lines.append("-" * 60)
        
        # Analyze merge-only extremes
        if merge_only:
            sizes = [(perm, r['file_size']) for perm, r in merge_only.items() if r.get('success')]
            if sizes:
                sizes.sort(key=lambda x: x[1])
                
                smallest = sizes[0]
                largest = sizes[-1]
                
                lines.append(f"\nMerge-only extremes:")
                lines.append(f"  Smallest: Permutation {smallest[0]} - {smallest[1]:,} bytes")
                lines.append(f"    Order: {' → '.join(merge_only[smallest[0]]['order'])}")
                lines.append(f"  Largest: Permutation {largest[0]} - {largest[1]:,} bytes")
                lines.append(f"    Order: {' → '.join(merge_only[largest[0]]['order'])}")
                lines.append(f"  Difference: {largest[1] - smallest[1]:,} bytes ({((largest[1] - smallest[1])/smallest[1])*100:.2f}%)")
        
        # Analyze specific permutation patterns
        lines.append("\n🔄 ORDER PATTERN ANALYSIS")
        lines.append("-" * 60)
        
        # Check if first ontology matters
        first_onto_impact = self.analyze_first_ontology_impact(merge_only)
        lines.append("\nImpact of first ontology:")
        for onto, stats in first_onto_impact.items():
            lines.append(f"  {onto} first: avg size = {stats['avg_size']:,} bytes ({stats['count']} permutations)")
        
        # Check if CHEBI position matters
        chebi_position_impact = self.analyze_position_impact(merge_only, 'chebi.owl')
        lines.append("\nCHEBI position impact:")
        for pos, size in chebi_position_impact.items():
            lines.append(f"  Position {pos}: avg size = {size:,} bytes")
        
        return lines
    
    def analyze_first_ontology_impact(self, results: Dict) -> Dict:
        """Analyze impact of which ontology comes first."""
        first_onto_stats = defaultdict(lambda: {'total_size': 0, 'count': 0})
        
        for perm_id, result in results.items():
            if result.get('success'):
                first = result['order'][0]
                first_onto_stats[first]['total_size'] += result['file_size']
                first_onto_stats[first]['count'] += 1
        
        # Calculate averages
        for onto, stats in first_onto_stats.items():
            stats['avg_size'] = stats['total_size'] // stats['count'] if stats['count'] > 0 else 0
        
        return dict(first_onto_stats)
    
    def analyze_position_impact(self, results: Dict, target_onto: str) -> Dict:
        """Analyze impact of a specific ontology's position."""
        position_sizes = defaultdict(list)
        
        for perm_id, result in results.items():
            if result.get('success'):
                order = result['order']
                if target_onto in order:
                    position = order.index(target_onto) + 1
                    position_sizes[position].append(result['file_size'])
        
        # Calculate averages
        position_avgs = {}
        for pos, sizes in position_sizes.items():
            position_avgs[pos] = sum(sizes) // len(sizes) if sizes else 0
        
        return position_avgs
    
    def save_report(self, report_text: str) -> Path:
        """Save the detailed report."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.results_dir / f'detailed_comparison_{timestamp}.txt'
        
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        return report_file

def main():
    """Generate detailed comparison report."""
    script_dir = Path(__file__).parent
    generator = DetailedReportGenerator(str(script_dir))
    
    try:
        report = generator.generate_detailed_comparison()
        print(report)
        
        report_file = generator.save_report(report)
        print(f"\n📋 Detailed report saved to: {report_file}")
        
        return 0
    except Exception as e:
        print(f"❌ Error generating detailed report: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())