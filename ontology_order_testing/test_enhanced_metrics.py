#!/usr/bin/env python3
"""
Test Enhanced Metrics Functionality

Validates that the enhanced metrics collector works correctly with robust fallbacks.
"""

import os
import sys
from pathlib import Path

# Import enhanced metrics
sys.path.insert(0, os.path.dirname(__file__))
from enhanced_metrics import EnhancedMetricsCollector

def test_metrics_on_available_files():
    """Test enhanced metrics on available ontology files."""
    
    testing_dir = Path(__file__).parent
    data_dir = testing_dir / 'data'
    
    print("🧪 Testing Enhanced Metrics Collector")
    print("=" * 50)
    
    # Initialize collector
    collector = EnhancedMetricsCollector()
    
    # Find available ontology files
    owl_files = []
    if data_dir.exists():
        owl_files = list(data_dir.glob("*.owl"))
    
    if not owl_files:
        print("❌ No OWL files found in data/ directory")
        print("📁 Data directory exists:", data_dir.exists())
        if data_dir.exists():
            all_files = list(data_dir.iterdir())
            print(f"📋 Files in data/: {[f.name for f in all_files[:10]]}")
        return False
    
    print(f"✅ Found {len(owl_files)} OWL files")
    
    # Test on a few representative files
    test_files = owl_files[:3]  # Test first 3 files
    
    for owl_file in test_files:
        print(f"\n🔬 Testing: {owl_file.name}")
        print(f"   File size: {owl_file.stat().st_size / (1024*1024):.1f} MB")
        
        try:
            # Test collection
            metrics = collector.collect_all_metrics(owl_file)
            
            # Validate results
            basic_counts = metrics.get('basic_counts', {})
            file_size = metrics.get('file_size', 0)
            collection_time = metrics.get('collection_time', 0)
            
            print(f"   ✅ Collection completed in {collection_time:.1f}s")
            print(f"   📊 Method used: {basic_counts.get('analysis_method', 'unknown')}")
            
            # Show key metrics
            axioms = basic_counts.get('total_axioms', 0)
            classes = basic_counts.get('total_classes', 0)
            
            if axioms > 0:
                print(f"   📈 Axioms: {axioms:,}")
            if classes > 0:
                print(f"   🏷️  Classes: {classes:,}")
            
            # Check for annotation data
            annotation_props = metrics.get('annotation_properties', {})
            if annotation_props:
                defined_terms = annotation_props.get('total_defined_terms', 0)
                if defined_terms > 0:
                    print(f"   🔗 Defined terms: {defined_terms:,}")
            
            # Validate that we got meaningful results
            if axioms == 0 and classes == 0:
                print("   ⚠️  Warning: Zero counts detected - may indicate analysis issues")
            else:
                print("   ✅ Meaningful results obtained")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return False
    
    print("\n🎉 Enhanced metrics testing completed successfully!")
    return True

def main():
    """Main test function."""
    success = test_metrics_on_available_files()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())