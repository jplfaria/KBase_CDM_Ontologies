"""
Run Summary Generator for CDM Ontologies Pipeline
Tracks and reports all activities during a pipeline run.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import psutil
import tempfile
from functools import wraps


def auto_save(method):
    """Decorator to automatically save state after method execution."""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        self.save_state()
        return result
    return wrapper


class RunSummary:
    """Collects and generates summary of pipeline run."""
    
    def __init__(self, run_id: str, output_dir: str, mode: str = "PRODUCTION"):
        self.run_id = run_id
        self.output_dir = output_dir
        self.mode = mode
        self.start_time = datetime.now()
        self.end_time = None
        self.status = "RUNNING"
        
        # System resources at start
        memory = psutil.virtual_memory()
        # Get disk usage for the output directory's mount point
        disk = psutil.disk_usage(output_dir)
        
        self.system_info = {
            'initial_memory_available_gb': round(memory.available / (1024**3), 1),
            'total_memory_gb': round(memory.total / (1024**3), 1),
            'initial_disk_available_gb': round(disk.free / (1024**3), 1),
            'total_disk_gb': round(disk.total / (1024**3), 1),
            'peak_memory_usage_gb': 0,
            'peak_memory_percent': 0
        }
        
        # Steps tracking
        self.steps = {}
        self.current_step = None
        
        # Ontology tracking
        self.ontology_stats = {
            'total_processed': 0,
            'new_downloads': [],
            'updated': [],
            'skipped': [],
            'failed': [],
            'remote_changes_detected': []
        }
        
        # Version tracking
        self.version_changes = {
            'files_updated': [],
            'backups_created': 0,
            'backup_size_gb': 0
        }
        
        # Processing results
        self.processing_results = {}
        
        # Errors and warnings
        self.issues = {
            'errors': [],
            'warnings': []
        }
        
        # Output files
        self.output_files = {}
        
    @auto_save
    def start_step(self, step_name: str, step_number: int):
        """Mark the start of a pipeline step."""
        self.current_step = step_name
        self.steps[step_name] = {
            'number': step_number,
            'start_time': datetime.now(),
            'end_time': None,
            'status': 'RUNNING',
            'duration_seconds': 0,
            'details': {}
        }
    
    @auto_save
    def end_step(self, step_name: str, status: str = 'SUCCESS', details: Dict = None):
        """Mark the end of a pipeline step."""
        if step_name in self.steps:
            self.steps[step_name]['end_time'] = datetime.now()
            self.steps[step_name]['status'] = status
            duration = self.steps[step_name]['end_time'] - self.steps[step_name]['start_time']
            self.steps[step_name]['duration_seconds'] = duration.total_seconds()
            if details:
                self.steps[step_name]['details'] = details
        self.current_step = None
    
    @auto_save
    def add_ontology_download(self, filename: str, status: str, size_bytes: int = 0, 
                            old_version: str = None, new_version: str = None):
        """Record an ontology download event."""
        self.ontology_stats['total_processed'] += 1
        
        download_info = {
            'filename': filename,
            'size_mb': round(size_bytes / (1024**2), 1) if size_bytes else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        if status == 'new':
            self.ontology_stats['new_downloads'].append(download_info)
        elif status == 'updated':
            download_info['old_version'] = old_version
            download_info['new_version'] = new_version
            self.ontology_stats['updated'].append(download_info)
        elif status == 'skipped':
            self.ontology_stats['skipped'].append(filename)
        elif status == 'failed':
            self.ontology_stats['failed'].append(download_info)
        elif status == 'remote_changed':
            self.ontology_stats['remote_changes_detected'].append(download_info)
    
    @auto_save
    def add_version_change(self, filename: str, old_checksum: str, new_checksum: str):
        """Record a version change."""
        self.version_changes['files_updated'].append({
            'filename': filename,
            'old_checksum': old_checksum[:8] if old_checksum else 'N/A',
            'new_checksum': new_checksum[:8] if new_checksum else 'N/A'
        })
    
    @auto_save
    def add_backup(self, size_bytes: int):
        """Record backup creation."""
        self.version_changes['backups_created'] += 1
        self.version_changes['backup_size_gb'] += size_bytes / (1024**3)
    
    @auto_save
    def update_memory_usage(self, usage_gb: float, usage_percent: float):
        """Update peak memory usage if current is higher."""
        if usage_gb > self.system_info['peak_memory_usage_gb']:
            self.system_info['peak_memory_usage_gb'] = round(usage_gb, 1)
            self.system_info['peak_memory_percent'] = round(usage_percent, 1)
    
    @auto_save
    def add_processing_result(self, key: str, value: Any):
        """Add a processing result metric."""
        self.processing_results[key] = value
    
    @auto_save
    def add_output_file(self, name: str, path: str, size_bytes: int = 0):
        """Record an output file."""
        self.output_files[name] = {
            'path': path,
            'size_gb': round(size_bytes / (1024**3), 2) if size_bytes else 0
        }
    
    @auto_save
    def add_error(self, error_msg: str):
        """Add an error message."""
        self.issues['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'message': error_msg,
            'step': self.current_step
        })
    
    @auto_save
    def add_warning(self, warning_msg: str):
        """Add a warning message."""
        self.issues['warnings'].append({
            'timestamp': datetime.now().isoformat(),
            'message': warning_msg,
            'step': self.current_step
        })
    
    @auto_save
    def finalize(self, status: str = 'SUCCESS'):
        """Finalize the summary."""
        self.end_time = datetime.now()
        self.status = status
        
        # Get final system resources
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(self.output_dir)
        self.system_info['final_memory_available_gb'] = round(memory.available / (1024**3), 1)
        self.system_info['final_disk_available_gb'] = round(disk.free / (1024**3), 1)
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def generate_summary(self) -> str:
        """Generate the formatted summary text."""
        if not self.end_time:
            self.finalize()
        
        duration = (self.end_time - self.start_time).total_seconds()
        
        lines = []
        lines.append("CDM Ontologies Pipeline Run Summary")
        lines.append("=" * 70)
        lines.append(f"Run ID: {self.run_id}")
        lines.append(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"End Time: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Duration: {self.format_duration(duration)}")
        lines.append(f"Status: {self.status}")
        lines.append(f"Mode: {self.mode}")
        lines.append("")
        
        # System Resources
        lines.append("System Resources:")
        lines.append(f"- Initial Memory: {self.system_info['initial_memory_available_gb']}GB available / {self.system_info['total_memory_gb']}GB total")
        lines.append(f"- Peak Memory Usage: {self.system_info['peak_memory_usage_gb']}GB ({self.system_info['peak_memory_percent']}% of system)")
        lines.append(f"- Initial Disk: {self.system_info['initial_disk_available_gb']}GB available")
        lines.append(f"- Final Disk: {self.system_info['final_disk_available_gb']}GB available")
        disk_used = self.system_info['initial_disk_available_gb'] - self.system_info['final_disk_available_gb']
        lines.append(f"- Disk Used: {disk_used:.1f}GB")
        lines.append("")
        
        # Ontology Downloads
        lines.append("Ontology Downloads:")
        lines.append(f"- Total Ontologies Processed: {self.ontology_stats['total_processed']}")
        
        if self.ontology_stats['new_downloads']:
            lines.append(f"- New Downloads: {len(self.ontology_stats['new_downloads'])}")
            for ont in self.ontology_stats['new_downloads'][:5]:  # Show first 5
                lines.append(f"  • {ont['filename']} ({ont['size_mb']}MB)")
            if len(self.ontology_stats['new_downloads']) > 5:
                lines.append(f"  ... and {len(self.ontology_stats['new_downloads']) - 5} more")
        
        if self.ontology_stats['updated']:
            lines.append(f"- Updated: {len(self.ontology_stats['updated'])}")
            for ont in self.ontology_stats['updated'][:5]:
                lines.append(f"  • {ont['filename']} ({ont['size_mb']}MB)")
        
        lines.append(f"- Skipped (Up-to-date): {len(self.ontology_stats['skipped'])}")
        lines.append(f"- Failed Downloads: {len(self.ontology_stats['failed'])}")
        
        if self.ontology_stats['failed']:
            for ont in self.ontology_stats['failed']:
                lines.append(f"  • {ont['filename']}")
        lines.append("")
        
        # Version Changes
        if self.version_changes['files_updated']:
            lines.append("Version Changes:")
            lines.append(f"- Files Updated: {len(self.version_changes['files_updated'])}")
            for change in self.version_changes['files_updated'][:5]:
                lines.append(f"  • {change['filename']}: {change['old_checksum']} → {change['new_checksum']}")
            lines.append(f"- Backups Created: {self.version_changes['backups_created']}")
            lines.append(f"- Total Backup Size: {self.version_changes['backup_size_gb']:.2f}GB")
            lines.append("")
        
        # Pipeline Steps
        lines.append("Pipeline Steps:")
        for step_name, step_data in sorted(self.steps.items(), key=lambda x: x[1]['number']):
            status_icon = "✓" if step_data['status'] == 'SUCCESS' else "✗" if step_data['status'] == 'FAILED' else "⚠"
            duration_str = self.format_duration(step_data['duration_seconds'])
            lines.append(f"{status_icon} Step {step_data['number']}: {step_name} ({duration_str})")
            
            # Add step details if available
            if step_data['details']:
                for key, value in step_data['details'].items():
                    lines.append(f"  - {key}: {value}")
        lines.append("")
        
        # Processing Results
        if self.processing_results:
            lines.append("Processing Results:")
            for key, value in self.processing_results.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
        
        # Issues
        if self.issues['errors'] or self.issues['warnings']:
            lines.append("Issues Encountered:")
            for warning in self.issues['warnings']:
                lines.append(f"⚠️  Warning: {warning['message']}")
            for error in self.issues['errors']:
                lines.append(f"✗  Error: {error['message']}")
            lines.append("")
        
        # Output Files
        if self.output_files:
            lines.append("Output Files:")
            for name, info in self.output_files.items():
                size_str = f" ({info['size_gb']}GB)" if info['size_gb'] > 0 else ""
                lines.append(f"- {name}: {os.path.basename(info['path'])}{size_str}")
            lines.append("")
        
        # Footer
        lines.append("-" * 70)
        lines.append(f"Summary generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def save_summary(self):
        """Save the summary to a file."""
        summary_text = self.generate_summary()
        
        # Save with timestamp in filename
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        summary_file = os.path.join(self.output_dir, f"run_summary_{timestamp}.txt")
        
        with open(summary_file, 'w') as f:
            f.write(summary_text)
        
        # Also save as JSON for programmatic access
        json_file = os.path.join(self.output_dir, f"run_summary_{timestamp}.json")
        summary_data = {
            'run_id': self.run_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            'status': self.status,
            'mode': self.mode,
            'system_info': self.system_info,
            'steps': self.steps,
            'ontology_stats': self.ontology_stats,
            'version_changes': self.version_changes,
            'processing_results': self.processing_results,
            'issues': self.issues,
            'output_files': self.output_files
        }
        
        with open(json_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        return summary_file, json_file
    
    def print_summary(self):
        """Print summary to console."""
        print("\n" + "=" * 70)
        print(self.generate_summary())
        print("=" * 70 + "\n")
    
    def save_state(self):
        """Save current state to temporary file for inter-process communication."""
        summary_path = os.environ.get('RUN_SUMMARY_PATH')
        if summary_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(summary_path), exist_ok=True)
            state = {
                'run_id': self.run_id,
                'output_dir': self.output_dir,
                'mode': self.mode,
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'status': self.status,
                'system_info': self.system_info,
                'steps': self.steps,
                'current_step': self.current_step,
                'ontology_stats': self.ontology_stats,
                'version_changes': self.version_changes,
                'processing_results': self.processing_results,
                'issues': self.issues,
                'output_files': self.output_files
            }
            with open(summary_path, 'w') as f:
                json.dump(state, f, indent=2, default=str)
    
    @classmethod
    def load_state(cls, summary_path: str) -> 'RunSummary':
        """Load summary state from temporary file."""
        with open(summary_path, 'r') as f:
            state = json.load(f)
        
        summary = cls(state['run_id'], state['output_dir'], state['mode'])
        summary.start_time = datetime.fromisoformat(state['start_time'])
        if state['end_time']:
            summary.end_time = datetime.fromisoformat(state['end_time'])
        summary.status = state['status']
        summary.system_info = state['system_info']
        summary.steps = state['steps']
        summary.current_step = state['current_step']
        summary.ontology_stats = state['ontology_stats']
        summary.version_changes = state['version_changes']
        summary.processing_results = state['processing_results']
        summary.issues = state['issues']
        summary.output_files = state['output_files']
        
        return summary


# Global instance for easy access
_summary_instance = None

def get_summary() -> Optional[RunSummary]:
    """Get the current summary instance, loading from file if needed."""
    global _summary_instance
    
    # If we already have an instance, return it
    if _summary_instance:
        return _summary_instance
    
    # Try to load from environment path
    summary_path = os.environ.get('RUN_SUMMARY_PATH')
    if summary_path and os.path.exists(summary_path):
        try:
            _summary_instance = RunSummary.load_state(summary_path)
            return _summary_instance
        except Exception:
            # If loading fails, return None
            pass
    
    return None

def init_summary(run_id: str, output_dir: str, mode: str = "PRODUCTION") -> RunSummary:
    """Initialize a new summary instance."""
    global _summary_instance
    _summary_instance = RunSummary(run_id, output_dir, mode)
    
    # Save summary file path to environment for child processes
    os.environ['RUN_SUMMARY_PATH'] = os.path.join(output_dir, '.run_summary_temp.json')
    
    # Immediately save state so child processes can access it
    _summary_instance.save_state()
    
    return _summary_instance