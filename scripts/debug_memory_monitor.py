#!/usr/bin/env python3
"""Debug script to diagnose memory monitoring issues."""

import psutil
import os
import sys
import json
from datetime import datetime

def get_all_processes_info():
    """Get detailed info about all processes to debug memory monitoring."""
    processes = []
    current_user = os.environ.get('USER', 'unknown')
    
    print(f"Current user: {current_user}")
    print(f"Current PID: {os.getpid()}")
    print("-" * 80)
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'username', 'exe']):
        try:
            info = proc.info
            
            # Skip kernel processes
            if not info.get('cmdline'):
                continue
                
            memory_mb = info['memory_info'].rss / (1024**2) if info.get('memory_info') else 0
            
            # Check if it's a Java-related process
            name = info.get('name', '').lower()
            cmdline = ' '.join(info.get('cmdline', []))
            exe = info.get('exe', '')
            
            # Look for Java processes with various patterns
            is_java = False
            java_type = None
            
            # Check by process name
            if 'java' in name:
                is_java = True
                java_type = "name='java'"
            
            # Check by executable path
            elif exe and ('java' in exe.lower() or 'jdk' in exe.lower() or 'jre' in exe.lower()):
                is_java = True
                java_type = f"exe contains java: {exe}"
            
            # Check by command line
            elif any(pattern in cmdline.lower() for pattern in ['java ', 'java.exe', '/bin/java', 'robot.jar', 'semsql', 'relation-graph']):
                is_java = True
                java_type = "cmdline contains java patterns"
            
            if is_java or memory_mb > 100:  # Also show large processes
                process_info = {
                    'pid': info['pid'],
                    'name': name,
                    'username': info.get('username', 'unknown'),
                    'memory_mb': round(memory_mb, 2),
                    'memory_gb': round(memory_mb / 1024, 2),
                    'is_java': is_java,
                    'java_type': java_type,
                    'exe': exe,
                    'cmdline': cmdline[:200] + '...' if len(cmdline) > 200 else cmdline
                }
                
                processes.append(process_info)
                
                # Print Java processes or large memory users
                if is_java:
                    print(f"\n🔵 JAVA PROCESS FOUND:")
                elif memory_mb > 1000:
                    print(f"\n🟡 LARGE PROCESS:")
                else:
                    continue
                    
                print(f"  PID: {process_info['pid']}")
                print(f"  Name: {process_info['name']}")
                print(f"  User: {process_info['username']}")
                print(f"  Memory: {process_info['memory_gb']:.2f} GB")
                if is_java:
                    print(f"  Java Detection: {java_type}")
                print(f"  Exe: {process_info['exe']}")
                print(f"  Cmdline: {process_info['cmdline']}")
                
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            continue
        except Exception as e:
            print(f"Error processing PID {proc.pid}: {e}")
    
    return processes

def test_java_detection():
    """Test different methods of detecting Java processes."""
    print("\n" + "=" * 80)
    print("TESTING JAVA PROCESS DETECTION")
    print("=" * 80)
    
    # Method 1: By process name
    java_by_name = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == 'java':
                java_by_name.append(proc.info['pid'])
        except:
            pass
    print(f"\nMethod 1 - Processes with name='java': {len(java_by_name)} found")
    if java_by_name:
        print(f"  PIDs: {java_by_name[:5]}...")
    
    # Method 2: By name containing 'java'
    java_by_name_contains = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'java' in proc.info['name'].lower():
                java_by_name_contains.append((proc.info['pid'], proc.info['name']))
        except:
            pass
    print(f"\nMethod 2 - Processes with 'java' in name: {len(java_by_name_contains)} found")
    if java_by_name_contains:
        for pid, name in java_by_name_contains[:5]:
            print(f"  PID {pid}: {name}")
    
    # Method 3: By cmdline
    java_by_cmdline = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('java' in str(arg).lower() for arg in cmdline):
                java_by_cmdline.append((proc.info['pid'], proc.info['name']))
        except:
            pass
    print(f"\nMethod 3 - Processes with 'java' in cmdline: {len(java_by_cmdline)} found")
    if java_by_cmdline:
        for pid, name in java_by_cmdline[:5]:
            print(f"  PID {pid}: {name}")

def save_debug_info(output_file):
    """Save debug information to a file."""
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'platform': sys.platform,
        'user': os.environ.get('USER', 'unknown'),
        'processes': get_all_processes_info()
    }
    
    with open(output_file, 'w') as f:
        json.dump(debug_info, f, indent=2)
    
    print(f"\n\nDebug information saved to: {output_file}")

if __name__ == "__main__":
    print("CDM Ontologies Memory Monitor Debug Tool")
    print("=" * 80)
    
    # Get all process info
    processes = get_all_processes_info()
    
    # Test Java detection methods
    test_java_detection()
    
    # Save to file if requested
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
        save_debug_info(output_file)
    
    print("\n" + "=" * 80)
    print("Debug complete. If no Java processes were found, check:")
    print("1. Are Java processes running? Try: ps aux | grep java")
    print("2. Is this running in a Docker container? Process names may differ")
    print("3. Check process permissions - some processes may not be accessible")