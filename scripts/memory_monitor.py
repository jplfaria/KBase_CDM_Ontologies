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
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
        try:
            if proc.info['name'] == 'java':
                cmdline_info = proc.info['cmdline']
                if cmdline_info and isinstance(cmdline_info, (list, tuple)):
                    cmdline = ' '.join(str(arg) for arg in cmdline_info)
                else:
                    cmdline = ''
                memory_mb = proc.info['memory_info'].rss / (1024**2)
                
                process_type = 'unknown'
                if 'robot.jar' in cmdline:
                    process_type = 'ROBOT'
                elif 'relation-graph' in cmdline:
                    process_type = 'relation-graph'
                elif 'semsql' in cmdline:
                    process_type = 'SemanticSQL'
                
                java_processes.append({
                    'pid': proc.info['pid'],
                    'type': process_type,
                    'memory_mb': round(memory_mb, 2),
                    'memory_gb': round(memory_mb / 1024, 2),
                    'cmdline_snippet': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return java_processes

def monitor_tool_execution(tool_name, command, log_dir, interval=15):
    """Monitor memory usage during tool execution."""
    log_file = os.path.join(log_dir, f"{tool_name}_memory_log.json")
    summary_file = os.path.join(log_dir, f"{tool_name}_memory_summary.txt")
    
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
            
            # Calculate total Java memory usage
            total_java_memory = sum(p['memory_gb'] for p in java_procs)
            
            # Track peak memory
            peak_memory = max(peak_memory, mem_info['used_memory_gb'])
            
            # Store data point
            data_point = {
                **mem_info,
                'java_processes': java_procs,
                'total_java_memory_gb': round(total_java_memory, 2),
                'tool_name': tool_name
            }
            memory_data.append(data_point)
            
            # Log current state
            logging.info(f"Memory: {mem_info['used_memory_gb']:.2f}GB used, "
                        f"{mem_info['available_memory_gb']:.2f}GB available, "
                        f"Java: {total_java_memory:.2f}GB")
            
            time.sleep(interval)
        
        # Wait for process completion
        return_code = process.wait()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Save detailed log
        with open(log_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        # Create summary
        final_memory = memory_data[-1] if memory_data else None
        summary = {
            'tool_name': tool_name,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': round(duration, 2),
            'duration_minutes': round(duration / 60, 2),
            'return_code': return_code,
            'peak_memory_gb': round(peak_memory, 2),
            'final_memory_gb': round(final_memory['used_memory_gb'], 2) if final_memory else 0,
            'max_java_memory_gb': round(max(d.get('total_java_memory_gb', 0) for d in memory_data), 2) if memory_data else 0,
            'data_points': len(memory_data)
        }
        
        # Save summary
        with open(summary_file, 'w') as f:
            f.write(f"Memory Usage Summary for {tool_name}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Start Time: {summary['start_time']}\n")
            f.write(f"End Time: {summary['end_time']}\n")
            f.write(f"Duration: {summary['duration_minutes']:.2f} minutes\n")
            f.write(f"Return Code: {summary['return_code']}\n")
            f.write(f"Peak System Memory: {summary['peak_memory_gb']:.2f} GB\n")
            f.write(f"Final System Memory: {summary['final_memory_gb']:.2f} GB\n")
            f.write(f"Max Java Memory: {summary['max_java_memory_gb']:.2f} GB\n")
            f.write(f"Monitoring Data Points: {summary['data_points']}\n")
        
        logging.info(f"Tool {tool_name} completed with return code {return_code}")
        logging.info(f"Peak memory usage: {peak_memory:.2f} GB")
        logging.info(f"Duration: {duration/60:.2f} minutes")
        
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
    interval = int(sys.argv[4]) if len(sys.argv) > 4 else 15
    
    utils_dir = create_utils_directory(repo_path)
    return_code, summary = monitor_tool_execution(tool_name, command, utils_dir, interval)
    
    sys.exit(return_code if return_code is not None else 0)