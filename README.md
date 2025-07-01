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

## Quick Start

### Test Mode (Recommended First Step)

```bash
# Build and run with test dataset (6 ontologies)
make docker-build
make docker-test

# Run test in background with nohup (for long processes)
make docker-test-nohup

# Monitor progress of background test run
make docker-test-status
```

### Production Mode

```bash
# Requires 1.5TB+ available RAM
make docker-run-prod

# Run in background with nohup (for long-running processes)
make docker-run-prod-nohup

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

## KBase CDM Initial Release Ontologies

The production dataset (`config/ontologies_source.txt`) includes 30+ ontologies across multiple categories:

### Core Closure Ontologies (Non-Base)
- **BFO** (Basic Formal Ontology) - Foundational upper-level ontology
- **FOODON** - Food ontology for agricultural and nutritional data
- **IAO** (Information Artifact Ontology) - Information and data artifacts
- **OMO** (OBO Metadata Ontology) - Metadata and annotation standards
- **PO** (Plant Ontology) - Plant anatomy and developmental stages

### Core Closure Ontologies (Base Versions)
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

### Production Dataset (30+ ontologies)

The production run follows the same 7-step process but with the complete KBase CDM ontology collection, creating a comprehensive biological knowledge base suitable for systems biology research.

- **Processing time:** Hours to days (depending on system resources)
- **Memory allocation:** 1.5TB container limits
- **Output location:** `outputs/` (git-ignored, user-generated)
- **Database size:** Expected 10GB+ with millions of integrated terms

## Output Structure

### Test Outputs (Included as Examples)
```
outputs_test/                               # Complete test run results
├── CDM_merged_ontologies.owl              # Merged ontology (all 6 ontologies)
├── CDM_merged_ontologies.db               # SQLite database (85.5MB)
├── CDM_merged_ontologies-relation-graph.tsv.gz  # Relationship graph
├── core_ontologies_analysis.json         # Step 1: Core analysis results
├── non_core_ontologies_analysis.json     # Step 2: Non-core analysis
├── core_onto_unique_external_*.tsv       # External term mappings
├── tsv_tables/                            # Step 6: Database exports (17 files)
│   ├── entailed_edge.tsv                 # 430K+ relationships
│   ├── statements.tsv                    # 162K+ RDF statements  
│   ├── prefix.tsv                        # 1,207 namespace prefixes
│   └── ... (14 more tables)
├── parquet_files/                         # Step 7: Compressed exports (18 files)
│   ├── entailed_edge.parquet             # Efficient relationship storage
│   ├── statements.parquet                # Compressed RDF statements
│   └── ... (16 more files, 89.6% compression)
└── utils/                                 # Memory monitoring logs
    ├── ROBOT_merge_memory_summary.txt    # ROBOT performance stats
    ├── SemsQL_make_memory_summary.txt    # Database creation stats
    └── ... (detailed monitoring files)
```

### Production Outputs (User-Generated)
```
outputs/                                   # Production results (git-ignored)
├── CDM_merged_ontologies.owl             # Complete 30+ ontology merge
├── CDM_merged_ontologies.db              # Full production database (10GB+)
├── tsv_tables/                           # All database tables
├── parquet_files/                        # Compressed data exports
└── utils/                                # Production monitoring logs

ontology_data_owl/                        # Downloaded and processed ontologies
├── *.owl                                 # Individual ontology files
└── non-base-ontologies/                  # Unprocessed versions

ontology_versions/                        # Version tracking and backups
├── ontology_versions.json               # SHA256 checksums and metadata
└── backups/                              # Previous versions
```

## Memory Requirements

All environments use unified memory settings (1.5TB container limits):

| Mode | Ontologies | Container Memory | Processing Time |
|------|------------|------------------|-----------------|
| Test | 6 | 1.5TB | ~10 minutes |
| Production | 30+ | 1.5TB | 24+ hours |

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