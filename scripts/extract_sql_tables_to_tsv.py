import os
import sqlite3
import pandas as pd
from pathlib import Path
from enhanced_download import get_output_directories, is_test_mode
from run_summary import get_summary

def extract_sql_tables_to_tsv(repo_path: str) -> bool:
    """
    Extract all tables from the CDM_merged_ontologies.db database to TSV files.
    
    Args:
        repo_path (str): Path to the repository root directory
    
    Returns:
        bool: True if extraction was successful, False otherwise
    """
    try:
        # Setup paths - support test configuration
        test_mode = is_test_mode()
        ontology_data_path, _, outputs_path, version_dir = get_output_directories(repo_path, test_mode)
        
        outputs_dir = outputs_path
        db_file = os.path.join(outputs_dir, 'CDM_merged_ontologies.db')
        tsv_dir = os.path.join(outputs_dir, 'tsv_tables')
        
        print(f"🔧 Mode: {'TEST' if test_mode else 'PRODUCTION'}")
        print(f"📁 Database file: {db_file}")
        print(f"📁 TSV output directory: {tsv_dir}")
        
        # Verify database file exists
        if not os.path.exists(db_file):
            raise FileNotFoundError(f"Database file not found: {db_file}")
        
        # Ensure the TSV output directory exists
        os.makedirs(tsv_dir, exist_ok=True)
        
        print(f"Reading database from: {db_file}")
        print(f"Saving TSV files to: {tsv_dir}")
        
        # Connect to the SQLite database
        conn = sqlite3.connect(db_file)
        
        try:
            # Get a list of all tables in the database
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Update summary if available
            summary = get_summary()
            if summary:
                summary.add_processing_result('tsv_tables_exported', len(tables))
            
            total_tsv_size = 0
            
            # Extract each table and save as TSV
            for table in tables:
                table_name = table[0]
                print(f"Processing table: {table_name}")
                
                # Read the table into a pandas DataFrame
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                # Escape newlines, carriage returns, and tabs in all string columns
                for col in df.columns:
                    if df[col].dtype == 'object':  # String columns
                        df[col] = df[col].apply(lambda x: 
                            x.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') 
                            if isinstance(x, str) else x
                        )
                
                # Create the output path
                output_path = os.path.join(tsv_dir, f"{table_name}.tsv")
                
                # Save as TSV with proper escaping
                df.to_csv(output_path, sep='\t', index=False, escapechar='\\', doublequote=False)
                print(f"Exported '{table_name}' to '{output_path}'")
                
                # Track file size
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    total_tsv_size += file_size
            
            print(f"\nAll tables have been exported to TSV files in: {tsv_dir}")
            
            # Update summary with TSV output info
            if summary:
                summary.add_output_file('tsv_tables', tsv_dir, total_tsv_size)
                summary.add_processing_result('tsv_total_size_gb', round(total_tsv_size / (1024**3), 2))
            
            return True
            
        finally:
            # Always close the connection
            conn.close()
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return False

if __name__ == '__main__':
    repo_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    extract_sql_tables_to_tsv(repo_path)