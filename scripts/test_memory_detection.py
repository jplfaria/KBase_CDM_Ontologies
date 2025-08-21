#!/usr/bin/env python3
"""Quick test script to verify memory monitoring is working correctly."""

import subprocess
import time
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_monitor import get_java_processes_memory, get_memory_info


def test_with_simple_java_process():
    """Test memory detection with a simple Java process."""
    print("Testing memory detection with a simple Java process...")
    print("-" * 60)
    
    # Start a simple Java process that just sleeps
    java_code = '''
    public class TestMemory {
        public static void main(String[] args) throws Exception {
            System.out.println("Test Java process started, PID: " + 
                ProcessHandle.current().pid());
            Thread.sleep(10000);  // Sleep for 10 seconds
        }
    }
    '''
    
    # Write the Java file
    with open('/tmp/TestMemory.java', 'w') as f:
        f.write(java_code)
    
    try:
        # Compile the Java file
        print("Compiling test Java program...")
        result = subprocess.run(['javac', '/tmp/TestMemory.java'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to compile: {result.stderr}")
            print("Make sure Java JDK is installed (not just JRE)")
            return False
        
        # Run the Java process in background
        print("Starting test Java process...")
        proc = subprocess.Popen(['java', '-cp', '/tmp', 'TestMemory'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give it time to start
        time.sleep(2)
        
        # Now test detection
        print("\nTesting Java process detection...")
        java_procs = get_java_processes_memory()
        
        print(f"Found {len(java_procs)} Java processes:")
        for p in java_procs:
            print(f"  PID: {p['pid']}, Type: {p['type']}, "
                  f"Memory: {p['memory_gb']:.3f}GB, User: {p['username']}")
            print(f"    Cmdline: {p['cmdline_snippet']}")
        
        # Kill the test process
        proc.terminate()
        proc.wait()
        
        return len(java_procs) > 0
        
    except FileNotFoundError:
        print("ERROR: Java not found. Make sure Java is installed and in PATH")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        # Cleanup
        for f in ['/tmp/TestMemory.java', '/tmp/TestMemory.class']:
            if os.path.exists(f):
                os.remove(f)


def test_current_system():
    """Test current system for Java processes."""
    print("\nChecking current system for Java processes...")
    print("-" * 60)
    
    # Get system info
    mem_info = get_memory_info()
    print(f"System Memory: {mem_info['total_memory_gb']:.1f}GB total, "
          f"{mem_info['available_memory_gb']:.1f}GB available")
    print(f"Current user: {os.environ.get('USER', 'unknown')}")
    
    # Get Java processes
    java_procs = get_java_processes_memory()
    
    if not java_procs:
        print("\nNo Java processes detected!")
        print("\nTrying alternative detection methods...")
        
        # Try to find any java-like processes
        import psutil
        found_any = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info.get('name', '').lower()
                cmdline = ' '.join(proc.info.get('cmdline', []))
                
                if any(pattern in name + cmdline.lower() for pattern in 
                       ['java', 'robot', 'semsql', 'jdk', 'jre']):
                    if not found_any:
                        print("\nFound potentially related processes:")
                        found_any = True
                    print(f"  PID: {proc.info['pid']}, Name: {proc.info['name']}")
                    print(f"    Cmdline: {cmdline[:100]}...")
            except:
                pass
        
        if not found_any:
            print("No Java-related processes found at all.")
    else:
        print(f"\nFound {len(java_procs)} Java processes:")
        
        # Group by type
        by_type = {}
        for p in java_procs:
            ptype = p['type']
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(p)
        
        # Display by type
        for ptype, procs in by_type.items():
            print(f"\n{ptype} processes ({len(procs)}):")
            for p in procs:
                print(f"  PID: {p['pid']}, Memory: {p['memory_gb']:.2f}GB, "
                      f"User: {p['username']}")
                if p['cmdline_snippet']:
                    print(f"    {p['cmdline_snippet']}")


def main():
    """Main test function."""
    print("CDM Ontologies Memory Monitor Test")
    print("=" * 60)
    
    # Test 1: Check current system
    test_current_system()
    
    # Test 2: Create a test Java process (if requested)
    if '--with-test' in sys.argv:
        print("\n" + "=" * 60)
        success = test_with_simple_java_process()
        if success:
            print("\n✅ Memory detection is working correctly!")
        else:
            print("\n❌ Memory detection failed. Check the output above for details.")
    else:
        print("\nTo test with a simple Java process, run:")
        print(f"  python {sys.argv[0]} --with-test")
    
    # Save debug info if requested
    if '--save-debug' in sys.argv:
        output_file = 'memory_debug_info.json'
        print(f"\nSaving debug information to {output_file}...")
        from debug_memory_monitor import save_debug_info
        save_debug_info(output_file)


if __name__ == "__main__":
    main()