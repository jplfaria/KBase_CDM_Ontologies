#!/usr/bin/env python3
"""Quick environment check for Java processes without psutil dependency."""

import subprocess
import os
import sys

def check_java_processes():
    """Check for Java processes using ps command."""
    print("CDM Ontologies Java Process Environment Check")
    print("=" * 60)
    
    # Check current user
    print(f"Current user: {os.environ.get('USER', 'unknown')}")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    # Check if we're in Docker
    if os.path.exists('/.dockerenv'):
        print("Running in Docker container: YES")
    else:
        print("Running in Docker container: NO")
    
    print("\n" + "-" * 60)
    print("Checking for Java processes using 'ps'...")
    print("-" * 60)
    
    try:
        # Try different ps commands
        commands = [
            ("ps aux | grep -i java | grep -v grep", "Standard ps aux"),
            ("ps -ef | grep -i java | grep -v grep", "System V style ps"),
            ("pgrep -la java", "pgrep for java processes"),
        ]
        
        found_any = False
        for cmd, desc in commands:
            print(f"\n{desc} ({cmd}):")
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    print(result.stdout)
                    found_any = True
                else:
                    print("  No Java processes found with this command")
            except Exception as e:
                print(f"  Error: {e}")
        
        if not found_any:
            print("\n⚠️  No Java processes found. This is normal if no Java tools are running.")
            print("\nTo test with a Java process, you could:")
            print("1. Start the CDM pipeline in another terminal")
            print("2. Or run a simple Java command like: java -version")
        
    except Exception as e:
        print(f"Error checking processes: {e}")
    
    # Check Java installation
    print("\n" + "-" * 60)
    print("Checking Java installation...")
    print("-" * 60)
    
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        print("Java is installed:")
        print(result.stderr if result.stderr else result.stdout)
    except FileNotFoundError:
        print("❌ Java not found in PATH")
    
    # Check for psutil
    print("\n" + "-" * 60)
    print("Checking Python package requirements...")
    print("-" * 60)
    
    try:
        import psutil
        print("✅ psutil is installed (version: {})".format(psutil.__version__))
    except ImportError:
        print("❌ psutil is NOT installed")
        print("\nTo install psutil, run one of:")
        print("  pip install psutil")
        print("  pip3 install psutil")
        print("  python -m pip install psutil")
        print("  conda install psutil  (if using conda)")
        
        # Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("\n⚠️  You appear to be in a virtual environment.")
            print("Make sure to install psutil in this environment.")

if __name__ == "__main__":
    check_java_processes()