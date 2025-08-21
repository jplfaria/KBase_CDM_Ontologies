# SemsQL Custom Prefixes

## Purpose

This directory contains custom prefixes that are added to SemsQL during the Docker build process. These prefixes are essential for properly handling URIs from various biological databases in our merged ontology, which combines 32 different ontologies from OBO Foundry, PyOBO, and in-house sources.

## Custom Prefixes

The `custom_prefixes.csv` file contains the following 10 custom prefix mappings:

- **KEGG** (Kyoto Encyclopedia of Genes and Genomes)
  - `kegg.reaction` → `http://www.kegg.jp/entry/` - Direct KEGG reaction entries
  - `kegg.reaction` → `http://www.kegg.jp/find/reaction/` - KEGG reaction search
  - `kegg.pathway` → `https://rest.kegg.jp/find/pathway/` - KEGG pathway search API

- **SEED** (Model SEED Database)
  - `seed.compound` → `https://modelseed.org/biochem/compounds/` - SEED compound entries
  - `seed.reaction` → `https://modelseed.org/biochem/reactions/` - SEED reaction entries

- **MetaCyc** (Metabolic Pathway Database)
  - `metacyc.reaction` → `https://metacyc.org/reaction?orgid=META&id=` - MetaCyc reactions
  - `metacyc.reaction` → `https://metacyc.org/compound?orgid=META&id=` - MetaCyc compounds
  - `metacyc.pathway` → `http://purl.obolibrary.org/obo/metacyc.pathway/` - MetaCyc pathways

- **Reactome** (Pathway Database)
  - `Reactome` → `https://reactome.org/content/detail/` - Reactome pathway details

- **OMP** (Ontology of Microbial Phenotypes)
  - `OMP` → `http://purl.obolibrary.org/obo/OMP_` - OMP term URIs

## How It Works

1. **During Docker Build**: The `custom_prefixes.csv` file is copied into the Docker image and appended to SemsQL's main `prefixes.csv` file.

2. **In SemsQL Database Creation**: When SemsQL creates a database from our merged ontology, it imports all prefixes (including our custom ones) into the database's `prefix` table.

3. **Result**: All URIs from KEGG, SEED, MetaCyc, and Reactome are properly prefixed in the resulting SemsQL database.

## Integration with Main Workflow

The custom prefixes are automatically integrated when:
- Building the Docker image (`make docker-build`)
- Running the production pipeline (`make docker-run-prod`)
- Running the test pipeline (`make docker-test`)

The merged ontology contains terms from 32 ontologies including KEGG, SEED, MetaCyc, Reactome, and many others from OBO Foundry and PyOBO sources.

## File Format

The `custom_prefixes.csv` file follows the standard SemsQL prefix format:
```csv
prefix,base
prefix_name,base_uri
```

Multiple prefixes can map to different base URIs for the same database (e.g., different KEGG entry types).