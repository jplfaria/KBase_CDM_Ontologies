#!/bin/bash
# Simple script to create ontology test package using CDM pipeline tools

set -e  # Exit on error

# Check arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <output_directory>"
    echo "Example: $0 /scratch/jplfaria/ontologies_play"
    exit 1
fi

OUTPUT_BASE="$1"
WORK_DIR="$OUTPUT_BASE/ontology_test_package"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Creating ontology test package..."
echo "Output directory: $OUTPUT_BASE"
echo "Working directory: $WORK_DIR"

# Create working directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Download ontologies
echo "Downloading seed.owl..."
curl -L -o seed.owl https://raw.githubusercontent.com/Knowledge-Graph-Hub/semantic-units/main/seed.owl

echo "Downloading modelseed.owl..."
curl -L -o modelseed.owl https://raw.githubusercontent.com/ModelSEED/ModelSEEDDatabase/master/Biochemistry/Ontologies/modelseed_ontology.owl

# Check if we have custom prefixes
PREFIXES_FILE="$REPO_ROOT/semsql_custom_prefixes/prefixes.yaml"
if [ -f "$PREFIXES_FILE" ]; then
    echo "Using custom prefixes from: $PREFIXES_FILE"
    PREFIXES_ARG="-P $PREFIXES_FILE"
else
    echo "No custom prefixes file found"
    PREFIXES_ARG=""
fi

# Function to process an ontology
process_ontology() {
    local name=$1
    local owl_file=$2
    
    echo "Processing $name..."
    
    # Create SemanticSQL database
    echo "  Creating SemanticSQL database..."
    semsql make "${name}.db" -i "$owl_file" $PREFIXES_ARG
    
    # Extract statements table
    echo "  Extracting statements table..."
    sqlite3 -header -separator $'\t' "${name}.db" 'SELECT * FROM statements' > "${name}_statements.tsv"
    
    # Extract entailed_edge table
    echo "  Extracting entailed_edge table..."
    sqlite3 -header -separator $'\t' "${name}.db" 'SELECT * FROM entailed_edge' > "${name}_entailed_edge.tsv"
    
    # Convert TSV to Parquet using Python
    echo "  Converting to Parquet format..."
    python3 -c "
import pandas as pd
import sys

# Statements
try:
    df = pd.read_csv('${name}_statements.tsv', sep='\t')
    df.to_parquet('${name}_statements.parquet', index=False)
    print(f'    Created ${name}_statements.parquet with {len(df)} rows')
except Exception as e:
    print(f'    Warning: Could not create statements parquet: {e}')

# Entailed edges
try:
    df = pd.read_csv('${name}_entailed_edge.tsv', sep='\t')
    df.to_parquet('${name}_entailed_edge.parquet', index=False)
    print(f'    Created ${name}_entailed_edge.parquet with {len(df)} rows')
except Exception as e:
    print(f'    Warning: Could not create entailed_edge parquet: {e}')
"
}

# Process individual ontologies
process_ontology "seed" "seed.owl"
process_ontology "modelseed" "modelseed.owl"

# Convert seed.owl to JSON
echo "Converting seed.owl to JSON..."
robot convert --input seed.owl --output seed.json

# Merge ontologies
echo "Merging ontologies..."
robot merge --input seed.owl --input modelseed.owl --output modelseed_unified.owl

# Process merged ontology
process_ontology "modelseed_unified" "modelseed_unified.owl"

# Create package
PACKAGE_NAME="ontology_test_package.tar.gz"
PACKAGE_PATH="$OUTPUT_BASE/$PACKAGE_NAME"

echo "Creating package: $PACKAGE_PATH"
tar -czf "$PACKAGE_PATH" \
    *.owl \
    *.json \
    *.db \
    *.tsv \
    *.parquet

# Create summary
SUMMARY_PATH="$OUTPUT_BASE/package_contents.txt"
cat > "$SUMMARY_PATH" << EOF
Ontology Test Package Contents
==================================================

OWL Files:
- seed.owl
- modelseed.owl  
- modelseed_unified.owl (merged)

For each ontology:
- {name}.db (SemanticSQL database)
- {name}_statements.tsv
- {name}_statements.parquet
- {name}_entailed_edge.tsv
- {name}_entailed_edge.parquet

Additional:
- seed.json (ROBOT conversion of seed.owl)

Package location: $PACKAGE_PATH
Package size: $(du -h "$PACKAGE_PATH" | cut -f1)

Files in package:
$(tar -tzf "$PACKAGE_PATH" | sort)
EOF

echo ""
echo "✅ Success! Package created at: $PACKAGE_PATH"
echo "📄 See summary at: $SUMMARY_PATH"
echo ""
echo "To download to your local machine:"
echo "  scp jplfaria@poplar:$PACKAGE_PATH ."
echo ""
echo "Working directory preserved at: $WORK_DIR"