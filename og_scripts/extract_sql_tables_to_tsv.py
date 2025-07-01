import os
import sqlite3
import pandas as pd
from pathlib import Path

def extract_sql_tables_to_tsv(repo_path: str) -> bool:
    """
    Extract all tables from the CDM_merged_ontologies.db database to TSV files.
    
    Args:
        repo_path (str): Path to the repository root directory
    
    Returns:
        bool: True if extraction was successful, False otherwise
    """
    try:
        # Set up paths
        outputs_dir = os.path.join(repo_path, 'outputs')
        db_file = os.path.join(outputs_dir, 'CDM_merged_ontologies.db')
        tsv_dir = os.path.join(outputs_dir, 'tsv_tables')
        
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
            
            # Extract each table and save as TSV
            for table in tables:
                table_name = table[0]
                print(f"Processing table: {table_name}")
                
                # Read the table into a pandas DataFrame
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                # Create the output path
                output_path = os.path.join(tsv_dir, f"{table_name}.tsv")
                
                # Save as TSV
                df.to_csv(output_path, sep='\t', index=False)
                print(f"Exported '{table_name}' to '{output_path}'")
            
            print(f"\nAll tables have been exported to TSV files in: {tsv_dir}")
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