#!/usr/bin/env python3
"""Memory monitoring utility for CDM Ontologies Pipeline tools."""

import os
import sys
import time
import subprocess
import psutil
import json
from datetime import datetime
from pathlib import Path
import logging

def setup_logging(log_file):
    """Set up logging for memory monitoring."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_memory_info():
    """Get current system memory information."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        'timestamp': datetime.now().isoformat(),
        'total_memory_gb': round(memory.total / (1024**3), 2),
        'available_memory_gb': round(memory.available / (1024**3), 2),
        'used_memory_gb': round(memory.used / (1024**3), 2),
        'memory_percent': memory.percent,
        'swap_total_gb': round(swap.total / (1024**3), 2),
        'swap_used_gb': round(swap.used / (1024**3), 2),
        'swap_percent': swap.percent
    }

def get_java_processes_memory():
    """Get memory usage of Java processes (ROBOT, relation-graph)."""
    java_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'username']):
        try:
            if proc.info['name'] == 'java':
                # Handle case where cmdline might be None
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                memory_mb = proc.info['memory_info'].rss / (1024**2)
                username = proc.info.get('username', 'unknown')
                
                process_type = 'unknown'
                if 'robot.jar' in cmdline:
                    process_type = 'ROBOT'
                elif 'relation-graph' in cmdline:
                    process_type = 'relation-graph'
                elif 'semsql' in cmdline or 'semantic' in cmdline:
                    process_type = 'SemanticSQL'
                elif any(x in cmdline for x in ['CDM_merged', 'ontolog']):
                    process_type = 'ROBOT'  # Likely ROBOT working on ontologies
                
                java_processes.append({
                    'pid': proc.info['pid'],
                    'type': process_type,
                    'memory_mb': round(memory_mb, 2),
                    'memory_gb': round(memory_mb / 1024, 2),
                    'username': username,
                    'cmdline_snippet': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return java_processes

def monitor_tool_execution(tool_name, command, log_dir, interval=60):
    """Monitor memory usage during tool execution."""
    log_file = os.path.join(log_dir, f"{tool_name}_memory_log.json")
    summary_file = os.path.join(log_dir, f"{tool_name}_memory_summary.txt")
    
    # Import run summary here to avoid circular import
    from run_summary import get_summary
    
    # Get current user for process filtering
    current_user = os.environ.get('USER', 'unknown')
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    setup_logging(os.path.join(log_dir, f"{tool_name}_monitor.log"))
    logging.info(f"Starting memory monitoring for {tool_name}")
    logging.info(f"Command: {command}")
    
    # Start the tool process
    process = subprocess.Popen(command, shell=True)
    
    memory_data = []
    peak_memory = 0
    start_time = datetime.now()
    
    try:
        while process.poll() is None:
            # Get system memory info
            mem_info = get_memory_info()
            
            # Get Java processes memory
            java_procs = get_java_processes_memory()
            
            # Filter for current user's processes
            user_java_procs = [p for p in java_procs if p.get('username') == current_user]
            other_java_procs = [p for p in java_procs if p.get('username') != current_user]
            
            # Calculate memory usage
            user_java_memory = sum(p['memory_gb'] for p in user_java_procs)
            other_java_memory = sum(p['memory_gb'] for p in other_java_procs)
            total_java_memory = user_java_memory + other_java_memory
            
            # Find the main task process (largest memory user for current user)
            task_process = max(user_java_procs, key=lambda p: p['memory_gb']) if user_java_procs else None
            task_memory = task_process['memory_gb'] if task_process else 0
            
            # Track peak memory
            peak_memory = max(peak_memory, task_memory)
            
            # Store data point
            data_point = {
                **mem_info,
                'java_processes': java_procs,
                'user_java_processes': user_java_procs,
                'other_java_processes': other_java_procs,
                'user_java_memory_gb': round(user_java_memory, 2),
                'other_java_memory_gb': round(other_java_memory, 2),
                'total_java_memory_gb': round(total_java_memory, 2),
                'task_memory_gb': round(task_memory, 2),
                'tool_name': tool_name
            }
            memory_data.append(data_point)
            
            # Log only significant changes or every 10 minutes
            current_time = datetime.now()
            time_since_start = (current_time - start_time).total_seconds()
            
            # Log every 10 minutes or when memory changes significantly (>5GB)
            should_log = (len(memory_data) == 1 or  # First data point
                         time_since_start % 600 < interval or  # Every 10 minutes
                         abs(task_memory - memory_data[-2].get('task_memory_gb', 0)) > 5.0 if len(memory_data) > 1 else False)  # Significant change
            
            if should_log:
                system_percent = round(mem_info['memory_percent'], 1)
                task_percent = round((task_memory / mem_info['total_memory_gb']) * 100, 1) if mem_info['total_memory_gb'] > 0 else 0
                
                logging.info(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] {tool_name}: "
                            f"Task={task_memory:.1f}GB ({task_percent:.1f}%), "
                            f"System={mem_info['used_memory_gb']:.1f}GB ({system_percent}%), "
                            f"Available={mem_info['available_memory_gb']:.1f}GB")
                
                # Update run summary with memory usage
                summary = get_summary()
                if summary:
                    summary.update_memory_usage(task_memory, task_percent)
            
            time.sleep(interval)
        
        # Wait for process completion
        return_code = process.wait()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Save detailed log
        with open(log_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        # Create enhanced summary
        final_memory = memory_data[-1] if memory_data else None
        
        # Calculate peak values
        peak_task_memory = max(d.get('task_memory_gb', 0) for d in memory_data) if memory_data else 0
        peak_system_memory = max(d.get('used_memory_gb', 0) for d in memory_data) if memory_data else 0
        peak_user_java_memory = max(d.get('user_java_memory_gb', 0) for d in memory_data) if memory_data else 0
        
        # Get system info
        total_system_memory = memory_data[0]['total_memory_gb'] if memory_data else 0
        
        summary = {
            'tool_name': tool_name,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': round(duration, 2),
            'duration_minutes': round(duration / 60, 2),
            'return_code': return_code,
            'peak_task_memory_gb': round(peak_task_memory, 2),
            'peak_task_memory_percent': round((peak_task_memory / total_system_memory) * 100, 1) if total_system_memory > 0 else 0,
            'peak_system_memory_gb': round(peak_system_memory, 2),
            'peak_user_java_memory_gb': round(peak_user_java_memory, 2),
            'final_task_memory_gb': round(final_memory.get('task_memory_gb', 0), 2) if final_memory else 0,
            'final_system_memory_gb': round(final_memory['used_memory_gb'], 2) if final_memory else 0,
            'total_system_memory_gb': round(total_system_memory, 2),
            'data_points': len(memory_data),
            'success': return_code == 0
        }
        
        # Save enhanced summary
        with open(summary_file, 'w') as f:
            f.write(f"Memory Usage Summary for {tool_name}\n")
            f.write("=" * 70 + "\n\n")
            
            # Task Information
            f.write("TASK INFORMATION\n")
            f.write("-" * 70 + "\n")
            f.write(f"Tool Name: {tool_name}\n")
            f.write(f"Start Time: {summary['start_time']}\n")
            f.write(f"End Time: {summary['end_time']}\n")
            f.write(f"Duration: {summary['duration_minutes']:.2f} minutes\n")
            f.write(f"Status: {'SUCCESS' if summary['success'] else 'FAILED'} (Return Code: {summary['return_code']})\n")
            f.write("\n")
            
            # Memory Usage Summary
            f.write("MEMORY USAGE SUMMARY\n")
            f.write("-" * 70 + "\n")
            f.write(f"System Total Memory: {summary['total_system_memory_gb']:.2f} GB\n")
            f.write("\n")
            
            # Peak Memory Usage
            f.write("Peak Memory Usage:\n")
            f.write(f"  - Task Process: {summary['peak_task_memory_gb']:.2f} GB "
                   f"({summary['peak_task_memory_percent']:.1f}% of system)\n")
            f.write(f"  - All User Java: {summary['peak_user_java_memory_gb']:.2f} GB\n")
            f.write(f"  - Total System: {summary['peak_system_memory_gb']:.2f} GB\n")
            f.write("\n")
            
            # Final Memory Usage
            f.write("Final Memory Usage:\n")
            f.write(f"  - Task Process: {summary['final_task_memory_gb']:.2f} GB\n")
            f.write(f"  - Total System: {summary['final_system_memory_gb']:.2f} GB\n")
            f.write("\n")
            
            # Monitoring Details
            f.write("MONITORING DETAILS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Data Points Collected: {summary['data_points']}\n")
            f.write(f"Monitoring Interval: {interval} seconds\n")
            f.write(f"\nDetailed logs saved to: {os.path.basename(log_file)}\n")
        
        logging.info(f"\nTool {tool_name} completed with return code {return_code}")
        logging.info(f"Peak memory usage: {peak_task_memory:.2f} GB ({summary['peak_task_memory_percent']:.1f}% of system)")
        logging.info(f"Duration: {duration/60:.2f} minutes")
        
        # Update run summary with final peak memory
        run_summary = get_summary()
        if run_summary:
            run_summary.update_memory_usage(peak_task_memory, summary['peak_task_memory_percent'])
        
        return return_code, summary
        
    except KeyboardInterrupt:
        logging.warning(f"Monitoring interrupted for {tool_name}")
        process.terminate()
        return -1, None

def create_utils_directory(repo_path):
    """Create utils directory structure for memory logs."""
    from enhanced_download import get_output_directories, is_test_mode
    
    test_mode = is_test_mode()
    _, _, outputs_path, _ = get_output_directories(repo_path, test_mode)
    
    utils_dir = os.path.join(outputs_path, "utils")
    os.makedirs(utils_dir, exist_ok=True)
    
    return utils_dir

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python memory_monitor.py <tool_name> <command> <repo_path> [interval]")
        sys.exit(1)
    
    tool_name = sys.argv[1]
    command = sys.argv[2]
    repo_path = sys.argv[3]
    interval = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    
    utils_dir = create_utils_directory(repo_path)
    return_code, summary = monitor_tool_execution(tool_name, command, utils_dir, interval)
    
    sys.exit(return_code if return_code is not None else 0)