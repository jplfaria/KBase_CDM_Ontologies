# KBase CDM Ontologies Pipeline

A containerized pipeline for processing and merging biological ontologies at scale with comprehensive version tracking and multi-environment support.

## Repository Locations

This repository is maintained in two locations:
- **Personal Development**: [jplfaria/KBase_CDM_Ontologies](https://github.com/jplfaria/KBase_CDM_Ontologies)
- **KBase Organization**: [kbaseincubator/KBase_CDM_Ontologies](https://github.com/kbaseincubator/KBase_CDM_Ontologies)

Both repositories are kept in sync and contain identical content.

## Overview

This pipeline processes biological ontologies from sources like OBO Foundry, Gene Ontology, CHEBI, and others, creating unified knowledge bases for computational analysis. It transforms heterogeneous ontology formats into structured databases while maintaining provenance and version control.

**Key Features:**
- Processes 30+ major biological ontologies
- Handles datasets requiring >1TB RAM for production workloads
- Creates semantic SQL databases for efficient querying
- Exports to multiple formats (OWL, SQLite, TSV, Parquet)
- Comprehensive version tracking with SHA256 checksums
- Docker-based deployment with all dependencies included
- Timestamped output folders preserve results from each run
- Detailed run summaries capture all workflow activities and metrics

## Quick Start

### Test Mode (Recommended First Step)

```bash
# Build and run with test dataset (6 ontologies)
make docker-build
make docker-test

# Run test in background with nohup (for long processes)
make docker-test-nohup
# Creates timestamped log: logs/nohup_cdm_test_YYYYMMDD_HHMMSS.out

# Monitor progress of background test run
make docker-test-status
```

### Production Mode

```bash
# Requires 1.5TB+ available RAM
make docker-run-prod

# Run in background with nohup (for long-running processes)
make docker-run-prod-nohup
# Creates timestamped log: logs/nohup_cdm_prod_YYYYMMDD_HHMMSS.out

# Monitor progress of background run
make docker-prod-status
```

## Installation

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- 1.5TB+ available RAM for container allocation

### Setup

```bash
git clone https://github.com/jplfaria/KBase_CDM_Ontologies.git
cd KBase_CDM_Ontologies
make docker-build
```

## Pipeline Architecture

The pipeline consists of 7 sequential steps:

1. **Analyze Core Ontologies** - Downloads and processes primary ontologies
2. **Analyze Non-Core Ontologies** - Processes additional OBO ontologies  
3. **Create Pseudo Base Ontologies** - Creates base versions using ROBOT
4. **Merge Ontologies** - Combines all ontologies using ROBOT
5. **Create Semantic SQL Database** - Converts to queryable SQLite format
6. **Extract Tables to TSV** - Exports database tables to TSV format
7. **Create Parquet Files** - Compresses data to efficient Parquet format

## Run Summary Feature

Every pipeline run generates a comprehensive summary report that captures all important information about the workflow execution. This feature provides visibility into what happened during processing without reviewing full logs.

### Summary Contents

The run summary includes:
- **Execution Details**: Run ID, timestamps, duration, and final status
- **System Resources**: Memory and disk usage throughout the run
- **Ontology Downloads**: New downloads, updates, skipped files, and failures
- **Version Changes**: Files updated with old/new checksums and backup details
- **Pipeline Steps**: Timing and status for each of the 7 workflow steps
- **Processing Results**: Database statistics, file counts, compression ratios
- **Output Files**: All generated files with sizes and locations
- **Issues Encountered**: Warnings and errors during processing

### Output Formats

Each run generates two summary files in the output directory:
- `run_summary_YYYYMMDD_HHMMSS.txt` - Human-readable text format
- `run_summary_YYYYMMDD_HHMMSS.json` - Machine-readable JSON for programmatic access

### Example Summary

```
CDM Ontologies Pipeline Run Summary
======================================================================
Run ID: run_20250707_154322
Start Time: 2025-07-07 15:43:22
End Time: 2025-07-07 15:43:44
Duration: 22s
Status: SUCCESS
Mode: TEST

System Resources:
- Initial Memory: 21.3GB available / 64.0GB total
- Peak Memory Usage: 8.5GB (13.3% of system)
- Initial Disk: 1103.2GB available
- Final Disk: 1102.1GB available
- Disk Used: 1.1GB

Ontology Downloads:
- Total Ontologies Processed: 6
- New Downloads: 2
  • ro-base.owl (2.1MB)
  • pato-base.owl (8.3MB)
- Updated: 1
  • envo.owl (15.2MB)
- Skipped (Up-to-date): 3
- Failed Downloads: 0

Pipeline Steps:
✓ Step 1: Analyze Core Ontologies (5s)
✓ Step 2: Analyze Non-Core Ontologies (3s)
✓ Step 3: Create Pseudo Base Ontologies (2s)
✓ Step 4: Merge Ontologies (7s)
✓ Step 5: Create Semantic SQL Database (3s)
✓ Step 6: Extract SQL Tables to TSV (1s)
✓ Step 7: Create Parquet Files (1s)

Processing Results:
- total_ontologies_to_merge: 6
- database_size_gb: 0.08
- database_tables: 17
- database_total_rows: 435,892
- tsv_tables_exported: 17
- tsv_total_size_gb: 0.12
- parquet_files_created: 17
- parquet_total_size_gb: 0.01
- compression_ratio: 91.7%
- space_saved_gb: 0.11

Output Files:
- merged_ontology: CDM_merged_ontologies.owl (0.01GB)
- semantic_sql_db: CDM_merged_ontologies.db (0.08GB)
- tsv_tables: tsv_tables/ (0.12GB)
- parquet_files: parquet_files/ (0.01GB)
```

## KBase CDM Initial Release Ontologies

The production dataset (`config/ontologies_source.txt`) includes 32 ontologies across multiple categories:

### Core Closure Ontologies (Non-Base)
- **BFO** (Basic Formal Ontology) - Foundational upper-level ontology
- **FOODON** - Food ontology for agricultural and nutritional data
- **IAO** (Information Artifact Ontology) - Information and data artifacts
- **OMO** (OBO Metadata Ontology) - Metadata and annotation standards
- **OMP** (Ontology of Microbial Phenotypes) - Microbial characteristics and behaviors
- **PO** (Plant Ontology) - Plant anatomy and developmental stages

### Core Closure Ontologies (Base Versions)
- **ECO-base** (Evidence and Conclusion Ontology) - Scientific evidence types
- **FAO-base** - Food and Agriculture Organization terms
- **OBI-base** (Ontology for Biomedical Investigations) - Experimental protocols
- **PATO-base** (Phenotype and Trait Ontology) - Observable characteristics
- **PCO-base** (Population and Community Ontology) - Population studies
- **RO-base** (Relations Ontology) - Standardized relationships
- **UBERON-base** - Cross-species anatomy ontology

### OBO Foundry Ontologies
- **ENVO** - Environmental conditions and exposures
- **GO** (Gene Ontology) - Gene and protein functions
- **NCBI Taxon** - Taxonomic classifications (>2M organisms)
- **ChEBI** - Chemical entities of biological interest
- **UO** (Units of Measurement Ontology) - Standardized units
- **TAXRANK** - Taxonomic ranks and hierarchies
- **SO** (Sequence Ontology) - Genomic and proteomic features

### PyOBO Controlled Vocabularies
- **GTDB** - Genome Taxonomy Database classifications
- **EC codes** - Enzyme Commission functional classifications
- **Pfam** - Protein family domains and motifs
- **Rhea** - Biochemical reactions and pathways
- **Credit** - Contributor role taxonomy
- **ROR** (Research Organization Registry) - Institutional affiliations
- **InterPro** - Protein sequence analysis and classification

### In-House Ontologies
- **SEED** - Subsystems and functional roles
- **MetaCyc** - Metabolic pathways and enzymes
- **KEGG** - Kyoto Encyclopedia pathway data
- **ModelSEED** - Metabolic modeling compounds and reactions

## Configuration

### Test Run Example (6 ontologies)

The test dataset (`config/ontologies_source_test.txt`) provides a complete example of what users can expect from the full production run. It processes 6 representative ontologies:

- **BFO, IAO** - Core foundational ontologies
- **RO-base, PATO-base** - Essential relationships and phenotypes  
- **ENVO** - Environmental ontology (moderate size)
- **Credit** - Small controlled vocabulary

**Test Pipeline Results** (see `outputs_test/` directory):

1. **Ontology Analysis** → `core_ontologies_analysis.json`, `non_core_ontologies_analysis.json`
2. **Downloaded Ontologies** → `ontology_data_owl_test/` (6 OWL files)
3. **Base Ontologies** → `bfo-base.owl`, `iao-base.owl` (external axioms removed)
4. **Merged Ontology** → `CDM_merged_ontologies.owl` (unified knowledge base)
5. **SQLite Database** → `CDM_merged_ontologies.db` (85.5MB, 18 tables, 430K+ edges)
6. **TSV Tables** → `tsv_tables/` (17 files, 27.7MB total)
7. **Parquet Files** → `parquet_files/` (18 files, 2.9MB, 89.6% compression)

**Memory Monitoring** → `utils/` (detailed logs for ROBOT, SemsQL operations)

**Execution Time:** ~5 minutes (demonstrates full pipeline efficiency)

### Production Dataset (31 ontologies)

The production run follows the same 7-step process but with the complete KBase CDM ontology collection, creating a comprehensive biological knowledge base suitable for systems biology research.

- **Processing time:** Hours to days (depending on system resources)
- **Memory allocation:** 1.5TB container limits
- **Output location:** `outputs/` (git-ignored, user-generated)
- **Database size:** Expected 10GB+ with millions of integrated terms

## Custom Prefixes

The pipeline includes custom URI prefixes for biological databases that are not part of the standard SemsQL distribution. These prefixes are essential for properly handling URIs from KEGG, SEED, MetaCyc, and Reactome in the merged ontology.

### Custom Prefix Configuration

**Location:** `semsql_custom_prefixes/custom_prefixes.csv`

**Included Prefixes:**
- **KEGG** - Kyoto Encyclopedia reactions and pathways
- **SEED** - Model SEED compounds and reactions  
- **MetaCyc** - Metabolic pathways and reactions
- **Reactome** - Biological pathway database

### ⚠️ Important: Docker Rebuild Required

**When modifying `custom_prefixes.csv`, you MUST rebuild the Docker container:**

```bash
# After editing custom_prefixes.csv
make docker-build

# Then run your pipeline
make docker-run-prod
```

The custom prefixes are integrated during the Docker build process and appended to SemsQL's main prefix file. This ensures all generated databases include the proper namespace mappings for these biological resources.

## Output Structure

The pipeline creates timestamped output directories for each run, preserving results and enabling comparison across runs. The timestamp format is `YYYYMMDD_HHMMSS`.

### Example Test Output (Included in Repository)

This repository includes a complete example test run in `outputs_test/run_20250704_001300/` and corresponding logs in `logs/` to demonstrate the pipeline's output structure and expected results.

```
outputs_test/                               # Test run results (example included)
├── run_20250704_001300/                   # Example timestamped test run
│   ├── CDM_merged_ontologies.owl          # Merged ontology (14.7MB)
│   ├── CDM_merged_ontologies.db           # SQLite database (85.5MB)
│   ├── CDM_merged_ontologies-relation-graph.tsv.gz  # Relationship graph
│   ├── core_ontologies_analysis.json      # Step 1: Core analysis results
│   ├── non_core_ontologies_analysis.json  # Step 2: Non-core analysis
│   ├── core_onto_unique_external_*.tsv    # External term mappings
│   ├── run_summary_20250704_001300.txt    # Human-readable run summary
│   ├── run_summary_20250704_001300.json   # Machine-readable run summary
│   ├── tsv_tables/                         # Step 6: Database exports (17 files)
│   │   ├── entailed_edge.tsv              # 430K+ relationships
│   │   ├── statements.tsv                 # 162K+ RDF statements  
│   │   ├── prefix.tsv                     # 1,207 namespace prefixes
│   │   └── ... (14 more tables)
│   ├── parquet_files/                      # Step 7: Compressed exports (18 files)
│   │   ├── entailed_edge.parquet          # Efficient relationship storage
│   │   ├── statements.parquet             # Compressed RDF statements
│   │   └── ... (16 more files, 89.6% compression)
│   └── utils/                              # Memory monitoring logs
│       ├── ROBOT_merge_memory_summary.txt # ROBOT performance stats
│       ├── SemsQL_make_memory_summary.txt # Database creation stats
│       └── ... (detailed monitoring files)
└── latest/                                 # Symlink to most recent test run
```

### Production Outputs (User-Generated)
```
outputs/                                   # Production results (git-ignored)
├── run_YYYYMMDD_HHMMSS/                 # Timestamped run folder
│   ├── CDM_merged_ontologies.owl         # Complete 32 ontology merge
│   ├── CDM_merged_ontologies.db          # Full production database (10GB+)
│   ├── run_summary_YYYYMMDD_HHMMSS.txt  # Human-readable run summary
│   ├── run_summary_YYYYMMDD_HHMMSS.json # Machine-readable run summary
│   ├── tsv_tables/                       # All database tables
│   ├── parquet_files/                    # Compressed data exports
│   └── utils/                            # Production monitoring logs
└── latest/                               # Symlink to most recent run
```

### Logging System

All pipeline runs generate comprehensive logs with timestamps matching the output directories:

```
logs/                                      # All pipeline logs
├── cdm_ontologies_test_20250704_001300.log    # Example test workflow log
├── nohup_cdm_test_20250704_001300.out        # Example nohup wrapper log
├── cdm_ontologies_prod_YYYYMMDD_HHMMSS.log    # Production workflow logs
└── nohup_cdm_prod_YYYYMMDD_HHMMSS.out        # Production nohup logs

ontology_data_owl_test/                   # Example test ontologies (included)
├── bfo-base.owl                          # Basic Formal Ontology
├── iao-base.owl                          # Information Artifact Ontology
├── ro-base.owl                           # Relations Ontology
├── pato-base.owl                         # Phenotype and Trait Ontology
└── non-base-ontologies/
    ├── envo.owl                          # Environmental Ontology
    └── credit.owl                        # Contributor Role Taxonomy

ontology_versions/                        # Version tracking and backups
├── ontology_versions.json               # SHA256 checksums and metadata
└── backups/                              # Previous versions
```

## Project Files

### Core Scripts
- **`Makefile`** - Primary command interface for all operations
- **`requirements.txt`** - Python dependencies

### Docker Files
- **`docker-compose.yml`** - Docker orchestration configuration
- **`Dockerfile`** - Container build instructions with all dependencies
- **`docker-entrypoint.sh`** - Dynamic user handling in containers

### Configuration
All configuration files are located in the `config/` directory:
- **`ontologies_source.txt`** - List of production ontologies to process (31 ontologies)
- **`ontologies_source_test.txt`** - Smaller list for testing (6 ontologies)
- **`prefix_mapping.txt`** - URI prefix mappings for ontologies
- **`.env`** - Production environment configuration (not in git)
- **`.env.test`** - Test environment configuration (not in git)

### Utility Scripts
- **`clean_run.sh`** - Removes all outputs for a fresh pipeline run
  - Cleans: ontology data, outputs, version tracking, logs, and cache
  - Usage: `./clean_run.sh` before starting a new complete run
- **`fix-permissions.sh`** - Fixes Docker-created file permissions
- **`run_tests.sh`** - Runs unit test suite with pytest
  - Generates coverage reports in `htmlcov/`
  - Requires: `pip install pytest pytest-cov pytest-mock`

### Custom Prefixes
- **`semsql_custom_prefixes/`** - Custom URI prefix management
  - `custom_prefixes.csv` - KEGG, SEED, MetaCyc, Reactome prefixes
  - `README.md` - Documentation for custom prefix usage

## Memory Requirements

All environments use unified memory settings (1.5TB container limits):

| Mode | Ontologies | Container Memory | Processing Time |
|------|------------|------------------|-----------------|
| Test | 6 | 1.5TB | ~10 minutes |
| Production | 32 | 1.5TB | 24+ hours |

## Documentation

- [Getting Started Guide](docs/GETTING_STARTED.md)
- [Pipeline Architecture](docs/PIPELINE_ARCHITECTURE.md)
- [Configuration Options](docs/CONFIGURATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## CLI Usage

```bash
# Run complete workflow
python -m cdm_ontologies run-all

# Run individual steps
python -m cdm_ontologies analyze-core
python -m cdm_ontologies analyze-non-core
python -m cdm_ontologies create-base
python -m cdm_ontologies merge
python -m cdm_ontologies create-db
python -m cdm_ontologies extract-tables
python -m cdm_ontologies create-parquet

# Version management
python scripts/version_manager.py status
python scripts/version_manager.py history
```

## External Tools

The Docker container includes all required tools:
- **ROBOT v1.9.8** - Ontology manipulation
- **relation-graph v2.3.2** - Relationship inference
- **SemanticSQL** - OWL to SQL conversion

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests with `make docker-test`
4. Submit a pull request

## License

This project is licensed under the MIT License - see [LICENSE.txt](LICENSE.txt) for details.

## Support

- Issues: [GitHub Issues](https://github.com/jplfaria/KBase_CDM_Ontologies/issues)
- Documentation: [docs/](docs/)

## Acknowledgments

This pipeline processes ontologies from:
- [OBO Foundry](http://obofoundry.org/)
- [Gene Ontology](http://geneontology.org/)
- [ChEBI](https://www.ebi.ac.uk/chebi/)
- [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy)
- And many other biological ontology providers