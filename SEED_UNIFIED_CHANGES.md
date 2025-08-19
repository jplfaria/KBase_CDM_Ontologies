# Seed Unified Ontology Integration

## Changes Made

### 1. Updated Ontology Source List
**File**: `config/ontologies_source_seed_unified.txt`
- **Removed**: `seed` and `modelseed` from in-house ontologies section
- **Added**: `https://github.com/ModelSEED/ModelSEEDTemplates/raw/template_ontology/templates/ontology/ontology/seed_unified.owl.gz`

### 2. Updated Custom Prefixes
**File**: `semsql_custom_prefixes/custom_prefixes_seed_unified.csv`
- **Added**: `seed.role,https://pubseed.theseed.org/RoleEditor.cgi?page=ShowRole&Role=`
- **Added**: `seed.subsystem,https://pubseed.theseed.org/SubsysEditor.cgi?page=ShowSubsystem&subsystem=`
- **Added**: `seed.complex,https://modelseed.org/biochem/complexes/`
- **Added**: `https://modelseed.org/ontology/enables_reaction,enables_reaction`
- **Added**: `https://modelseed.org/ontology/has_role,has_role`
- **Added**: `https://modelseed.org/ontology/has_complex,has_complex`
- **Added**: `https://modelseed.org/ontology/reaction_type,reaction_type`

## Analysis of seed_unified.owl

The unified ontology contains:
- **66,961** reaction references (`seed.reaction`)
- **45,706** compound references (`seed.compound`)
- **14,197** complex references (`seed.complex`) - NEW
- **61,636** role references (`pubseed.role`) - NEW  
- **1,324** subsystem references (`pubseed.subsystem`) - NEW

## File Management on Remote Machine

### Option 1: Keep old files (Recommended)
- Leave `seed.owl` and `modelseed.owl` in `ontology_data_owl/` 
- They won't be processed since they're not in the source list
- Provides backup in case of issues

### Option 2: Remove old files
```bash
# On remote machine
cd /scratch/jplfaria/KBase_CDM_Ontologies/ontology_data_owl
mv seed.owl seed.owl.backup
mv modelseed.owl modelseed.owl.backup
```

## Testing the Changes

To test with the new configuration:
```bash
# Use the new config files
export ONTOLOGIES_SOURCE_FILE=config/ontologies_source_seed_unified.txt
export CUSTOM_PREFIXES_FILE=semsql_custom_prefixes/custom_prefixes_seed_unified.csv
make docker-test
```

## What This Achieves

1. **Consolidation**: Single unified ontology replaces separate seed + modelseed
2. **Enhanced Coverage**: Includes complexes, CHEBI links, and subsystem/role mappings
3. **Better Integration**: Direct URLs to source databases for better traceability
4. **Reduced Redundancy**: Eliminates potential conflicts between seed and modelseed