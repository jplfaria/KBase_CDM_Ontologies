#!/usr/bin/env python3
"""
Generate Summary Report for Order Testing

This script creates a readable summary report from both the enhanced analysis
(24 ontologies) and permutation testing (4 ontologies) results.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

class OrderTestingSummaryGenerator:
    def __init__(self, testing_dir: str):
        self.testing_dir = Path(testing_dir)
        self.results_dir = self.testing_dir / 'results'
        
    def load_results(self) -> Dict:
        """Load all available test results."""
        results = {}
        
        # Load enhanced analysis results (24 ontologies)
        enhanced_file = self.results_dir / 'enhanced_analysis_results.json'
        if enhanced_file.exists():
            with open(enhanced_file, 'r') as f:
                results['enhanced_analysis'] = json.load(f)
            print(f"✅ Loaded enhanced analysis: {enhanced_file}")
        else:
            print(f"❌ Enhanced analysis not found: {enhanced_file}")
        
        # Load permutation test results (4 ontologies)
        perm_file = self.results_dir / 'permutation_test_results.json'
        if perm_file.exists():
            with open(perm_file, 'r') as f:
                results['permutation_tests'] = json.load(f)
            print(f"✅ Loaded permutation tests: {perm_file}")
        else:
            print(f"❌ Permutation tests not found: {perm_file}")
        
        return results
    
    def generate_enhanced_summary(self, enhanced_data: Dict) -> List[str]:
        """Generate summary for enhanced analysis (24 ontologies)."""
        lines = []
        lines.append("=" * 70)
        lines.append("📊 ENHANCED ANALYSIS SUMMARY (24 ONTOLOGIES)")
        lines.append("=" * 70)
        
        if 'results' not in enhanced_data:
            lines.append("❌ No enhanced analysis results found")
            return lines
        
        results = enhanced_data['results']
        analysis = enhanced_data.get('analysis', {})
        
        # Test execution summary
        lines.append("\n🚀 Test Execution Summary:")
        orders_tested = list(results.keys())
        lines.append(f"   Orders tested: {', '.join(orders_tested)}")
        
        # Results for each order
        for order in orders_tested:
            order_data = results[order]
            lines.append(f"\n📋 {order.upper()} Order Results:")
            
            # Merge-only results
            merge_only = order_data.get('merge_only', {})
            if merge_only.get('success'):
                lines.append(f"   ✅ Merge-only: {merge_only['file_size']:,} bytes, {merge_only['axiom_count']} axioms")
            else:
                lines.append(f"   ❌ Merge-only: Failed")
            
            # With removes results
            with_removes = order_data.get('with_removes', {})
            if with_removes.get('success'):
                lines.append(f"   ✅ With removes: {with_removes['file_size']:,} bytes, {with_removes['axiom_count']} axioms")
            else:
                lines.append(f"   ❌ With removes: Failed")
        
        # Analysis summary
        if analysis and 'summary' in analysis:
            summary = analysis['summary']
            lines.append(f"\n🔍 Analysis Results:")
            lines.append(f"   Terms with different definers: {summary.get('terms_with_different_definers', 0)}")
            lines.append(f"   Tests with differences: {summary.get('tests_with_differences', 0)}")
            lines.append(f"   Remove operations impact: {summary.get('remove_operations_impact', False)}")
            
            # Key findings
            findings = summary.get('key_findings', [])
            if findings:
                lines.append(f"\n🎯 Key Findings:")
                for finding in findings:
                    lines.append(f"   • {finding}")
        
        # Term attribution analysis
        if 'key_term_attribution_differences' in analysis:
            term_analysis = analysis['key_term_attribution_differences']
            terms_with_diffs = [t for t in term_analysis.values() if t.get('has_differences', False)]
            
            if terms_with_diffs:
                lines.append(f"\n🏷️  Terms with Order-Dependent Attribution ({len(terms_with_diffs)}):")
                for term in terms_with_diffs[:10]:  # Show first 10
                    label = term.get('label', 'unknown')
                    category = term.get('category', 'unknown')
                    definers = term.get('unique_definers', [])
                    lines.append(f"   • {label} ({category}): {len(definers)} different definers")
                
                if len(terms_with_diffs) > 10:
                    lines.append(f"   ... and {len(terms_with_diffs) - 10} more")
        
        return lines
    
    def generate_permutation_summary(self, perm_data: Dict) -> List[str]:
        """Generate summary for permutation tests (4 ontologies)."""
        lines = []
        lines.append("=" * 70)
        lines.append("🧪 PERMUTATION TEST SUMMARY (4 ONTOLOGIES)")
        lines.append("=" * 70)
        
        if 'metadata' not in perm_data:
            lines.append("❌ No permutation test results found")
            return lines
        
        metadata = perm_data['metadata']
        analysis = perm_data.get('analysis', {})
        
        # Test overview
        lines.append(f"\n📊 Test Overview:")
        lines.append(f"   Ontologies tested: {', '.join(metadata['test_ontologies'])}")
        lines.append(f"   Total permutations: {metadata['total_permutations']}")
        lines.append(f"   Key CHEBI terms tracked: {len(metadata['key_terms_tested'])}")
        
        # Success rates
        merge_results = perm_data.get('merge_only', {})
        remove_results = perm_data.get('with_removes', {})
        
        successful_merge = sum(1 for r in merge_results.values() if r.get('success', False))
        successful_remove = sum(1 for r in remove_results.values() if r.get('success', False))
        
        lines.append(f"\n✅ Success Rates:")
        lines.append(f"   Merge-only: {successful_merge}/24 ({successful_merge/24*100:.1f}%)")
        lines.append(f"   With removes: {successful_remove}/24 ({successful_remove/24*100:.1f}%)")
        
        # Analysis summary
        if 'summary' in analysis:
            summary = analysis['summary']
            lines.append(f"\n🔍 Analysis Results:")
            lines.append(f"   Terms with order-dependent attribution: {summary.get('terms_with_order_dependent_attribution', 0)}")
            lines.append(f"   Merge-only has variations: {summary.get('merge_only_has_variations', False)}")
            lines.append(f"   With-removes has variations: {summary.get('with_removes_has_variations', False)}")
            lines.append(f"   Remove operations vary by order: {summary.get('remove_operations_vary_by_order', False)}")
            
            # Key findings
            findings = summary.get('key_findings', [])
            if findings:
                lines.append(f"\n🎯 Key Findings:")
                for finding in findings:
                    lines.append(f"   • {finding}")
        
        # Detailed term attribution analysis
        if 'term_attribution_analysis' in analysis:
            term_analysis = analysis['term_attribution_analysis']
            varying_terms = {k: v for k, v in term_analysis.items() if v.get('varies_with_order', False)}
            
            if varying_terms:
                lines.append(f"\n🏷️  Terms with Order-Dependent Attribution:")
                for term_id, term_data in varying_terms.items():
                    label = term_data.get('label', 'unknown')
                    merge_definers = term_data.get('unique_definers_merge', [])
                    remove_definers = term_data.get('unique_definers_removes', [])
                    
                    lines.append(f"   • {term_id} ({label}):")
                    lines.append(f"     Merge-only definers: {len(merge_definers)} unique")
                    lines.append(f"     With-removes definers: {len(remove_definers)} unique")
        
        # File size and axiom count variations
        if successful_merge > 0:
            merge_file_sizes = [r['file_size'] for r in merge_results.values() if r.get('success')]
            merge_axiom_counts = [r['axiom_count'] for r in merge_results.values() if r.get('success')]
            
            lines.append(f"\n📏 Merge-Only Variations:")
            lines.append(f"   File size range: {min(merge_file_sizes):,} - {max(merge_file_sizes):,} bytes")
            lines.append(f"   Axiom count range: {min(merge_axiom_counts):,} - {max(merge_axiom_counts):,}")
            lines.append(f"   File size variation: {len(set(merge_file_sizes))} unique values")
            lines.append(f"   Axiom count variation: {len(set(merge_axiom_counts))} unique values")
        
        if successful_remove > 0:
            remove_file_sizes = [r['file_size'] for r in remove_results.values() if r.get('success')]
            remove_axiom_counts = [r['axiom_count'] for r in remove_results.values() if r.get('success')]
            
            lines.append(f"\n📏 With-Removes Variations:")
            lines.append(f"   File size range: {min(remove_file_sizes):,} - {max(remove_file_sizes):,} bytes")
            lines.append(f"   Axiom count range: {min(remove_axiom_counts):,} - {max(remove_axiom_counts):,}")
            lines.append(f"   File size variation: {len(set(remove_file_sizes))} unique values")
            lines.append(f"   Axiom count variation: {len(set(remove_axiom_counts))} unique values")
        
        return lines
    
    def generate_comparative_analysis(self, enhanced_data: Dict, perm_data: Dict) -> List[str]:
        """Generate comparative analysis between the two test types."""
        lines = []
        lines.append("=" * 70)
        lines.append("🔬 COMPARATIVE ANALYSIS")
        lines.append("=" * 70)
        
        # Test scope comparison
        lines.append(f"\n📊 Test Scope Comparison:")
        lines.append(f"   Enhanced Analysis: 24 ontologies, 3 orders, 6 total tests")
        lines.append(f"   Permutation Tests: 4 ontologies, 24 orders, 48 total tests")
        
        # Extract findings from both tests
        enhanced_findings = []
        perm_findings = []
        
        if enhanced_data and 'analysis' in enhanced_data and 'summary' in enhanced_data['analysis']:
            enhanced_findings = enhanced_data['analysis']['summary'].get('key_findings', [])
        
        if perm_data and 'analysis' in perm_data and 'summary' in perm_data['analysis']:
            perm_findings = perm_data['analysis']['summary'].get('key_findings', [])
        
        # Consistency check
        lines.append(f"\n🎯 Consistency Analysis:")
        
        # Check if both tests show order effects
        enhanced_has_differences = any('order affects' in f.lower() or 'differences' in f.lower() for f in enhanced_findings)
        perm_has_differences = any('order affects' in f.lower() or 'differences' in f.lower() for f in perm_findings)
        
        if enhanced_has_differences and perm_has_differences:
            lines.append(f"   ✅ Both tests confirm merge order affects results")
        elif not enhanced_has_differences and not perm_has_differences:
            lines.append(f"   ✅ Both tests show consistent results regardless of order")
        else:
            lines.append(f"   ⚠️  Tests show conflicting results about order effects")
        
        # Check remove operation effects
        enhanced_remove_impact = any('remove' in f.lower() for f in enhanced_findings)
        perm_remove_impact = any('remove' in f.lower() for f in perm_findings)
        
        if enhanced_remove_impact or perm_remove_impact:
            lines.append(f"   📝 Remove operations show order-dependent behavior")
        else:
            lines.append(f"   📝 Remove operations appear consistent across orders")
        
        # Recommendations
        lines.append(f"\n💡 Recommendations:")
        
        if enhanced_has_differences or perm_has_differences:
            lines.append(f"   • Order matters: Use consistent merge order in production")
            lines.append(f"   • Consider hierarchy-based ordering for stable results")
            lines.append(f"   • Document chosen order in pipeline configuration")
        else:
            lines.append(f"   • Order appears stable: Current ordering strategy is adequate")
            lines.append(f"   • No immediate action required for merge order")
        
        if enhanced_remove_impact or perm_remove_impact:
            lines.append(f"   • Remove operations amplify order effects")
            lines.append(f"   • Test remove operations with production data")
        
        return lines
    
    def generate_full_report(self) -> str:
        """Generate complete summary report."""
        print("📋 Generating Order Testing Summary Report...")
        
        # Load all results
        all_results = self.load_results()
        
        report_lines = []
        report_lines.append("ONTOLOGY ORDER TESTING - COMPREHENSIVE SUMMARY REPORT")
        report_lines.append("=" * 70)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Testing Directory: {self.testing_dir}")
        
        # Enhanced analysis summary
        if 'enhanced_analysis' in all_results:
            enhanced_summary = self.generate_enhanced_summary(all_results['enhanced_analysis'])
            report_lines.extend(enhanced_summary)
        
        # Permutation test summary
        if 'permutation_tests' in all_results:
            perm_summary = self.generate_permutation_summary(all_results['permutation_tests'])
            report_lines.extend(perm_summary)
        
        # Comparative analysis
        if 'enhanced_analysis' in all_results and 'permutation_tests' in all_results:
            comparative = self.generate_comparative_analysis(
                all_results['enhanced_analysis'], 
                all_results['permutation_tests']
            )
            report_lines.extend(comparative)
        
        # Footer
        report_lines.append("\n" + "=" * 70)
        report_lines.append("🏁 END OF REPORT")
        report_lines.append("=" * 70)
        
        return '\n'.join(report_lines)
    
    def save_report(self, report_text: str) -> Path:
        """Save the report to a file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.results_dir / f'order_testing_summary_{timestamp}.txt'
        
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        return report_file

def main():
    """Main function for summary generation."""
    # Get the testing directory
    script_dir = Path(__file__).parent
    
    generator = OrderTestingSummaryGenerator(str(script_dir))
    
    try:
        # Generate and display report
        report = generator.generate_full_report()
        print("\n" + report)
        
        # Save report
        report_file = generator.save_report(report)
        print(f"\n📋 Summary report saved to: {report_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error generating summary: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())