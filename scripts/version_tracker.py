"""
Ontology Version Tracking System
Tracks downloads, checksums, and changes for ontology files.
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path


def get_file_checksum(filepath):
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_version_info(version_file):
    """Load existing version information."""
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}


def save_version_info(version_file, version_info):
    """Save version information to file."""
    os.makedirs(os.path.dirname(version_file), exist_ok=True)
    with open(version_file, 'w') as f:
        json.dump(version_info, f, indent=2, sort_keys=True)


def backup_old_version(filepath, checksum, version_dir):
    """Create backup of old version with checksum in filename."""
    if not os.path.exists(filepath):
        return
    
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    backup_name = f"{name}_{checksum[:8]}{ext}"
    
    backup_dir = os.path.join(version_dir, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_path = os.path.join(backup_dir, backup_name)
    if not os.path.exists(backup_path):
        shutil.copy2(filepath, backup_path)
        print(f"📦 Backed up old version: {backup_name}")


def log_download_attempt(version_dir, filename, status, checksum, url=None, error=None):
    """Log download attempt to audit trail."""
    log_file = os.path.join(version_dir, 'download_history.log')
    os.makedirs(version_dir, exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | {filename} | {status} | {checksum[:8] if checksum else 'N/A'}"
    
    if url:
        log_entry += f" | {url}"
    if error:
        log_entry += f" | ERROR: {error}"
    
    with open(log_file, 'a') as f:
        f.write(log_entry + '\n')


def update_version_info(version_file, filename, url, old_checksum, new_checksum, check_only=False, remote_metadata=None):
    """Update version tracking information."""
    version_info = load_version_info(version_file)
    
    # Get file size
    file_size = 0
    if os.path.exists(os.path.join(os.path.dirname(version_file), '..', filename)):
        file_path = os.path.join(os.path.dirname(version_file), '..', filename)
        file_size = os.path.getsize(file_path)
    
    # If we're just checking (not downloading), update last_checked only
    if check_only and filename in version_info:
        version_info[filename]['last_checked'] = datetime.now().isoformat()
        # Update remote metadata if provided
        if remote_metadata:
            version_info[filename].update(remote_metadata)
    else:
        version_info[filename] = {
            'url': url,
            'checksum': new_checksum,
            'previous_checksum': old_checksum,
            'last_updated': datetime.now().isoformat(),
            'last_checked': datetime.now().isoformat(),
            'size_bytes': file_size,
            'version_history': version_info.get(filename, {}).get('version_history', [])
        }
        # Add remote metadata if provided
        if remote_metadata:
            version_info[filename].update(remote_metadata)
    
    # Add to version history
    if old_checksum:
        version_info[filename]['version_history'].append({
            'checksum': old_checksum,
            'replaced_on': datetime.now().isoformat()
        })
    
    save_version_info(version_file, version_info)


def get_version_status(version_file, filename):
    """Get version status for a specific file."""
    version_info = load_version_info(version_file)
    return version_info.get(filename, {})


def should_download(filepath, url, version_file, check_remote=True):
    """Determine if file should be downloaded based on version tracking."""
    filename = os.path.basename(filepath)
    
    # If file doesn't exist, definitely download
    if not os.path.exists(filepath):
        return True, "file_not_exists"
    
    # Check if we have version info
    version_info = load_version_info(version_file)
    file_info = version_info.get(filename, {})
    
    # If no version info, check file and update tracking
    if not file_info:
        return True, "no_version_info"
    
    # Compare current file checksum with tracked checksum
    current_checksum = get_file_checksum(filepath)
    tracked_checksum = file_info.get('checksum')
    
    if current_checksum != tracked_checksum:
        return True, "checksum_mismatch"
    
    # Check if URL has changed
    if file_info.get('url') != url:
        return True, "url_changed"
    
    # Check remote changes if enabled
    if check_remote:
        # Import here to avoid circular dependency
        from enhanced_download import check_remote_changes
        if check_remote_changes(url, file_info):
            return True, "remote_changed"
    
    return False, "up_to_date"


def generate_version_report(version_file, output_file=None):
    """Generate a human-readable version report."""
    version_info = load_version_info(version_file)
    
    if not version_info:
        report = "No version information available.\n"
    else:
        report = "# Ontology Version Report\n\n"
        report += f"Generated: {datetime.now().isoformat()}\n\n"
        
        for filename, info in sorted(version_info.items()):
            report += f"## {filename}\n"
            report += f"- **URL**: {info.get('url', 'Unknown')}\n"
            report += f"- **Size**: {info.get('size_bytes', 0):,} bytes\n"
            report += f"- **Checksum**: {info.get('checksum', 'N/A')[:16]}...\n"
            report += f"- **Last Updated**: {info.get('last_updated', 'Unknown')}\n"
            
            history = info.get('version_history', [])
            if history:
                report += f"- **Previous Versions**: {len(history)}\n"
            
            report += "\n"
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"📊 Version report saved to: {output_file}")
    
    return report