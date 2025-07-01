#!/usr/bin/env python3
"""
Version Manager - CLI tool for managing ontology versions and tracking.
"""

import sys
import os
import argparse
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from version_tracker import (
    load_version_info, generate_version_report, 
    get_file_checksum, log_download_attempt
)
from enhanced_download import is_test_mode, get_output_directories


def show_status(repo_path):
    """Show current version status."""
    test_mode = is_test_mode()
    _, _, _, version_dir = get_output_directories(repo_path, test_mode)
    version_file = os.path.join(version_dir, 'ontology_versions.json')
    
    print(f"🔧 Mode: {'TEST' if test_mode else 'PRODUCTION'}")
    print(f"📁 Version Directory: {version_dir}")
    print()
    
    if not os.path.exists(version_file):
        print("❌ No version information found")
        return
    
    version_info = load_version_info(version_file)
    
    if not version_info:
        print("📝 Version file exists but is empty")
        return
    
    print(f"📊 Tracking {len(version_info)} ontologies:")
    print()
    
    for filename, info in sorted(version_info.items()):
        size_mb = info.get('size_bytes', 0) / (1024 * 1024)
        checksum = info.get('checksum', 'N/A')[:8]
        last_updated = info.get('last_updated', 'Unknown')[:10]  # Just the date
        
        status = "🆕" if not info.get('previous_checksum') else "🔄"
        
        print(f"  {status} {filename:<25} {size_mb:>6.1f}MB  {checksum}...  {last_updated}")


def generate_report(repo_path, output_file=None):
    """Generate detailed version report."""
    test_mode = is_test_mode()
    _, _, _, version_dir = get_output_directories(repo_path, test_mode)
    version_file = os.path.join(version_dir, 'ontology_versions.json')
    
    if output_file is None:
        output_file = os.path.join(version_dir, 'version_report.md')
    
    report = generate_version_report(version_file, output_file)
    print(report)


def validate_files(repo_path):
    """Validate that tracked files match their checksums."""
    test_mode = is_test_mode()
    ontology_data_path, _, _, version_dir = get_output_directories(repo_path, test_mode)
    version_file = os.path.join(version_dir, 'ontology_versions.json')
    
    if not os.path.exists(version_file):
        print("❌ No version information found")
        return
    
    version_info = load_version_info(version_file)
    
    print("🔍 Validating file checksums...")
    print()
    
    valid_count = 0
    invalid_count = 0
    missing_count = 0
    
    for filename, info in version_info.items():
        file_path = os.path.join(ontology_data_path, filename)
        tracked_checksum = info.get('checksum')
        
        if not os.path.exists(file_path):
            print(f"❌ {filename:<25} - File missing")
            missing_count += 1
            continue
        
        current_checksum = get_file_checksum(file_path)
        
        if current_checksum == tracked_checksum:
            print(f"✅ {filename:<25} - Checksum valid")
            valid_count += 1
        else:
            print(f"⚠️  {filename:<25} - Checksum mismatch!")
            print(f"   Tracked:  {tracked_checksum[:16]}...")
            print(f"   Current:  {current_checksum[:16]}...")
            invalid_count += 1
    
    print()
    print(f"📊 Summary: {valid_count} valid, {invalid_count} invalid, {missing_count} missing")


def show_history(repo_path, filename=None):
    """Show download history."""
    test_mode = is_test_mode()
    _, _, _, version_dir = get_output_directories(repo_path, test_mode)
    
    if filename:
        # Show specific file history
        version_file = os.path.join(version_dir, 'ontology_versions.json')
        version_info = load_version_info(version_file)
        
        if filename not in version_info:
            print(f"❌ No version information for {filename}")
            return
        
        info = version_info[filename]
        print(f"📋 Version History for {filename}")
        print(f"   URL: {info.get('url', 'Unknown')}")
        print(f"   Current Checksum: {info.get('checksum', 'N/A')}")
        print(f"   Last Updated: {info.get('last_updated', 'Unknown')}")
        
        history = info.get('version_history', [])
        if history:
            print(f"   Previous Versions: {len(history)}")
            for i, old_version in enumerate(history, 1):
                print(f"     {i}. {old_version.get('checksum', 'N/A')[:16]}... ({old_version.get('replaced_on', 'Unknown')[:10]})")
        else:
            print("   No previous versions")
    else:
        # Show download log
        log_file = os.path.join(version_dir, 'download_history.log')
        
        if not os.path.exists(log_file):
            print("❌ No download history found")
            return
        
        print("📋 Recent Download History:")
        print()
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Show last 20 entries
        for line in lines[-20:]:
            if line.strip():
                parts = line.strip().split(' | ')
                if len(parts) >= 4:
                    timestamp, filename, status, checksum = parts[:4]
                    date_time = timestamp[:19]  # Remove microseconds
                    status_icon = {"new": "🆕", "updated": "🔄", "skipped": "⏭️", "no_change": "✅", "error": "❌"}.get(status, "❓")
                    print(f"  {status_icon} {date_time} | {filename:<20} | {status}")


def clean_backups(repo_path, keep=5):
    """Clean old backup files, keeping only the most recent ones."""
    test_mode = is_test_mode()
    _, _, _, version_dir = get_output_directories(repo_path, test_mode)
    backup_dir = os.path.join(version_dir, 'backups')
    
    if not os.path.exists(backup_dir):
        print("📁 No backup directory found")
        return
    
    backup_files = list(Path(backup_dir).glob('*'))
    if not backup_files:
        print("📁 No backup files found")
        return
    
    # Group by base filename
    file_groups = {}
    for backup_file in backup_files:
        # Extract base filename from backup name (remove _checksum part)
        name_parts = backup_file.stem.split('_')
        if len(name_parts) >= 2:
            base_name = '_'.join(name_parts[:-1]) + backup_file.suffix
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(backup_file)
    
    removed_count = 0
    
    for base_name, backups in file_groups.items():
        # Sort by modification time (newest first)
        backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Remove old backups beyond the keep limit
        for old_backup in backups[keep:]:
            print(f"🗑️  Removing old backup: {old_backup.name}")
            old_backup.unlink()
            removed_count += 1
    
    remaining_count = sum(min(len(backups), keep) for backups in file_groups.values())
    print(f"✅ Cleanup complete: {removed_count} removed, {remaining_count} kept")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='Ontology Version Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python version_manager.py status                    # Show current status
  python version_manager.py report                    # Generate detailed report
  python version_manager.py validate                  # Validate file checksums
  python version_manager.py history                   # Show download history
  python version_manager.py history bfo.owl           # Show history for specific file
  python version_manager.py clean --keep 3            # Clean old backups, keep 3 newest
        """
    )
    
    parser.add_argument('command', choices=['status', 'report', 'validate', 'history', 'clean'],
                        help='Command to execute')
    parser.add_argument('filename', nargs='?', help='Specific filename for history command')
    parser.add_argument('--keep', type=int, default=5, help='Number of backups to keep (default: 5)')
    parser.add_argument('--output', '-o', help='Output file for report')
    
    args = parser.parse_args()
    
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("🗂️  CDM Ontologies Version Manager")
    print("=" * 50)
    
    if args.command == 'status':
        show_status(repo_path)
    elif args.command == 'report':
        generate_report(repo_path, args.output)
    elif args.command == 'validate':
        validate_files(repo_path)
    elif args.command == 'history':
        show_history(repo_path, args.filename)
    elif args.command == 'clean':
        clean_backups(repo_path, args.keep)


if __name__ == '__main__':
    main()