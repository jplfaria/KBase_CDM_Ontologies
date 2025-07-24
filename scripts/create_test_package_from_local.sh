#!/bin/bash
# Script to create ontology test package using local ontology files

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

echo "Creating ontology test package using local files..."
echo "Output directory: $OUTPUT_BASE"
echo "Working directory: $WORK_DIR"

# Create working directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Copy ontologies from local data directory
ONTOLOGY_DIR="$REPO_ROOT/ontology_data_owl"
if [ ! -d "$ONTOLOGY_DIR" ]; then
    echo "ERROR: Ontology directory not found: $ONTOLOGY_DIR"
    echo "Please run this script from the KBase_CDM_Ontologies repository"
    exit 1
fi

echo "Copying ontologies from local directory..."
if [ -f "$ONTOLOGY_DIR/seed.owl" ]; then
    echo "  Copying seed.owl..."
    cp "$ONTOLOGY_DIR/seed.owl" .
else
    echo "ERROR: seed.owl not found in $ONTOLOGY_DIR"
    exit 1
fi

if [ -f "$ONTOLOGY_DIR/modelseed.owl" ]; then
    echo "  Copying modelseed.owl..."
    cp "$ONTOLOGY_DIR/modelseed.owl" .
else
    echo "ERROR: modelseed.owl not found in $ONTOLOGY_DIR"
    exit 1
fi

# Check file sizes
echo ""
echo "Copied files:"
ls -lh *.owl

# Build local Docker image if needed
echo ""
echo "Checking Docker image..."
if ! docker images | grep -q "cdm_ontologies_local"; then
    echo "Building Docker image..."
    cd "$REPO_ROOT"
    docker build -t cdm_ontologies_local .
    cd "$WORK_DIR"
else
    echo "Docker image already exists"
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
DOCKER_CMD="docker run --rm -v $WORK_DIR:/work -w /work cdm_ontologies_local"

# Function to process an ontology
process_ontology() {
    local name=$1
    local owl_file=$2
    
    echo ""
    echo "Processing $name..."
    
    # Create SemanticSQL database using Docker
    echo "  Creating SemanticSQL database..."
    $DOCKER_CMD semsql make "/work/${name}.db" "/work/$owl_file" $PREFIXES_ARG
    
    # Extract statements table
    echo "  Extracting statements table..."
    $DOCKER_CMD sh -c "sqlite3 -header -separator '\t' '/work/${name}.db' 'SELECT * FROM statements' > '/work/${name}_statements.tsv'"
    
    # Extract entailed_edge table
    echo "  Extracting entailed_edge table..."
    $DOCKER_CMD sh -c "sqlite3 -header -separator '\t' '/work/${name}.db' 'SELECT * FROM entailed_edge' > '/work/${name}_entailed_edge.tsv'"
    
    # Convert TSV to Parquet
    echo "  Converting to Parquet format..."
    $DOCKER_CMD python -c "
import pandas as pd
import os
os.chdir('/work')

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

# Convert seed.owl to JSON
echo ""
echo "Converting seed.owl to JSON..."
$DOCKER_CMD robot convert --input /work/seed.owl --output /work/seed.json

# Merge ontologies
echo ""
echo "Merging ontologies..."
$DOCKER_CMD robot merge --input /work/seed.owl --input /work/modelseed.owl --output /work/modelseed_unified.owl

# Process merged ontology
process_ontology "modelseed_unified" "modelseed_unified.owl"

# Fix permissions (Docker might create files as root)
echo ""
echo "Fixing file permissions..."
docker run --rm -v "$WORK_DIR:/work" --user root alpine:latest \
    chown -R $(id -u):$(id -g) /work

# Create package
PACKAGE_NAME="ontology_test_package.tar.gz"
PACKAGE_PATH="$OUTPUT_BASE/$PACKAGE_NAME"

echo ""
echo "Creating package: $PACKAGE_PATH"
tar -czf "$PACKAGE_PATH" \
    *.owl \
    *.json \
    *.db \
    *.tsv \
    *.parquet 2>/dev/null || {
    echo "Creating package with available files..."
    tar -czf "$PACKAGE_PATH" *
}

# Create summary
SUMMARY_PATH="$OUTPUT_BASE/package_contents.txt"
echo ""
echo "Creating summary..."
cat > "$SUMMARY_PATH" << EOF
Ontology Test Package Contents
==================================================

OWL Files:
- seed.owl ($(ls -lh seed.owl | awk '{print $5}'))
- modelseed.owl ($(ls -lh modelseed.owl | awk '{print $5}'))
- modelseed_unified.owl ($(ls -lh modelseed_unified.owl | awk '{print $5}'))

Databases:
$(ls -lh *.db 2>/dev/null | awk '{print "- " $9 " (" $5 ")"}')

TSV Files:
$(ls -lh *.tsv 2>/dev/null | awk '{print "- " $9 " (" $5 ")"}')

Parquet Files:
$(ls -lh *.parquet 2>/dev/null | awk '{print "- " $9 " (" $5 ")"}')

JSON Files:
$(ls -lh *.json 2>/dev/null | awk '{print "- " $9 " (" $5 ")"}')

Package Details:
- Location: $PACKAGE_PATH
- Size: $(du -h "$PACKAGE_PATH" | cut -f1)
- Created: $(date)
- Source files from: $ONTOLOGY_DIR

Docker image: cdm_ontologies_local (built from $REPO_ROOT)

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