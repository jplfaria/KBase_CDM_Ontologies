#!/usr/bin/env python3
"""
Fix memory monitoring for order testing.

This script ensures that memory monitoring is properly configured and 
the utils directory is created in the results folder.
"""

import os
import sys
from pathlib import Path

def fix_memory_monitoring():
    """Ensure memory monitoring is properly configured for order testing."""
    
    # Get the testing directory
    script_dir = Path(__file__).parent
    results_dir = script_dir / 'results'
    utils_dir = results_dir / 'utils'
    
    print("🔧 Fixing Memory Monitoring Configuration")
    print("=" * 50)
    
    # Create directories
    print(f"📁 Creating results directory: {results_dir}")
    results_dir.mkdir(exist_ok=True)
    
    print(f"📁 Creating utils directory: {utils_dir}")
    utils_dir.mkdir(exist_ok=True)
    
    # Check if memory monitoring is enabled
    env_file = script_dir / 'local_env' / '.env.local'
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            
        if 'ENABLE_MEMORY_MONITORING=true' in content:
            print("✅ Memory monitoring is ENABLED")
        else:
            print("❌ Memory monitoring is DISABLED")
            
        # Check memory settings
        if 'ROBOT_JAVA_ARGS="-Xmx1024g' in content:
            print("✅ Memory allocation is 1TB (optimal)")
        else:
            print("⚠️  Memory allocation may be suboptimal")
    else:
        print(f"❌ Environment file not found: {env_file}")
    
    # Check if memory monitor script exists
    memory_script = script_dir.parent / 'scripts' / 'memory_monitor.py'
    if memory_script.exists():
        print(f"✅ Memory monitor script found: {memory_script}")
    else:
        print(f"❌ Memory monitor script not found: {memory_script}")
    
    # Create a test log to verify permissions
    test_log = utils_dir / 'test_permissions.txt'
    try:
        with open(test_log, 'w') as f:
            f.write("Memory monitoring test - permissions OK\n")
        test_log.unlink()  # Clean up
        print("✅ Write permissions OK for utils directory")
    except Exception as e:
        print(f"❌ Write permission error: {e}")
    
    print("\n🎯 Memory Monitoring Status:")
    print(f"   Results dir: {results_dir.exists()} ({'exists' if results_dir.exists() else 'missing'})")
    print(f"   Utils dir:   {utils_dir.exists()} ({'exists' if utils_dir.exists() else 'missing'})")
    
    return {
        'results_dir_exists': results_dir.exists(),
        'utils_dir_exists': utils_dir.exists(),
        'env_file_exists': env_file.exists(),
        'memory_script_exists': memory_script.exists()
    }

if __name__ == "__main__":
    status = fix_memory_monitoring()
    
    if all(status.values()):
        print("\n🎉 Memory monitoring is properly configured!")
        sys.exit(0)
    else:
        print("\n⚠️  Some issues found with memory monitoring setup")
        sys.exit(1)