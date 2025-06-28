#!/usr/bin/env python3
"""Test imports and Python environment in Docker."""

import sys
import os

print("🐍 Python Environment Test")
print("=" * 50)
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current directory: {os.getcwd()}")
print(f"Script location: {os.path.abspath(__file__)}")
print()

# Test collections import
print("Testing collections import:")
try:
    from collections import defaultdict, Counter
    print("  ✅ collections.defaultdict: SUCCESS")
    print("  ✅ collections.Counter: SUCCESS")
    
    # Test usage
    d = defaultdict(list)
    d['test'].append(1)
    print(f"  ✅ defaultdict usage: {dict(d)}")
    
    c = Counter(['a', 'b', 'a'])
    print(f"  ✅ Counter usage: {dict(c)}")
except Exception as e:
    print(f"  ❌ collections import error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test other critical imports
print("Testing other imports:")
modules = [
    'json',
    'pathlib',
    'subprocess',
    'tempfile',
    'typing',
    'datetime'
]

for module in modules:
    try:
        __import__(module)
        print(f"  ✅ {module}: SUCCESS")
    except Exception as e:
        print(f"  ❌ {module}: FAILED - {e}")

print()

# Test local module imports
print("Testing local module imports:")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from enhanced_metrics import EnhancedMetricsCollector
    print("  ✅ enhanced_metrics: SUCCESS")
except Exception as e:
    print(f"  ❌ enhanced_metrics: FAILED - {e}")

try:
    from generate_detailed_report import DetailedReportGenerator
    print("  ✅ generate_detailed_report: SUCCESS")
except Exception as e:
    print(f"  ❌ generate_detailed_report: FAILED - {e}")

print()
print("🎉 Import test complete!")