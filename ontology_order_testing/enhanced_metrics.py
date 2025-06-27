#!/usr/bin/env python3
"""
Enhanced Metrics Collection for Ontology Analysis

Provides detailed metrics and comparison capabilities for merged ontologies.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
import tempfile
import time

class EnhancedMetricsCollector:
    def __init__(self):
        self.metrics_cache = {}
    
    def collect_all_metrics(self, owl_file: Path) -> Dict:
        """Collect comprehensive metrics from an OWL file."""
        start_time = time.time()
        
        metrics = {
            'file_path': str(owl_file),
            'file_size': owl_file.stat().st_size if owl_file.exists() else 0,
            'basic_counts': self.get_basic_counts(owl_file),
            'axiom_breakdown': self.get_axiom_breakdown(owl_file),
            'annotation_properties': self.get_annotation_properties(owl_file),
            'defined_by_analysis': self.get_defined_by_analysis(owl_file),
            'collection_time': time.time() - start_time
        }
        
        return metrics
    
    def get_basic_counts(self, owl_file: Path) -> Dict:
        """Get basic entity counts using multiple methods."""
        counts = {}
        
        # Method 1: Use ROBOT stats if available
        try:
            stats_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            stats_file.close()
            
            result = subprocess.run([
                'robot', 'stats',
                '--input', str(owl_file),
                '--output', stats_file.name
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and Path(stats_file.name).exists():
                with open(stats_file.name, 'r') as f:
                    content = f.read()
                    # Parse stats output
                    for line in content.split('\n'):
                        if 'Classes:' in line:
                            counts['total_classes'] = int(line.split(':')[1].strip())
                        elif 'Object properties:' in line:
                            counts['object_properties'] = int(line.split(':')[1].strip())
                        elif 'Data properties:' in line:
                            counts['data_properties'] = int(line.split(':')[1].strip())
                        elif 'Annotation properties:' in line:
                            counts['annotation_properties'] = int(line.split(':')[1].strip())
                        elif 'Individuals:' in line:
                            counts['individuals'] = int(line.split(':')[1].strip())
                        elif 'Axioms:' in line and 'Logical' not in line:
                            counts['total_axioms'] = int(line.split(':')[1].strip())
                        elif 'Logical axioms:' in line:
                            counts['logical_axioms'] = int(line.split(':')[1].strip())
            
            os.unlink(stats_file.name)
        except Exception as e:
            print(f"  ⚠️  Stats collection failed: {str(e)}")
        
        # Method 2: SPARQL queries as fallback
        if 'total_classes' not in counts:
            counts['total_classes'] = self.count_by_sparql(owl_file, 'owl:Class')
        
        if 'object_properties' not in counts:
            counts['object_properties'] = self.count_by_sparql(owl_file, 'owl:ObjectProperty')
        
        if 'data_properties' not in counts:
            counts['data_properties'] = self.count_by_sparql(owl_file, 'owl:DatatypeProperty')
        
        return counts
    
    def count_by_sparql(self, owl_file: Path, rdf_type: str) -> int:
        """Count entities of a specific type using SPARQL."""
        try:
            prefix = "owl" if rdf_type.startswith("owl:") else "rdf"
            query = f'''
                PREFIX {prefix}: <http://www.w3.org/2002/07/{prefix}#>
                SELECT (COUNT(DISTINCT ?s) as ?count)
                WHERE {{ ?s a {rdf_type} }}
            '''
            
            result = subprocess.run([
                'robot', 'query',
                '--input', str(owl_file),
                '--query', query,
                '--format', 'csv'
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return int(lines[1])
        except Exception as e:
            print(f"  ⚠️  SPARQL count failed for {rdf_type}: {str(e)}")
        
        return 0
    
    def get_axiom_breakdown(self, owl_file: Path) -> Dict:
        """Get detailed axiom type counts."""
        axiom_types = {}
        
        try:
            # Query for different axiom types
            axiom_queries = {
                'subclass_axioms': '''
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    SELECT (COUNT(*) as ?count)
                    WHERE { ?s rdfs:subClassOf ?o }
                ''',
                'equivalent_class_axioms': '''
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    SELECT (COUNT(*) as ?count)
                    WHERE { ?s owl:equivalentClass ?o }
                ''',
                'disjoint_class_axioms': '''
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    SELECT (COUNT(*) as ?count)
                    WHERE { ?s owl:disjointWith ?o }
                ''',
                'annotation_assertions': '''
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    SELECT (COUNT(*) as ?count)
                    WHERE { ?s rdfs:label ?o }
                '''
            }
            
            for axiom_type, query in axiom_queries.items():
                result = subprocess.run([
                    'robot', 'query',
                    '--input', str(owl_file),
                    '--query', query,
                    '--format', 'csv'
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        axiom_types[axiom_type] = int(lines[1])
                else:
                    axiom_types[axiom_type] = 0
                    
        except Exception as e:
            print(f"  ⚠️  Axiom breakdown failed: {str(e)}")
        
        return axiom_types
    
    def get_annotation_properties(self, owl_file: Path) -> Dict:
        """Analyze annotation properties, especially isDefinedBy."""
        annotations = {}
        
        try:
            # Count isDefinedBy annotations
            query = '''
                PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
                SELECT ?definer (COUNT(DISTINCT ?s) as ?count)
                WHERE { 
                    ?s oboInOwl:isDefinedBy ?definer 
                }
                GROUP BY ?definer
                ORDER BY DESC(?count)
            '''
            
            result = subprocess.run([
                'robot', 'query',
                '--input', str(owl_file),
                '--query', query,
                '--format', 'csv'
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                definers = {}
                for line in lines[1:]:  # Skip header
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            definer = parts[0]
                            count = int(parts[1])
                            definers[definer] = count
                
                annotations['defined_by_counts'] = definers
                annotations['total_defined_terms'] = sum(definers.values())
                annotations['unique_definers'] = len(definers)
        
        except Exception as e:
            print(f"  ⚠️  Annotation analysis failed: {str(e)}")
            
        return annotations
    
    def get_defined_by_analysis(self, owl_file: Path) -> Dict:
        """Detailed analysis of term attribution."""
        analysis = {}
        
        try:
            # Get sample of terms with their definers
            query = '''
                PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?term ?label ?definer
                WHERE { 
                    ?term oboInOwl:isDefinedBy ?definer .
                    OPTIONAL { ?term rdfs:label ?label }
                }
                LIMIT 1000
            '''
            
            result = subprocess.run([
                'robot', 'query',
                '--input', str(owl_file),
                '--query', query,
                '--format', 'csv'
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                term_definers = defaultdict(list)
                
                for line in lines[1:]:  # Skip header
                    if line:
                        parts = line.split(',', 2)
                        if len(parts) >= 3:
                            term = parts[0]
                            label = parts[1]
                            definer = parts[2]
                            
                            # Extract ontology prefix from term
                            if '/obo/' in term:
                                term_prefix = term.split('/obo/')[1].split('_')[0]
                                term_definers[term_prefix].append({
                                    'term': term,
                                    'label': label,
                                    'definer': definer
                                })
                
                analysis['sample_attributions'] = dict(term_definers)
                analysis['cross_references'] = self.analyze_cross_references(term_definers)
                
        except Exception as e:
            print(f"  ⚠️  Defined-by analysis failed: {str(e)}")
            
        return analysis
    
    def analyze_cross_references(self, term_definers: Dict) -> Dict:
        """Analyze cross-ontology term attribution."""
        cross_refs = defaultdict(lambda: defaultdict(int))
        
        for term_prefix, terms in term_definers.items():
            for term_info in terms:
                definer = term_info['definer']
                if '/obo/' in definer:
                    definer_prefix = definer.split('/obo/')[1].split('.')[0].upper()
                    if term_prefix.upper() != definer_prefix:
                        cross_refs[term_prefix.upper()][definer_prefix] += 1
        
        return dict(cross_refs)
    
    def compare_metrics(self, metrics1: Dict, metrics2: Dict, label1: str, label2: str) -> Dict:
        """Compare two sets of metrics and highlight differences."""
        comparison = {
            'label1': label1,
            'label2': label2,
            'file_size_diff': metrics2['file_size'] - metrics1['file_size'],
            'basic_count_diffs': {},
            'axiom_type_diffs': {},
            'definer_differences': {}
        }
        
        # Compare basic counts
        counts1 = metrics1.get('basic_counts', {})
        counts2 = metrics2.get('basic_counts', {})
        
        for key in set(counts1.keys()) | set(counts2.keys()):
            val1 = counts1.get(key, 0)
            val2 = counts2.get(key, 0)
            if val1 != val2:
                comparison['basic_count_diffs'][key] = {
                    label1: val1,
                    label2: val2,
                    'difference': val2 - val1
                }
        
        # Compare axiom types
        axioms1 = metrics1.get('axiom_breakdown', {})
        axioms2 = metrics2.get('axiom_breakdown', {})
        
        for key in set(axioms1.keys()) | set(axioms2.keys()):
            val1 = axioms1.get(key, 0)
            val2 = axioms2.get(key, 0)
            if val1 != val2:
                comparison['axiom_type_diffs'][key] = {
                    label1: val1,
                    label2: val2,
                    'difference': val2 - val1
                }
        
        # Compare definers
        definers1 = metrics1.get('annotation_properties', {}).get('defined_by_counts', {})
        definers2 = metrics2.get('annotation_properties', {}).get('defined_by_counts', {})
        
        all_definers = set(definers1.keys()) | set(definers2.keys())
        for definer in all_definers:
            count1 = definers1.get(definer, 0)
            count2 = definers2.get(definer, 0)
            if count1 != count2:
                comparison['definer_differences'][definer] = {
                    label1: count1,
                    label2: count2,
                    'difference': count2 - count1
                }
        
        # Calculate summary statistics
        comparison['summary'] = {
            'total_differences': len(comparison['basic_count_diffs']) + 
                               len(comparison['axiom_type_diffs']) + 
                               len(comparison['definer_differences']),
            'has_significant_differences': (
                abs(comparison['file_size_diff']) > 1000000 or  # 1MB
                len(comparison['definer_differences']) > 0
            )
        }
        
        return comparison