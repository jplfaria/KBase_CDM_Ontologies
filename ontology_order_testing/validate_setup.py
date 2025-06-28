#!/usr/bin/env python3
"""
Validate Setup Before Running Full Test Suite

Ensures all components are working properly.
"""

import os
import sys
import subprocess
from pathlib import Path

# Fix Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_environment():
    """Check basic environment setup."""
    print("🔧 Environment Validation")
    print("=" * 50)
    
    checks = []
    
    # Check Python version
    py_version = sys.version_info
    if py_version.major >= 3 and py_version.minor >= 8:
        checks.append(("Python 3.8+", True, f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
    else:
        checks.append(("Python 3.8+", False, f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
    
    # Check required commands
    commands = {
        'robot': 'ROBOT tool',
        'grep': 'grep command',
        'java': 'Java runtime'
    }
    
    for cmd, name in commands.items():
        try:
            result = subprocess.run(['which', cmd], capture_output=True, text=True)
            if result.returncode == 0:
                checks.append((name, True, "Found"))
            else:
                checks.append((name, False, "Not found"))
        except:
            checks.append((name, False, "Error checking"))
    
    # Check memory settings
    robot_memory = os.environ.get('ROBOT_JAVA_ARGS', 'Not set')
    if 'Xmx' in robot_memory:
        checks.append(("ROBOT memory config", True, robot_memory.split()[0]))
    else:
        checks.append(("ROBOT memory config", False, robot_memory))
    
    return checks

def check_imports():
    """Check all required imports."""
    print("\n📦 Import Validation")
    print("=" * 50)
    
    checks = []
    
    # Standard library imports
    std_modules = [
        'collections', 'json', 'pathlib', 'subprocess',
        'tempfile', 'typing', 'datetime', 'itertools'
    ]
    
    for module in std_modules:
        try:
            __import__(module)
            checks.append((f"import {module}", True, "OK"))
        except Exception as e:
            checks.append((f"import {module}", False, str(e)))
    
    # Test defaultdict specifically
    try:
        from collections import defaultdict
        d = defaultdict(list)
        d['test'].append(1)
        checks.append(("defaultdict usage", True, "Working"))
    except Exception as e:
        checks.append(("defaultdict usage", False, str(e)))
    
    return checks

def check_local_modules():
    """Check local module imports."""
    print("\n🔌 Local Module Validation")
    print("=" * 50)
    
    checks = []
    
    modules = [
        'enhanced_metrics',
        'generate_detailed_report',
        'generate_summary',
        'test_permutations_4onto',
        'enhanced_order_analysis'
    ]
    
    for module in modules:
        try:
            __import__(module)
            checks.append((f"{module}.py", True, "Imports OK"))
        except Exception as e:
            checks.append((f"{module}.py", False, f"Import error: {str(e)[:50]}"))
    
    return checks

def check_file_structure():
    """Check required directories and files."""
    print("\n📁 File Structure Validation")
    print("=" * 50)
    
    checks = []
    
    # Check directories
    dirs = ['scripts', 'data', 'results', 'logs', 'local_env']
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            checks.append((f"{dir_name}/", True, "Exists"))
        else:
            checks.append((f"{dir_name}/", False, "Missing"))
    
    # Check key files
    files = [
        'ontologies_source_full.txt',
        'docker-compose.override.yml',
        'local_env/.env.local'
    ]
    
    for file_name in files:
        file_path = Path(file_name)
        if file_path.exists():
            checks.append((file_name, True, "Exists"))
        else:
            checks.append((file_name, False, "Missing"))
    
    return checks

def print_results(category, checks):
    """Print validation results."""
    all_passed = all(status for _, status, _ in checks)
    
    for name, status, detail in checks:
        icon = "✅" if status else "❌"
        print(f"  {icon} {name:<30} {detail}")
    
    return all_passed

def main():
    """Run all validation checks."""
    print("🚀 Pre-Test Validation Suite")
    print("=" * 60)
    print("Validating setup before running full test suite...")
    print()
    
    all_passed = True
    
    # Run all checks
    env_checks = check_environment()
    all_passed &= print_results("Environment", env_checks)
    
    import_checks = check_imports()
    all_passed &= print_results("Imports", import_checks)
    
    module_checks = check_local_modules()
    all_passed &= print_results("Local Modules", module_checks)
    
    file_checks = check_file_structure()
    all_passed &= print_results("File Structure", file_checks)
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Ready to run tests!")
        print("\nRecommended next steps:")
        print("  1. Run a quick test: ./docker-run.sh test-metrics")
        print("  2. Run full suite: ./docker-run.sh all --nohup")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Please fix issues before running tests")
        print("\nCommon fixes:")
        print("  - Missing directories: Will be created automatically")
        print("  - Import errors: Check Python environment")
        print("  - Missing files: Ensure git pull completed")
        return 1

if __name__ == "__main__":
    sys.exit(main())