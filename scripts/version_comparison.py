#!/usr/bin/env python3
"""
Version Comparison Tool for Ontology Updates

Generates detailed reports when ontology versions change.
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional


def get_axiom_count(owl_file: Path) -> Optional[int]:
    """Get axiom count from an OWL file using ROBOT."""
    try:
        # Use ROBOT info to get axiom count
        robot_path = os.environ.get('ROBOT_PATH', 'robot')
        cmd = [robot_path, 'info', '--input', str(owl_file), '--format', 'json']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            # Look for axiom count in the metrics
            if 'metrics' in info:
                return info['metrics'].get('axiom_count', 0)
        return None
    except Exception as e:
        print(f"⚠️  Could not get axiom count: {e}")
        return None


def get_file_info(owl_file: Path) -> Dict:
    """Get comprehensive information about an OWL file."""
    info = {
        'size_bytes': owl_file.stat().st_size if owl_file.exists() else 0,
        'size_mb': round(owl_file.stat().st_size / (1024*1024), 2) if owl_file.exists() else 0,
        'last_modified': datetime.fromtimestamp(owl_file.stat().st_mtime).isoformat() if owl_file.exists() else None,
        'axiom_count': get_axiom_count(owl_file) if owl_file.exists() else None
    }
    return info


def compare_versions(old_file: Path, new_file: Path, ontology_name: str) -> Dict:
    """Compare two versions of an ontology and return differences."""
    old_info = get_file_info(old_file) if old_file and old_file.exists() else {}
    new_info = get_file_info(new_file)
    
    comparison = {
        'ontology': ontology_name,
        'timestamp': datetime.now().isoformat(),
        'old_version': {
            'file': str(old_file) if old_file else None,
            **old_info
        },
        'new_version': {
            'file': str(new_file),
            **new_info
        },
        'changes': {
            'size_change_bytes': new_info.get('size_bytes', 0) - old_info.get('size_bytes', 0),
            'size_change_mb': round(new_info.get('size_mb', 0) - old_info.get('size_mb', 0), 2),
            'size_change_percent': round(
                ((new_info.get('size_bytes', 0) - old_info.get('size_bytes', 0)) / old_info.get('size_bytes', 1)) * 100, 2
            ) if old_info.get('size_bytes', 0) > 0 else 0,
            'axiom_change': (new_info.get('axiom_count', 0) - old_info.get('axiom_count', 0)) 
                           if new_info.get('axiom_count') is not None and old_info.get('axiom_count') is not None else None
        }
    }
    
    return comparison


def generate_comparison_report(comparisons: list, output_file: Path):
    """Generate a human-readable comparison report."""
    with open(output_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("ONTOLOGY VERSION COMPARISON REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for comp in comparisons:
            f.write(f"📊 {comp['ontology']}\n")
            f.write("-" * 40 + "\n")
            
            # Old version info
            if comp['old_version']['file']:
                f.write("Previous version:\n")
                f.write(f"  File: {os.path.basename(comp['old_version']['file'])}\n")
                f.write(f"  Size: {comp['old_version']['size_mb']} MB\n")
                if comp['old_version'].get('axiom_count'):
                    f.write(f"  Axioms: {comp['old_version']['axiom_count']:,}\n")
            else:
                f.write("Previous version: None (new ontology)\n")
            
            # New version info
            f.write("\nNew version:\n")
            f.write(f"  File: {os.path.basename(comp['new_version']['file'])}\n")
            f.write(f"  Size: {comp['new_version']['size_mb']} MB\n")
            if comp['new_version'].get('axiom_count'):
                f.write(f"  Axioms: {comp['new_version']['axiom_count']:,}\n")
            
            # Changes
            f.write("\nChanges:\n")
            size_change = comp['changes']['size_change_mb']
            size_percent = comp['changes']['size_change_percent']
            
            if size_change > 0:
                f.write(f"  📈 Size increased by {size_change} MB ({size_percent}%)\n")
            elif size_change < 0:
                f.write(f"  📉 Size decreased by {abs(size_change)} MB ({abs(size_percent)}%)\n")
            else:
                f.write(f"  ➡️  Size unchanged\n")
            
            if comp['changes']['axiom_change'] is not None:
                axiom_change = comp['changes']['axiom_change']
                if axiom_change > 0:
                    f.write(f"  ✅ Added {axiom_change:,} axioms\n")
                elif axiom_change < 0:
                    f.write(f"  ❌ Removed {abs(axiom_change):,} axioms\n")
                else:
                    f.write(f"  ➡️  Axiom count unchanged\n")
            
            f.write("\n")
        
        # Summary
        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total ontologies checked: {len(comparisons)}\n")
        
        updated = [c for c in comparisons if c['changes']['size_change_bytes'] != 0]
        f.write(f"Updated ontologies: {len(updated)}\n")
        
        if updated:
            total_size_change = sum(c['changes']['size_change_mb'] for c in updated)
            f.write(f"Total size change: {total_size_change:+.2f} MB\n")
            
            axiom_changes = [c['changes']['axiom_change'] for c in updated 
                           if c['changes']['axiom_change'] is not None]
            if axiom_changes:
                total_axiom_change = sum(axiom_changes)
                f.write(f"Total axiom change: {total_axiom_change:+,}\n")


def check_version_updates(ontology_data_dir: Path, version_dir: Path, backup_dir: Path) -> list:
    """Check all ontologies for version updates and generate comparisons."""
    comparisons = []
    
    # Load current version info
    version_file = version_dir / 'ontology_versions.json'
    if version_file.exists():
        with open(version_file, 'r') as f:
            version_info = json.load(f)
    else:
        version_info = {}
    
    # Check each ontology file
    for owl_file in ontology_data_dir.glob('*.owl'):
        ontology_name = owl_file.name
        
        # Find the most recent backup if any
        backup_pattern = f"{owl_file.stem}_*.owl"
        backups = sorted(backup_dir.glob(backup_pattern))
        old_file = backups[-1] if backups else None
        
        # Compare versions
        comparison = compare_versions(old_file, owl_file, ontology_name)
        comparisons.append(comparison)
    
    return comparisons


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python version_comparison.py <test|prod>")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == 'test':
        ontology_dir = Path('ontology_data_owl_test')
        version_dir = Path('ontology_versions_test')
    else:
        ontology_dir = Path('ontology_data_owl')
        version_dir = Path('ontology_versions')
    
    backup_dir = version_dir / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    # Check for updates
    comparisons = check_version_updates(ontology_dir, version_dir, backup_dir)
    
    # Generate report
    report_file = version_dir / f'version_comparison_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    generate_comparison_report(comparisons, report_file)
    
    print(f"✅ Version comparison report generated: {report_file}")