# Configuration Guide

This guide covers all configuration options for the CDM Ontologies Pipeline, from basic environment setup to advanced customization.

## Configuration Files

### Environment Files

The pipeline uses environment files to manage different deployment scenarios:

- **`.env`**: Production configuration (32 ontologies, 1.5TB container)
- **`.env.test`**: Test configuration (6 ontologies, same memory settings)

### Configuration File Structure

```bash
# Memory Management (Unified 1.5TB settings)
ROBOT_JAVA_ARGS=-Xmx1500g -XX:MaxMetaspaceSize=8g -XX:+UseG1GC
RELATION_GRAPH_JAVA_ARGS=-Xmx1500g -XX:MaxMetaspaceSize=8g -XX:+UseG1GC
SEMSQL_MEMORY_LIMIT=1500g
PYTHON_MEMORY_LIMIT=1500g

# Dataset Control
DATASET_SIZE=test                                        # test or large
ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt # or config/ontologies_source.txt

# Processing Options
ENABLE_MEMORY_MONITORING=true     # Track tool memory usage
ENABLE_TSV_EXPORT=true            # Export database to TSV
ENABLE_PARQUET_EXPORT=true        # Create compressed Parquet files

# Performance Tuning
PARALLEL_DOWNLOADS=10            # Concurrent downloads
BATCH_SIZE=100                   # Processing batch size
TIMEOUT_SECONDS=30               # Network timeout
MAX_RETRIES=3                    # Download retry attempts

# Logging
LOG_LEVEL=INFO                   # Logging verbosity
ENABLE_DETAILED_LOGGING=false   # Extra debug info
```

## Memory Configuration

### Java Heap Sizing

The most critical configuration is Java heap size for ROBOT and relation-graph tools:

#### Automatic Sizing (Recommended)

```bash
# Calculate based on available system memory
TOTAL_RAM=$(free -g | awk 'NR==2{print $2}')
JAVA_HEAP=$((TOTAL_RAM * 80 / 100))
export ROBOT_JAVA_ARGS="-Xmx${JAVA_HEAP}g"
```

#### Manual Sizing

```bash
# Conservative (safe for most systems)
export ROBOT_JAVA_ARGS="-Xmx16g"

# Moderate (for 64GB+ systems)
export ROBOT_JAVA_ARGS="-Xmx32g"

# Aggressive (for 1TB+ systems)
export ROBOT_JAVA_ARGS="-Xmx800g"
```

#### Advanced Java Options

```bash
# Full optimization for large datasets
export ROBOT_JAVA_ARGS="-Xmx800g \
  -XX:+UseG1GC \
  -XX:+UseStringDeduplication \
  -XX:MaxGCPauseMillis=200 \
  -XX:+UnlockExperimentalVMOptions \
  -XX:+UseCGroupMemoryLimitForHeap"
```

### Memory Guidelines by Dataset

| Dataset | System RAM | Java Heap | Concurrent Downloads |
|---------|-----------|-----------|---------------------|
| Test | 8GB | 4GB | 5 |
| Small | 32GB | 16GB | 10 |
| Medium | 128GB | 64GB | 15 |
| Large | 1TB+ | 800GB | 20 |

## Dataset Configuration

### Ontology Source Files

#### Core Ontologies (`config/ontologies_source.txt`)

```
# Format: ontology_id|url|description
bfo|http://purl.obolibrary.org/obo/bfo.owl|Basic Formal Ontology
iao|http://purl.obolibrary.org/obo/iao.owl|Information Artifact Ontology
uo|http://purl.obolibrary.org/obo/uo.owl|Units of Measurement Ontology
```

#### Test Ontologies (`config/ontologies_source_test.txt`)

```
# Curated subset for testing
bfo|http://purl.obolibrary.org/obo/bfo.owl|Basic Formal Ontology
iao|http://purl.obolibrary.org/obo/iao.owl|Information Artifact Ontology
uo|http://purl.obolibrary.org/obo/uo.owl|Units of Measurement Ontology
omo|http://purl.obolibrary.org/obo/omo.owl|OBO Metadata Ontology
ro-base|http://purl.obolibrary.org/obo/ro/ro-base.owl|Relations Ontology Base
pato-base|http://purl.obolibrary.org/obo/pato/pato-base.owl|Phenotype Ontology Base
cl-base|http://purl.obolibrary.org/obo/cl/cl-base.owl|Cell Ontology Base
envo|https://purl.obolibrary.org/obo/envo.owl|Environment Ontology
credit|https://w3id.org/biopragmatics/resources/credit/credit.owl|Credit Ontology
```

### Merge Configuration

#### Merge Groups (`config/ontologies_merged.txt`)

```
# Group 1: Core ontologies
core_merged.owl:bfo,iao,uo,omo

# Group 2: Biological processes
bio_merged.owl:go,chebi,pr

# Group 3: Phenotypes and anatomy
pheno_merged.owl:pato,uberon,cl
```

### Size Limits and Filters

#### Ontology Size Limits

```bash
# Skip ontologies larger than specified size
MAX_ONTOLOGY_SIZE_MB=5000

# Skip empty or corrupt files
MIN_ONTOLOGY_SIZE_KB=1
```

#### Content Filters

```bash
# Skip ontologies with specific patterns
SKIP_PATTERNS="deprecated,obsolete,test"

# Include only OBO Foundry ontologies
OBO_FOUNDRY_ONLY=true

# Filter by ontology prefix
INCLUDE_PREFIXES="GO,CHEBI,UBERON,CL"
EXCLUDE_PREFIXES="TEST,TEMP"
```

## Processing Configuration

### Download Settings

#### Network Configuration

```bash
# Connection settings
TIMEOUT_SECONDS=30              # Per-request timeout
MAX_RETRIES=3                   # Retry attempts
RETRY_DELAY_SECONDS=2           # Initial retry delay
EXPONENTIAL_BACKOFF=true        # Use exponential backoff

# Concurrent downloads
PARALLEL_DOWNLOADS=10           # Simultaneous downloads
RATE_LIMIT_REQUESTS_PER_SECOND=2  # Rate limiting
```

#### User Agent and Headers

```bash
# Custom user agent
USER_AGENT="CDM-Ontologies-Pipeline/1.0 (https://github.com/kbase/ontologies)"

# Additional headers
CUSTOM_HEADERS="Accept: application/rdf+xml,text/turtle;q=0.9"
```

### Version Tracking

#### Backup Settings

```bash
# Backup configuration
ENABLE_BACKUPS=true             # Create backups before updates
MAX_BACKUPS_PER_FILE=5          # Keep N backups per file
BACKUP_RETENTION_DAYS=30        # Delete backups older than N days
COMPRESS_BACKUPS=true           # Compress backup files
```

#### Checksum Settings

```bash
# Checksum algorithm (sha256 recommended)
CHECKSUM_ALGORITHM=sha256

# Verify checksums on startup
VERIFY_CHECKSUMS_ON_START=true

# Store checksums in separate file
SEPARATE_CHECKSUM_FILE=true
```

### Processing Options

#### ROBOT Configuration

```bash
# ROBOT processing options
ROBOT_REMOVE_IMPORTS=true       # Remove import statements
ROBOT_COLLAPSE_IMPORTS=true     # Collapse imported axioms
ROBOT_ANNOTATE_DERIVED=true     # Annotate derived axioms
ROBOT_STRICT_MODE=false         # Strict error handling
```

#### Reasoning Configuration

```bash
# Reasoning options
ENABLE_REASONING=true           # Perform reasoning
REASONER_TYPE=elk               # elk, hermit, pellet
REASONING_TIMEOUT_MINUTES=60    # Timeout for reasoning
MATERIALIZE_INFERENCES=true     # Include inferred axioms
```

### Database Configuration

#### SemanticSQL Settings

```bash
# Database creation options
CREATE_VIEWS=true               # Create materialized views
ENABLE_FULL_TEXT_SEARCH=true    # Enable FTS indexes
OPTIMIZE_DATABASE=true          # Run VACUUM and ANALYZE
DATABASE_JOURNAL_MODE=WAL       # WAL, DELETE, TRUNCATE
```

#### Export Settings

```bash
# Table export options
EXPORT_TSV=true                 # Export to TSV format
EXPORT_PARQUET=true             # Export to Parquet format
EXPORT_JSON=false               # Export to JSON format
TSV_DELIMITER="\t"              # TSV delimiter character
PARQUET_COMPRESSION=snappy      # Parquet compression
```

## Environment-Specific Configuration

### Test Environment

Create `.env.test`:

```bash
# Test Environment Configuration
ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt
DATASET_SIZE=test

# Memory (conservative for testing)
ROBOT_JAVA_ARGS=-Xmx4g
_JAVA_OPTIONS=-Xmx4g

# Processing (fast for testing)
PARALLEL_DOWNLOADS=5
ENABLE_REASONING=false
CREATE_VIEWS=false
EXPORT_PARQUET=false

# Logging (verbose for debugging)
LOG_LEVEL=DEBUG
ENABLE_DETAILED_LOGGING=true
```

### Small Production Environment

Create `.env.small`:

```bash
# Small Production Configuration
ONTOLOGIES_SOURCE_FILE=ontologies_source_small.txt
DATASET_SIZE=small

# Memory (moderate)
ROBOT_JAVA_ARGS=-Xmx16g
_JAVA_OPTIONS=-Xmx16g

# Processing (balanced)
PARALLEL_DOWNLOADS=10
ENABLE_REASONING=true
REASONING_TIMEOUT_MINUTES=30
CREATE_VIEWS=true
EXPORT_PARQUET=true

# Logging (production level)
LOG_LEVEL=INFO
ENABLE_DETAILED_LOGGING=false
```

### Large Production Environment

Create `.env.large`:

```bash
# Large Production Configuration
ONTOLOGIES_SOURCE_FILE=config/ontologies_source.txt
DATASET_SIZE=large

# Memory (aggressive)
ROBOT_JAVA_ARGS=-Xmx800g -XX:+UseG1GC -XX:+UseStringDeduplication
_JAVA_OPTIONS=-Xmx800g

# Processing (optimized for throughput)
PARALLEL_DOWNLOADS=20
BATCH_SIZE=200
ENABLE_REASONING=true
REASONING_TIMEOUT_MINUTES=120
MATERIALIZE_INFERENCES=true

# Database (full optimization)
CREATE_VIEWS=true
ENABLE_FULL_TEXT_SEARCH=true
OPTIMIZE_DATABASE=true
EXPORT_PARQUET=true
PARQUET_COMPRESSION=snappy

# Logging (minimal overhead)
LOG_LEVEL=WARN
ENABLE_DETAILED_LOGGING=false
```

## Docker Configuration

### Docker Environment Variables

```yaml
services:
  pipeline:
    environment:
      # Load from file
      - ENV_FILE=.env.large
      
      # Or specify directly
      - ROBOT_JAVA_ARGS=-Xmx800g
      - PARALLEL_DOWNLOADS=20
      - LOG_LEVEL=INFO
```

### Docker Compose Overrides

Create `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  pipeline:
    environment:
      - CUSTOM_CONFIG=production
    deploy:
      resources:
        limits:
          memory: 1200G
        reservations:
          memory: 1000G
    volumes:
      - /fast/ssd:/workspace/temp
      - /large/disk:/workspace/outputs
```

## Kubernetes Configuration

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cdm-ontologies-config
data:
  ROBOT_JAVA_ARGS: "-Xmx800g"
  PARALLEL_DOWNLOADS: "20"
  LOG_LEVEL: "INFO"
  DATASET_SIZE: "large"
```

### Resource Limits

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: cdm-ontologies-pipeline
spec:
  template:
    spec:
      containers:
      - name: pipeline
        resources:
          requests:
            memory: "1000Gi"
            cpu: "8"
          limits:
            memory: "1200Gi"
            cpu: "16"
        env:
        - name: ROBOT_JAVA_ARGS
          valueFrom:
            configMapKeyRef:
              name: cdm-ontologies-config
              key: ROBOT_JAVA_ARGS
```

## Advanced Configuration

### Custom Processing Scripts

#### Custom Download Logic

```python
# custom_download.py
def custom_download_handler(url, output_path):
    """Custom download logic for specific sources"""
    if 'special-source.org' in url:
        # Implement custom authentication/processing
        return download_with_auth(url, output_path)
    else:
        # Use default download
        return default_download(url, output_path)
```

#### Custom Validation Rules

```python
# custom_validation.py
def custom_validation_rules(ontology_file):
    """Custom validation for specific ontologies"""
    ontology_id = get_ontology_id(ontology_file)
    
    if ontology_id == 'custom_ontology':
        # Apply custom validation rules
        return validate_custom_ontology(ontology_file)
    
    return default_validation(ontology_file)
```

### Plugin System

#### Loading Custom Plugins

```bash
# Enable plugin system
ENABLE_PLUGINS=true
PLUGIN_DIRECTORY=./plugins

# Load specific plugins
PLUGINS=custom_download,custom_validation,custom_export
```

#### Plugin Configuration

```python
# plugins/custom_export.py
class CustomExportPlugin:
    def __init__(self, config):
        self.config = config
    
    def export_data(self, database_path, output_dir):
        # Implement custom export logic
        pass
```

## Configuration Validation

### Validation Script

```bash
# Validate configuration before running
python scripts/validate_config.py --env-file .env.large

# Check system requirements
python scripts/check_requirements.py --dataset large
```

### Configuration Templates

Create configuration from templates:

```bash
# Generate configuration for system
python scripts/generate_config.py \
  --memory $(free -g | awk 'NR==2{print $2}')G \
  --dataset large \
  --output .env.custom
```

This comprehensive configuration guide covers all aspects of customizing the CDM Ontologies Pipeline for different environments and use cases. Start with the predefined environment files and customize as needed for your specific requirements.