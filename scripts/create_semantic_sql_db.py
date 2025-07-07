import sys
import os
import subprocess
import traceback
import shutil
from pathlib import Path
from enhanced_download import get_output_directories, is_test_mode
from run_summary import get_summary

def create_semantic_sql_db(
    repo_path: str,
    input_owl_filename: str = 'CDM_merged_ontologies.owl'
) -> bool:
    """
    Create a semantic SQL database from the merged ontologies OWL file using semsql make.
    """
    try:
        # Setup paths - support test configuration
        test_mode = is_test_mode()
        ontology_data_path, _, outputs_path, version_dir = get_output_directories(repo_path, test_mode)
        
        outputs_dir = outputs_path
        os.makedirs(outputs_dir, exist_ok=True)
        
        print(f"🔧 Mode: {'TEST' if test_mode else 'PRODUCTION'}")
        print(f"📁 Working directory: {outputs_dir}")
        
        # Change to outputs directory (semsql make expects OWL file in current directory)
        original_cwd = os.getcwd()
        os.chdir(outputs_dir)
        
        db_filename = input_owl_filename.replace('.owl', '.db')
        
        print(f"📥 Input OWL file: {input_owl_filename}")
        print(f"📤 Output DB file: {db_filename}")
        
        # Verify input file exists
        if not os.path.exists(input_owl_filename):
            raise FileNotFoundError(f"Input OWL file not found: {input_owl_filename}")
        
        # Set up environment for semsql
        env = os.environ.copy()
        env['PATH'] = f"/home/ontology/.local/bin:{env.get('PATH', '')}"
        
        # Use environment variables for memory settings or set defaults
        # For SemsQL, we need to ensure ROBOT inside semsql uses sufficient memory
        robot_memory = os.getenv('ROBOT_JAVA_ARGS', '-Xmx32g -XX:MaxMetaspaceSize=4g')
        env['ROBOT_JAVA_ARGS'] = robot_memory
        # _JAVA_OPTIONS will be picked up by all Java processes including ROBOT inside semsql
        # Use the same memory settings as ROBOT_JAVA_ARGS for consistency
        env['_JAVA_OPTIONS'] = robot_memory
        
        print(f"💾 SemsQL memory settings: {env['ROBOT_JAVA_ARGS']}")
        print(f"💾 Java options (_JAVA_OPTIONS): {env['_JAVA_OPTIONS']}")
        
        # Check if memory monitoring is enabled
        enable_monitoring = os.getenv('ENABLE_MEMORY_MONITORING', 'false').lower() == 'true'
        
        print("\n🔧 Running semsql make to create database...")
        print(f"Command: semsql make {db_filename}")
        
        # Run semsql make command with optional memory monitoring
        if enable_monitoring:
            print("🔍 Memory monitoring enabled - tracking SemsQL memory usage")
            monitor_script = os.path.join(os.path.dirname(__file__), 'memory_monitor.py')
            # Already in outputs_dir, so semsql can run directly
            monitor_command = [
                'python3', monitor_script,
                'SemsQL_make',
                f'semsql make {db_filename}',
                repo_path,
                str(os.getenv('MEMORY_MONITOR_INTERVAL', '15'))
            ]
            result = subprocess.run(monitor_command, check=True, env=env, cwd=outputs_dir)
        else:
            # Run semsql make command normally
            result = subprocess.run(
                ['semsql', 'make', db_filename],
                capture_output=True,
                text=True,
                env=env,
                timeout=86400  # 24 hour timeout for large datasets
            )
        
        if result.stdout:
            print("\n📄 SEMSQL Output:")
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️ SEMSQL Errors/Warnings:")
            print(result.stderr)
        
        # Check if database was created successfully
        if os.path.exists(db_filename):
            db_size = os.path.getsize(db_filename)
            print(f"\n✅ Database successfully created!")
            print(f"📊 Database file: {db_filename}")
            print(f"📏 Database size: {db_size:,} bytes ({db_size / (1024*1024):.1f} MB)")
            
            # Update summary if available
            summary = get_summary()
            if summary:
                summary.add_output_file('semantic_sql_db', os.path.join(outputs_dir, db_filename), db_size)
                summary.add_processing_result('database_size_gb', round(db_size / (1024**3), 2))
            
            # Try to connect and show basic info
            try:
                import sqlite3
                conn = sqlite3.connect(db_filename)
                cursor = conn.cursor()
                
                # Get list of tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = [row[0] for row in cursor.fetchall()]
                
                print(f"📋 Database contains {len(tables)} tables:")
                
                # Update summary with table count
                if summary:
                    summary.add_processing_result('database_tables', len(tables))
                
                total_rows = 0
                for table in tables[:10]:  # Show first 10 tables
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    total_rows += count
                    print(f"   - {table}: {count:,} rows")
                
                if len(tables) > 10:
                    print(f"   ... and {len(tables) - 10} more tables")
                    # Count rows in remaining tables for summary
                    for table in tables[10:]:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        total_rows += count
                
                if summary:
                    summary.add_processing_result('database_total_rows', total_rows)
                
                conn.close()
                
            except Exception as db_info_error:
                print(f"📋 Database created but couldn't read table info: {str(db_info_error)}")
            
            return True
            
        else:
            print(f"\n❌ Database creation failed - {db_filename} not found")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n⏰ Error: semsql make command timed out after 1 hour")
        return False
        
    except Exception as e:
        print(f"\n💥 Error occurred: {str(e)}")
        traceback.print_exc()
        return False
        
    finally:
        # Restore original working directory
        try:
            os.chdir(original_cwd)
        except:
            pass

if __name__ == '__main__':
    repo_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    success = create_semantic_sql_db(repo_path)
    if success:
        print("\n🎉 SemsSQL database creation completed successfully!")
    else:
        print("\n💥 SemsSQL database creation failed!")
        sys.exit(1)