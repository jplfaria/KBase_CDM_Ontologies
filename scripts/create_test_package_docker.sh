#!/bin/bash
# Script to create ontology test package using CDM pipeline Docker tools

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

echo "Creating ontology test package using Docker..."
echo "Output directory: $OUTPUT_BASE"
echo "Working directory: $WORK_DIR"

# Create working directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Download ontologies
echo "Downloading seed.owl from PURL..."
curl -L -o seed.owl http://purl.obolibrary.org/obo/seed.owl || {
    echo "Failed to download from PURL, trying GitHub..."
    curl -L -o seed.owl https://github.com/KBase-Ontologies/kbase-ontologies.github.io/raw/main/seed_reaction_ontology/seed.owl
}

echo "Downloading modelseed.owl..."
# First try the ModelSEED repo
if ! curl -f -L -o modelseed.owl https://raw.githubusercontent.com/ModelSEED/ModelSEEDDatabase/master/Biochemistry/Ontologies/modelseed_ontology.owl; then
    echo "Failed to download from ModelSEED repo, trying alternative sources..."
    # Try from KBase CDM test data
    curl -L -o modelseed.owl https://raw.githubusercontent.com/kbaseincubator/KBase_CDM_Ontologies/main/ontology_data_owl_test/modelseed.owl || {
        echo "ERROR: Could not download modelseed.owl from any source"
        exit 1
    }
fi

# Check if we have custom prefixes - copy to work dir if exists
PREFIXES_FILE="$REPO_ROOT/semsql_custom_prefixes/prefixes.yaml"
if [ -f "$PREFIXES_FILE" ]; then
    echo "Copying custom prefixes..."
    cp "$PREFIXES_FILE" .
    PREFIXES_ARG="-P /work/prefixes.yaml"
else
    echo "No custom prefixes file found"
    PREFIXES_ARG=""
fi

# Docker run command prefix
DOCKER_CMD="docker run --rm -v $WORK_DIR:/work -w /work"

# Function to process an ontology
process_ontology() {
    local name=$1
    local owl_file=$2
    
    echo "Processing $name..."
    
    # Create SemanticSQL database using Docker
    echo "  Creating SemanticSQL database..."
    $DOCKER_CMD ghcr.io/kbaseincubator/cdm_ontologies:latest \
        semsql make "/work/${name}.db" -i "/work/$owl_file" $PREFIXES_ARG
    
    # Extract statements table using Docker
    echo "  Extracting statements table..."
    $DOCKER_CMD ghcr.io/kbaseincubator/cdm_ontologies:latest \
        sqlite3 -header -separator $'\t' "/work/${name}.db" 'SELECT * FROM statements' > "${name}_statements.tsv"
    
    # Extract entailed_edge table using Docker
    echo "  Extracting entailed_edge table..."
    $DOCKER_CMD ghcr.io/kbaseincubator/cdm_ontologies:latest \
        sqlite3 -header -separator $'\t' "/work/${name}.db" 'SELECT * FROM entailed_edge' > "${name}_entailed_edge.tsv"
    
    # Convert TSV to Parquet using Python (on host, not in Docker)
    echo "  Converting to Parquet format..."
    python3 -c "
import pandas as pd
import sys
import os

os.chdir('$WORK_DIR')

# Statements
try:
    df = pd.read_csv('${name}_statements.tsv', sep='\t', low_memory=False)
    df.to_parquet('${name}_statements.parquet', index=False)
    print(f'    Created ${name}_statements.parquet with {len(df)} rows')
except Exception as e:
    print(f'    Warning: Could not create statements parquet: {e}')

# Entailed edges
try:
    df = pd.read_csv('${name}_entailed_edge.tsv', sep='\t', low_memory=False)
    df.to_parquet('${name}_entailed_edge.parquet', index=False)
    print(f'    Created ${name}_entailed_edge.parquet with {len(df)} rows')
except Exception as e:
    print(f'    Warning: Could not create entailed_edge parquet: {e}')
"
}

# Process individual ontologies
process_ontology "seed" "seed.owl"
process_ontology "modelseed" "modelseed.owl"

# Convert seed.owl to JSON using Docker
echo "Converting seed.owl to JSON..."
$DOCKER_CMD ghcr.io/kbaseincubator/cdm_ontologies:latest \
    robot convert --input /work/seed.owl --output /work/seed.json

# Merge ontologies using Docker
echo "Merging ontologies..."
$DOCKER_CMD ghcr.io/kbaseincubator/cdm_ontologies:latest \
    robot merge --input /work/seed.owl --input /work/modelseed.owl --output /work/modelseed_unified.owl

# Process merged ontology
process_ontology "modelseed_unified" "modelseed_unified.owl"

# Fix permissions (Docker might create files as root)
echo "Fixing file permissions..."
$DOCKER_CMD --user root alpine:latest \
    chown -R $(id -u):$(id -g) /work

# Create package
PACKAGE_NAME="ontology_test_package.tar.gz"
PACKAGE_PATH="$OUTPUT_BASE/$PACKAGE_NAME"

echo "Creating package: $PACKAGE_PATH"
tar -czf "$PACKAGE_PATH" \
    *.owl \
    *.json \
    *.db \
    *.tsv \
    *.parquet 2>/dev/null || echo "Note: Some file types might not exist"

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
- {name}_statements.parquet (if pandas is available)
- {name}_entailed_edge.tsv
- {name}_entailed_edge.parquet (if pandas is available)

Additional:
- seed.json (ROBOT conversion of seed.owl)

Package location: $PACKAGE_PATH
Package size: $(du -h "$PACKAGE_PATH" | cut -f1)

Files in package:
$(tar -tzf "$PACKAGE_PATH" | sort)

Docker image used: ghcr.io/kbaseincubator/cdm_ontologies:latest
EOF

echo ""
echo "✅ Success! Package created at: $PACKAGE_PATH"
echo "📄 See summary at: $SUMMARY_PATH"
echo ""
echo "To download to your local machine:"
echo "  scp jplfaria@poplar:$PACKAGE_PATH ."
echo ""
echo "Working directory preserved at: $WORK_DIR"