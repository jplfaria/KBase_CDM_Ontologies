#!/usr/bin/env python3
"""
Resource validation utilities for the CDM Ontologies Pipeline.
"""

import os
import shutil
import psutil
from typing import Optional, Tuple

def check_system_resources(min_memory_gb: float = 2.0, min_disk_gb: float = 5.0) -> Tuple[bool, str]:
    """
    Check if system has sufficient resources to run the pipeline.
    
    Args:
        min_memory_gb: Minimum required memory in GB
        min_disk_gb: Minimum required disk space in GB
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    checks = []
    
    # Check available memory
    memory = psutil.virtual_memory()
    available_memory_gb = memory.available / (1024**3)
    total_memory_gb = memory.total / (1024**3)
    
    if available_memory_gb < min_memory_gb:
        checks.append(f"❌ Insufficient memory: {available_memory_gb:.1f}GB available, {min_memory_gb}GB required")
    else:
        checks.append(f"✅ Memory: {available_memory_gb:.1f}GB available / {total_memory_gb:.1f}GB total")
    
    # Check available disk space
    disk_usage = shutil.disk_usage('.')
    available_disk_gb = disk_usage.free / (1024**3)
    total_disk_gb = disk_usage.total / (1024**3)
    
    if available_disk_gb < min_disk_gb:
        checks.append(f"❌ Insufficient disk space: {available_disk_gb:.1f}GB available, {min_disk_gb}GB required")
    else:
        checks.append(f"✅ Disk space: {available_disk_gb:.1f}GB available / {total_disk_gb:.1f}GB total")
    
    # Check if ROBOT is available
    robot_path = shutil.which('robot')
    if robot_path:
        checks.append(f"✅ ROBOT found: {robot_path}")
    else:
        checks.append("❌ ROBOT not found in PATH")
    
    # Check if semsql is available
    semsql_path = shutil.which('semsql')
    if semsql_path:
        checks.append(f"✅ SemsQL found: {semsql_path}")
    else:
        checks.append("❌ SemsQL not found in PATH")
    
    # Check if relation-graph is available
    rg_path = shutil.which('relation-graph')
    if rg_path:
        checks.append(f"✅ relation-graph found: {rg_path}")
    else:
        checks.append("❌ relation-graph not found in PATH")
    
    # Determine overall success
    has_errors = any("❌" in check for check in checks)
    status = "FAIL" if has_errors else "PASS"
    
    message = f"\n🔍 System Resource Check - {status}\n" + "\n".join(f"   {check}" for check in checks)
    
    return not has_errors, message

def validate_step_output(step_name: str, expected_files: list, min_size_bytes: int = 1024) -> Tuple[bool, str]:
    """
    Validate that a pipeline step produced expected output files.
    
    Args:
        step_name: Name of the pipeline step
        expected_files: List of file paths that should exist
        min_size_bytes: Minimum file size to consider valid
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    checks = []
    
    for file_path in expected_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size >= min_size_bytes:
                size_mb = file_size / (1024*1024)
                checks.append(f"✅ {os.path.basename(file_path)}: {size_mb:.1f}MB")
            else:
                checks.append(f"❌ {os.path.basename(file_path)}: too small ({file_size} bytes)")
        else:
            checks.append(f"❌ {os.path.basename(file_path)}: missing")
    
    has_errors = any("❌" in check for check in checks)
    status = "PASS" if not has_errors else "FAIL"
    
    message = f"\n📋 Step Validation: {step_name} - {status}\n" + "\n".join(f"   {check}" for check in checks)
    
    return not has_errors, message

if __name__ == "__main__":
    # Run resource check when script is executed directly
    success, message = check_system_resources()
    print(message)
    exit(0 if success else 1)