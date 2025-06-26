# Ontology Order Testing Framework

This directory contains testing infrastructure to investigate how ontology ordering affects ROBOT merge behavior, particularly with the `--annotate-defined-by` flag.

## Background

ROBOT's merge command can produce different results depending on the order of input ontologies:

1. **`--annotate-defined-by` behavior**: When multiple ontologies define the same term, the first occurrence is typically marked as the "defining" ontology
2. **Conflicting annotations**: Different order can affect which annotations are preserved/prioritized
3. **Memory efficiency**: Order can impact memory usage patterns during merge

## Test Setup

### Branches
- **`dev`**: Main development branch (stable)
- **`order_testing`**: Experimental branch for ontology ordering tests

### Directory Structure
```
ontology_order_testing/
├── README.md                    # This file
├── docker-run.sh                # Self-contained Docker execution
├── ontologies_source_full.txt   # Full dataset (23 ontologies)
├── test_merge_orders.py         # Main testing script
├── compare_merges.py            # Merge comparison utilities
├── analyze_annotations.py       # Annotation analysis tools
├── data/                        # Downloaded ontologies (gitignored)
├── results/                     # Test outputs (gitignored)
├── local_env/
│   └── .env.local              # Local environment configuration
├── scripts/
│   ├── download_ontologies.py  # Self-contained downloader
│   └── create_pseudo_base_local.py # Local pseudo-base creator
└── configs/
    ├── order_alphabetical.txt   # Alphabetical order (23 ontologies)
    ├── order_hierarchy.txt      # Foundational → domain → reference  
    └── order_size.txt          # Size-based ordering
```

## Test Cases

### 1. Alphabetical Order (Current Default)
Standard filesystem order, currently used by the pipeline. **23 ontologies** in alphabetical order.

### 2. Hierarchical Order (Recommended)
**23 ontologies** ordered by ontological dependency:
```
1. Upper-level ontologies (BFO, RO)
2. Mid-level foundational (IAO, OMO, PATO)
3. Anatomical/structural (UBERON, PCO)
4. Domain-specific base versions (OBI, FAO, PO, FOODON)
5. Large reference ontologies (GO, CHEBI, ENVO)
6. Specialized domains (SO, UO, TAXRANK)
7. External vocabularies (ECCODE, RHEA, PFAM, INTERPRO, GTDB, ROR)
8. Metadata (CRediT)
```

### 3. Size-Based Order
**23 ontologies** ordered by expected file size (largest first):
- GO (~500MB) and CHEBI (~200MB) first
- Medium ontologies (UBERON, OBI, ENVO)
- Small ontologies and vocabularies last

## Dataset

**Full realistic dataset**: 23 ontologies from production pipeline
- **Included**: All from config/ontologies_source.txt except NCBITaxon and in-house ontologies
- **Excluded**: NCBITaxon (too large), seed/metacyc/kegg/modelseed (in-house)
- **Processing**: Non-base ontologies converted to pseudo-base versions locally

## Self-Contained Execution

All operations are contained within `ontology_order_testing/` directory:

```bash
# Complete workflow (download, create base versions, test orders, analyze)
./ontology_order_testing/docker-run.sh all

# Individual steps
./ontology_order_testing/docker-run.sh download        # Download 23 ontologies
./ontology_order_testing/docker-run.sh pseudo-base     # Create pseudo-base versions  
./ontology_order_testing/docker-run.sh test-orders     # Test merge orders
./ontology_order_testing/docker-run.sh compare         # Compare results
./ontology_order_testing/docker-run.sh analyze         # Analyze annotations

# Interactive debugging
./ontology_order_testing/docker-run.sh shell
```

## Expected Outcomes

1. **Annotation consistency**: Foundational ontologies should be marked as definers for shared terms
2. **Memory efficiency**: Optimal order may reduce peak memory usage
3. **Reproducibility**: Consistent ordering across different filesystems/environments
4. **Debugging**: Easier to track term attribution and conflicts

## Integration Path

Successful testing may lead to:
1. Modified `merge_ontologies.py` with configurable ordering
2. Recommended default order in main pipeline
3. Documentation of ordering rationale

## Getting Started on a New Machine

When checking out this branch on a larger machine, users will need to:

1. **Download all 23 ontologies** (approx. 1.6GB total):
   ```bash
   ./ontology_order_testing/docker-run.sh download
   ```

2. **Create pseudo-base versions** for non-base ontologies:
   ```bash
   ./ontology_order_testing/docker-run.sh pseudo-base
   ```

3. **Run the full testing workflow**:
   ```bash
   ./ontology_order_testing/docker-run.sh all
   ```

This will:
- Test three different merge orders (alphabetical, hierarchical, size-based)
- Compare the results to identify differences
- Analyze term annotations to see how ordering affects attribution

**Note**: The large ontology files (CHEBI ~783MB, GO ~121MB) require significant memory. Ensure your machine has at least 128GB RAM available for Docker.