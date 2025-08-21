# Getting Started with CDM Ontologies Pipeline

This guide will walk you through setting up and running the CDM Ontologies Pipeline from scratch.

## Prerequisites

### Option 1: Docker (Recommended)
- Docker Engine 20.10+
- Docker Compose v2.0+
- 1.5TB+ available RAM for container allocation

### Option 2: Native Installation
- Python 3.10+
- Java 17+ (for ROBOT and relation-graph)
- Make
- 1.5TB+ RAM minimum

## Quick Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd KBase_CDM_Ontologies
```

### 2. Choose Your Installation Method

#### Docker Installation (Recommended)

```bash
# Build the container
make docker-build

# Run test pipeline (RECOMMENDED FIRST STEP)
# Processes 6 example ontologies in ~5 minutes
make docker-test

# Run production pipeline (32 ontologies)
make docker-run-prod
```

The test run is **strongly recommended** as your first step. It demonstrates the complete 7-step pipeline using a small dataset and creates example outputs in `outputs_test/` that show exactly what to expect from the full production run.

#### Native Installation

```bash
# Install Python dependencies
make install

# Setup directories
make setup

# Note: ROBOT and relation-graph need manual installation for native setup
# See DEPLOYMENT.md for detailed instructions
```

## Your First Test Run

### Step 1: Understanding the Test Environment

The pipeline includes a curated test dataset with 6 ontologies:

```bash
# View the test ontologies
cat config/ontologies_source_test.txt

# See available commands
make help
```

### Step 2: Run a Single Step

```bash
# Download and analyze test ontologies
make test-analyze-core

# Check version tracking
python scripts/version_manager.py status
```

### Step 3: Run Complete Test Workflow

```bash
# Run all pipeline steps with test data
make test-workflow

# Check final status
python scripts/version_manager.py status
```

## Understanding the Output

### Directory Structure After Test Run

```
KBase_CDM_Ontologies/
├── ontology_data_owl_test/          # Downloaded test ontologies
│   ├── bfo-base.owl                 # Basic Formal Ontology
│   ├── iao-base.owl                 # Information Artifact Ontology
│   ├── non-base-ontologies/
│   │   ├── envo.owl                 # Environmental Ontology
│   │   └── credit.owl               # Contributor Role Taxonomy
│   └── ...                          # Other test ontologies
├── outputs_test/                    # Pipeline outputs
│   └── run_YYYYMMDD_HHMMSS/        # Timestamped run directory
│       ├── core_ontologies_analysis.json    # Metadata catalog
│       ├── CDM_merged_ontologies.owl        # Unified ontology file
│       ├── CDM_merged_ontologies.db         # SQLite database
│       ├── tsv_tables/              # Exported database tables
│       └── parquet_files/           # Compressed data files
├── ontology_versions_test/          # Version tracking
│   ├── ontology_versions.json       # Version registry
│   ├── download_history.log         # Audit trail
│   └── backups/                     # Previous versions
└── logs/                            # Execution logs
    └── cdm_ontologies_test_YYYYMMDD_HHMMSS.log
```

### Key Output Files

- **`core_ontologies_analysis.json`**: Metadata about downloaded ontologies
- **`CDM_merged_ontologies.owl`**: Unified ontology in OWL format (14.7MB for test)
- **`CDM_merged_ontologies.db`**: SQLite database for queries (85.5MB for test)
- **`tsv_tables/`**: Exported data tables (17 files)
- **`parquet_files/`**: Compressed exports (89.6% compression)

## Version Tracking System

### Check What Was Downloaded

```bash
# Show current status
python version_manager.py status

# Generate detailed report
python version_manager.py report
```

### Run Pipeline Again

```bash
# Run the same command again
make test-analyze-core

# Notice: All files will be skipped (no changes detected)
# Check the logs to see "✅ No changes detected" messages
```

## Moving to Production

### Small Dataset (Development)

```bash
# Use small configuration
ENV_FILE=.env.small make run-workflow
```

### Large Dataset (Production)

```bash
# Use production configuration (requires 1.5TB+ RAM)
make docker-run-prod

# Or run in background with nohup
make docker-run-prod-nohup

# Monitor progress
make docker-prod-status
```

## Common Workflows

### Development Workflow

```bash
# 1. Make code changes
# 2. Test with small dataset
make test-workflow

# 3. Validate changes
python test_validation.py all

# 4. Run with different configurations
ENV_FILE=.env.small make run-workflow
```

### Production Deployment

```bash
# 1. Build production container
make docker-build

# 2. Deploy with appropriate resources
make docker-run-large

# 3. Monitor logs
tail -f logs/cdm_ontologies.log
```

## Troubleshooting

### Out of Memory

```bash
# Increase Java heap size
export ROBOT_JAVA_ARGS="-Xmx32g"

# Or use smaller dataset
ENV_FILE=.env.small make run-workflow
```

### Network Issues

The pipeline automatically retries downloads with exponential backoff. Check the history:

```bash
python version_manager.py history
```

### Validation Failures

```bash
# Run specific validation step
python test_validation.py 1

# Check detailed logs
tail -f logs/cdm_ontologies.log
```

## Next Steps

- Read [VERSION_TRACKING.md](VERSION_TRACKING.md) to understand version management
- See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [CONFIGURATION.md](CONFIGURATION.md) for advanced options
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

## Getting Help

- **Issues**: Report bugs on GitHub
- **Logs**: Check `logs/cdm_ontologies.log`
- **Validation**: Use `python test_validation.py all`
- **Versions**: Use `python version_manager.py status`