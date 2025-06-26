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
├── test_merge_orders.py         # Main testing script
├── compare_merges.py            # Merge comparison utilities
├── analyze_annotations.py       # Annotation analysis tools
├── configs/
│   ├── order_alphabetical.txt   # Current default (alphabetical)
│   ├── order_hierarchy.txt      # Foundational → domain → reference
│   └── order_size.txt          # Size-based ordering
└── results/                    # Test outputs (gitignored)
```

## Test Cases

### 1. Alphabetical Order (Current Default)
Standard filesystem order, currently used by the pipeline.

### 2. Hierarchical Order (Recommended)
```
1. Upper-level ontologies (BFO, RO)
2. Mid-level foundational (IAO, OMO, PATO, CARO)
3. Domain-specific base versions (UBERON, CL, PO, etc.)
4. Large reference ontologies (CHEBI, GO, ENVO)
5. Application ontologies (FOODON, SO, UO)
6. External vocabularies (ECCODE, RHEA, etc.)
7. In-house ontologies (last)
```

### 3. Size-Based Order
Largest ontologies first to optimize memory usage.

## Exclusions for Local Testing

To make testing manageable locally, we exclude:
- **NCBITaxon**: Too large for local testing
- **Very large ontologies**: Focus on representative subset

## Docker Execution

All tests must be run via Docker using the existing containerized environment:

```bash
# Run specific order test
docker-compose -f docker-compose.yml run cdm-ontologies python ontology_order_testing/test_merge_orders.py

# Compare merge results
docker-compose -f docker-compose.yml run cdm-ontologies python ontology_order_testing/compare_merges.py
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