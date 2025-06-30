# Ontology Order Testing Results - Key Findings

## Executive Summary
Order matters significantly when merging ontologies with ROBOT's --annotate-defined-by flag.

## 24-Ontology Test Results
### File Size Impact
- **Alphabetical**: 1,580,634,603 bytes (1.58 GB)
- **Hierarchy/Size**: 1,531,010,144 bytes (1.53 GB)
- **Savings**: 49,624,459 bytes (49.6 MB, 3.14%)

### Axiom Count Impact  
- **Alphabetical**: 3,812,530 axioms
- **Hierarchy/Size**: 3,634,095 axioms
- **Reduction**: 178,435 axioms (4.68%)

### Class Count Impact
- **Alphabetical**: 32,668 classes
- **Hierarchy/Size**: 24,095 classes  
- **Reduction**: 8,573 classes (26.2%)

## 4-Ontology Permutation Analysis
- Tested all 24 permutations of CHEBI, FOODON, GO, ENVO
- **Size variation**: 32.2 MB (4.20%) between best and worst orders
- **Best order**: FOODON → GO → ENVO → CHEBI (766 MB)
- **Worst order**: ENVO → GO → FOODON → CHEBI (798 MB)

## Key Insights
1. CHEBI position dramatically affects size (9MB smaller when last)
2. FOODON first produces smallest files
3. ENVO first produces largest files
4. Hierarchy ordering groups related ontologies, reducing redundancy

## Recommendation
Use hierarchy-based ordering in production for:
- 3.14% space savings
- 178K fewer axioms to process
- More logical grouping of related ontologies
