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
        """Get basic entity counts using multiple robust methods."""
        counts = {}
        file_size_gb = owl_file.stat().st_size / (1024**3) if owl_file.exists() else 0
        
        print(f"    📏 File size: {file_size_gb:.2f}GB - selecting appropriate method")
        
        # Method 1: ROBOT measure with high memory (primary method)
        counts = self.count_with_robot_measure(owl_file)
        
        # Method 2: SPARQL queries (fallback if ROBOT fails)
        if not counts or counts.get('total_axioms', 0) == 0:
            print(f"    🔄 ROBOT measure failed, trying SPARQL fallbacks...")
            sparql_counts = self.count_with_sparql_fallbacks(owl_file)
            counts.update(sparql_counts)
        
        # Method 3: Pattern-based counting (last resort)
        if not counts or counts.get('total_axioms', 0) == 0:
            print(f"    🔄 SPARQL failed, trying pattern-based counting...")
            pattern_counts = self.count_with_pattern_matching(owl_file)
            counts.update(pattern_counts)
        
        # Add analysis metadata
        counts['analysis_method'] = self.determine_method_used(counts)
        counts['file_size_gb'] = file_size_gb
        
        return counts
    
    def count_with_robot_measure(self, owl_file: Path) -> Dict:
        """Use ROBOT measure with high memory allocation."""
        counts = {}
        
        try:
            # Create temporary output file
            measure_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            measure_file.close()
            
            # Prepare environment with maximum memory allocation
            env = os.environ.copy()
            
            # Inherit high memory from testing environment, fallback to very generous defaults
            default_memory = '-Xmx128g -XX:MaxMetaspaceSize=16g -XX:+UseG1GC -XX:G1HeapRegionSize=32m'
            java_opts = env.get('ROBOT_JAVA_ARGS', default_memory)
            
            # Ensure we have adequate memory for large ontologies
            if 'Xmx' not in java_opts or ('8g' in java_opts and owl_file.stat().st_size > 100*1024*1024):
                java_opts = default_memory
            
            env['ROBOT_JAVA_ARGS'] = java_opts
            
            print(f"    🤖 ROBOT measure: {java_opts.split()[0]} memory")
            
            # Run ROBOT measure with extended timeout for large files
            file_size_mb = owl_file.stat().st_size / (1024*1024)
            timeout = min(1800, max(300, int(file_size_mb * 2)))  # 5-30 minutes based on file size
            
            result = subprocess.run([
                'robot', 'measure',
                '--input', str(owl_file),
                '--metrics', 'all',
                '--output', measure_file.name
            ], capture_output=True, text=True, timeout=timeout, env=env)
            
            if result.returncode == 0 and Path(measure_file.name).exists():
                with open(measure_file.name, 'r') as f:
                    content = f.read()
                    counts = self.parse_robot_measure_output(content)
                if counts.get('total_axioms', 0) > 0:
                    print(f"    ✅ ROBOT measure successful: {counts.get('total_axioms', 0):,} axioms")
                else:
                    print(f"    ⚠️  ROBOT measure returned zero axioms")
            else:
                error_msg = result.stderr[:300] if result.stderr else "Unknown error"
                print(f"    ❌ ROBOT measure failed: {error_msg}")
            
            # Cleanup
            try:
                os.unlink(measure_file.name)
            except:
                pass
            
        except subprocess.TimeoutExpired:
            print(f"    ⏱️  ROBOT measure timed out after {timeout//60} minutes")
            try:
                os.unlink(measure_file.name)
            except:
                pass
        except Exception as e:
            print(f"    ⚠️  ROBOT measure exception: {str(e)}")
        
        return counts
    
    def parse_robot_measure_output(self, content: str) -> Dict:
        """Parse ROBOT measure output to extract counts."""
        counts = {}
        
        for line in content.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Map ROBOT measure output to our standard keys
                if 'class' in key.lower() and 'count' in key.lower():
                    counts['total_classes'] = int(value)
                elif 'object' in key.lower() and 'propert' in key.lower():
                    counts['object_properties'] = int(value)
                elif 'data' in key.lower() and 'propert' in key.lower():
                    counts['data_properties'] = int(value)
                elif 'annotation' in key.lower() and 'propert' in key.lower():
                    counts['annotation_properties'] = int(value)
                elif 'individual' in key.lower():
                    counts['individuals'] = int(value)
                elif 'axiom' in key.lower() and 'logical' not in key.lower():
                    counts['total_axioms'] = int(value)
                elif 'logical' in key.lower() and 'axiom' in key.lower():
                    counts['logical_axioms'] = int(value)
        
        return counts
    
    def count_with_sparql_fallbacks(self, owl_file: Path) -> Dict:
        """Use SPARQL queries with memory management as fallback."""
        counts = {}
        
        # Basic entity counts with adaptive timeouts based on file size
        file_size_mb = owl_file.stat().st_size / (1024*1024)
        base_timeout = min(600, max(60, int(file_size_mb * 0.5)))  # 1-10 minutes based on size
        
        sparql_queries = {
            'total_classes': ('owl:Class', 'owl'),
            'object_properties': ('owl:ObjectProperty', 'owl'),
            'data_properties': ('owl:DatatypeProperty', 'owl'),
            'annotation_properties': ('owl:AnnotationProperty', 'owl'),
            'individuals': ('owl:NamedIndividual', 'owl')
        }
        
        print(f"    🔍 SPARQL queries with {base_timeout}s timeout")
        
        for count_type, (rdf_type, prefix) in sparql_queries.items():
            try:
                count = self.count_by_sparql(owl_file, rdf_type, timeout=base_timeout)
                if count > 0:
                    counts[count_type] = count
                    print(f"    ✅ SPARQL {count_type}: {count:,}")
                else:
                    print(f"    ⚪ SPARQL {count_type}: 0 (may indicate query issues)")
            except Exception as e:
                print(f"    ⚠️  SPARQL {count_type} failed: {str(e)}")
                continue
        
        # Try to estimate total axioms if we have entity counts
        if counts and 'total_axioms' not in counts:
            estimated_axioms = self.estimate_axioms_from_entities(counts)
            if estimated_axioms > 0:
                counts['total_axioms'] = estimated_axioms
                counts['axiom_estimation_method'] = 'entity_based'
                print(f"    📊 Estimated axioms from entities: {estimated_axioms:,}")
        
        return counts
    
    def count_with_pattern_matching(self, owl_file: Path) -> Dict:
        """Use pattern matching as last resort for very large files."""
        counts = {}
        
        try:
            print(f"    🔍 Pattern-based counting (most robust method)")
            
            # Multiple pattern strategies for reliability
            strategies = {
                'xml_tags': {
                    'total_classes': r'<owl:Class[>\s]',
                    'object_properties': r'<owl:ObjectProperty[>\s]',
                    'data_properties': r'<owl:DatatypeProperty[>\s]',
                    'annotation_properties': r'<owl:AnnotationProperty[>\s]',
                    'individuals': r'<owl:NamedIndividual[>\s]'
                },
                'rdf_about': {
                    'total_classes': r'rdf:about="[^"]*"[^>]*>\s*<rdf:type[^>]*owl:Class',
                    'object_properties': r'rdf:about="[^"]*"[^>]*>\s*<rdf:type[^>]*owl:ObjectProperty',
                    'annotation_properties': r'rdf:about="[^"]*"[^>]*>\s*<rdf:type[^>]*owl:AnnotationProperty'
                }
            }
            
            best_counts = {}
            
            for strategy_name, patterns in strategies.items():
                strategy_counts = {}
                
                for count_type, pattern in patterns.items():
                    try:
                        # Use grep with extended regex support
                        result = subprocess.run([
                            'grep', '-E', '-c', pattern, str(owl_file)
                        ], capture_output=True, text=True, timeout=120)
                        
                        if result.returncode == 0:
                            count = int(result.stdout.strip())
                            strategy_counts[count_type] = count
                    
                    except Exception as e:
                        continue
                
                # Use strategy with highest total counts (likely most accurate)
                total_entities = sum(strategy_counts.values())
                if total_entities > sum(best_counts.values()):
                    best_counts = strategy_counts
                    print(f"    📊 Best strategy: {strategy_name} ({total_entities:,} entities)")
            
            counts = best_counts
            
            # Report findings
            for count_type, count in counts.items():
                print(f"    📊 Pattern {count_type}: {count:,}")
            
            # Enhanced axiom estimation using multiple factors
            if counts:
                estimated_axioms = self.estimate_axioms_comprehensive(counts, owl_file)
                counts['total_axioms'] = estimated_axioms
                counts['estimation_note'] = 'Comprehensive axiom estimation from patterns and file analysis'
                print(f"    📊 Estimated total axioms: {estimated_axioms:,}")
        
        except Exception as e:
            print(f"    ❌ Pattern matching failed: {str(e)}")
        
        return counts
    
    def determine_method_used(self, counts: Dict) -> str:
        """Determine which counting method was successful."""
        if 'estimation_note' in counts:
            return 'pattern_matching'
        elif 'axiom_estimation_method' in counts:
            return 'sparql_with_estimation'
        elif counts.get('total_axioms', 0) > 0 and 'estimation' not in str(counts.get('total_axioms', '')):
            return 'robot_measure'
        elif counts.get('total_classes', 0) > 0:
            return 'sparql_fallback'
        else:
            return 'failed'
    
    def count_by_sparql(self, owl_file: Path, rdf_type: str, timeout: int = 120) -> int:
        """Count entities of a specific type using SPARQL."""
        try:
            prefix = "owl" if rdf_type.startswith("owl:") else "rdf"
            query = f'''
                PREFIX {prefix}: <http://www.w3.org/2002/07/{prefix}#>
                SELECT (COUNT(DISTINCT ?s) as ?count)
                WHERE {{ ?s a {rdf_type} }}
            '''
            
            # Inherit environment for memory settings with generous defaults
            env = os.environ.copy()
            if 'ROBOT_JAVA_ARGS' not in env:
                env['ROBOT_JAVA_ARGS'] = '-Xmx64g -XX:MaxMetaspaceSize=8g -XX:+UseG1GC'
            
            result = subprocess.run([
                'robot', 'query',
                '--input', str(owl_file),
                '--query', query,
                '--format', 'csv'
            ], capture_output=True, text=True, timeout=timeout, env=env)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1 and lines[1].strip():
                    try:
                        return int(lines[1].strip())
                    except ValueError:
                        print(f"  ⚠️  Invalid SPARQL result for {rdf_type}: '{lines[1]}'")
                        return 0
        except subprocess.TimeoutExpired:
            print(f"  ⏱️  SPARQL count timed out for {rdf_type} after {timeout}s")
        except Exception as e:
            print(f"  ⚠️  SPARQL count failed for {rdf_type}: {str(e)}")
        
        return 0
    
    def estimate_axioms_from_entities(self, counts: Dict) -> int:
        """Estimate total axioms based on entity counts using known ratios."""
        # Based on analysis of typical OBO ontologies
        entity_axiom_ratios = {
            'total_classes': 4.5,        # Classes typically have multiple axioms each
            'object_properties': 3.0,    # Properties have domain/range axioms
            'data_properties': 2.5,      # Fewer axioms per data property
            'annotation_properties': 2.0, # Mainly declaration axioms
            'individuals': 1.5           # Individual assertions
        }
        
        total_estimated = 0
        for entity_type, count in counts.items():
            if entity_type in entity_axiom_ratios:
                total_estimated += count * entity_axiom_ratios[entity_type]
        
        return int(total_estimated) if total_estimated > 0 else 0
    
    def estimate_axioms_comprehensive(self, counts: Dict, owl_file: Path) -> int:
        """Comprehensive axiom estimation using multiple factors."""
        # Method 1: Entity-based estimation
        entity_estimate = self.estimate_axioms_from_entities(counts)
        
        # Method 2: File size heuristic (based on typical OWL compression ratios)
        file_size = owl_file.stat().st_size
        size_estimate = file_size // 200  # Rough bytes-per-axiom ratio
        
        # Method 3: Pattern-based axiom counting
        pattern_estimate = self.count_axiom_patterns(owl_file)
        
        # Use the highest estimate as it's likely most accurate
        estimates = [e for e in [entity_estimate, size_estimate, pattern_estimate] if e > 0]
        
        if estimates:
            # Use median of available estimates for robustness
            estimates.sort()
            if len(estimates) == 1:
                return estimates[0]
            elif len(estimates) == 2:
                return int((estimates[0] + estimates[1]) / 2)
            else:
                return estimates[len(estimates)//2]
        
        return 0
    
    def count_axiom_patterns(self, owl_file: Path) -> int:
        """Count axioms using pattern matching."""
        try:
            # Common axiom patterns in OWL files
            axiom_patterns = [
                r'<owl:Class[^>]*>',
                r'<rdfs:subClassOf[^>]*>',
                r'<owl:equivalentClass[^>]*>',
                r'<owl:disjointWith[^>]*>',
                r'<owl:ObjectProperty[^>]*>',
                r'<owl:DatatypeProperty[^>]*>',
                r'<owl:AnnotationProperty[^>]*>',
                r'<rdfs:domain[^>]*>',
                r'<rdfs:range[^>]*>',
                r'<rdfs:label[^>]*>',
                r'<rdfs:comment[^>]*>',
                r'<obo:IAO_0000115[^>]*>'  # definition annotations
            ]
            
            total_axioms = 0
            for pattern in axiom_patterns:
                try:
                    result = subprocess.run([
                        'grep', '-E', '-c', pattern, str(owl_file)
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        total_axioms += int(result.stdout.strip())
                except:
                    continue
            
            return total_axioms
        except:
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