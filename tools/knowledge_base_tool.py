"""Sleep Knowledge Base Tool for ADK Agent"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

class SleepKnowledgeBaseTool:
    """Tool for accessing sleep knowledge graph"""
    
    def __init__(self, knowledge_path: str = None):
        if knowledge_path is None:
            # Look for knowledge base in the deployment structure
            base_dir = os.path.dirname(os.path.dirname(__file__))
            knowledge_path = os.path.join(base_dir, 'knowledge_base', 'sleep_knowledge_graph.json')
        
        with open(knowledge_path, 'r') as f:
            self.knowledge_graph = json.load(f)
        
        # Create quick lookup indices
        self._build_indices()
    
    def _build_indices(self):
        """Build indices for fast lookup"""
        self.problem_index = {}
        self.age_index = {}
        self.symptom_index = {}
        self.concept_index = {}
        
        # Index problems by symptoms
        for problem_name, problem_data in self.knowledge_graph['problems'].items():
            for symptom in problem_data.get('symptoms', []):
                symptom_key = symptom.lower()
                if symptom_key not in self.symptom_index:
                    self.symptom_index[symptom_key] = []
                self.symptom_index[symptom_key].append(problem_name)
        
        # Index by age groups
        for problem_name, problem_data in self.knowledge_graph['problems'].items():
            for age_group in problem_data.get('age_groups_affected', []):
                if age_group not in self.age_index:
                    self.age_index[age_group] = []
                self.age_index[age_group].append(problem_name)
    
    def find_problem_by_symptoms(self, symptoms: List[str]) -> List[Dict[str, Any]]:
        """Find problems matching given symptoms"""
        matched_problems = {}
        
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            # Check exact matches first
            if symptom_lower in self.symptom_index:
                for problem in self.symptom_index[symptom_lower]:
                    if problem not in matched_problems:
                        matched_problems[problem] = 0
                    matched_problems[problem] += 1
            
            # Check partial matches
            for indexed_symptom, problems in self.symptom_index.items():
                if symptom_lower in indexed_symptom or indexed_symptom in symptom_lower:
                    for problem in problems:
                        if problem not in matched_problems:
                            matched_problems[problem] = 0
                        matched_problems[problem] += 0.5
        
        # Sort by relevance
        sorted_problems = sorted(matched_problems.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for problem_name, score in sorted_problems[:3]:  # Top 3 matches
            problem_data = self.knowledge_graph['problems'][problem_name]
            results.append({
                'problem': problem_name,
                'match_score': score,
                'data': problem_data
            })
        
        return results
    
    def get_solutions_for_problem(self, problem_name: str) -> Optional[Dict[str, Any]]:
        """Get solutions for a specific problem"""
        if problem_name in self.knowledge_graph['problems']:
            problem_data = self.knowledge_graph['problems'][problem_name]
            return {
                'problem': problem_name,
                'definition': problem_data.get('definition', ''),
                'solutions': problem_data.get('solutions', {}),
                'related_problems': problem_data.get('related_problems', [])
            }
        return None
    
    def get_age_specific_info(self, age: str) -> Dict[str, Any]:
        """Get age-specific sleep information"""
        result = {
            'wake_windows': None,
            'schedule': None,
            'common_problems': [],
            'developmental_considerations': []
        }
        
        # Find wake windows
        wake_windows = self.knowledge_graph['age_specific_data']['wake_windows']
        for age_range, data in wake_windows.items():
            if age in age_range or age_range in age:
                result['wake_windows'] = data
                break
        
        # Find schedule
        schedules = self.knowledge_graph['age_specific_data']['schedules']
        for age_key, schedule in schedules.items():
            if age in age_key or age_key in age:
                result['schedule'] = schedule
                break
        
        # Find common problems for this age
        if age in self.age_index:
            result['common_problems'] = self.age_index[age]
        
        # Check for relevant regressions
        regressions = self.knowledge_graph['developmental_milestones']['sleep_regressions']
        for regression_name, regression_data in regressions.items():
            if age in regression_name or regression_name in age:
                result['developmental_considerations'].append({
                    'type': 'sleep_regression',
                    'name': regression_name,
                    'data': regression_data
                })
        
        return result
    
    def get_sleep_method(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific sleep training method"""
        methods = self.knowledge_graph['sleep_methods']
        
        # Check direct match
        if method_name in methods:
            return methods[method_name]
        
        # Check within sleep training methods
        if 'sleep_training' in methods and 'methods' in methods['sleep_training']:
            training_methods = methods['sleep_training']['methods']
            if method_name in training_methods:
                return training_methods[method_name]
        
        return None
    
    def get_concept(self, concept_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a sleep concept"""
        concepts = self.knowledge_graph['concepts']
        
        # Direct match
        if concept_name in concepts:
            return concepts[concept_name]
        
        # Fuzzy match
        for key, value in concepts.items():
            if concept_name.lower() in key.lower() or key.lower() in concept_name.lower():
                return value
        
        return None
    
    def traverse_problem_graph(self, start_problem: str, target_type: str = 'solution') -> List[Dict[str, Any]]:
        """Traverse the problem graph to find related information"""
        if start_problem not in self.knowledge_graph['problems']:
            return []
        
        visited = set()
        path = []
        
        def dfs(current_problem: str, depth: int = 0):
            if depth > 3 or current_problem in visited:
                return
            
            visited.add(current_problem)
            problem_data = self.knowledge_graph['problems'].get(current_problem, {})
            
            if target_type == 'solution' and 'solutions' in problem_data:
                path.append({
                    'problem': current_problem,
                    'solutions': problem_data['solutions']
                })
            
            # Explore related problems
            for related in problem_data.get('related_problems', []):
                dfs(related, depth + 1)
        
        dfs(start_problem)
        return path
    
    def search(self, query: str, child_age: Optional[str] = None) -> Dict[str, Any]:
        """Main search function that combines multiple search strategies"""
        query_lower = query.lower()
        results = {
            'matched_problems': [],
            'concepts': [],
            'methods': [],
            'age_specific': None,
            'recommendations': []
        }
        
        # Direct problem name matching
        for problem_name, problem_data in self.knowledge_graph['problems'].items():
            problem_words = problem_name.replace('_', ' ').lower()
            # Check if problem name appears in query
            if problem_words in query_lower:
                results['matched_problems'].append({
                    'problem': problem_name,
                    'match_score': 10,  # High score for direct match
                    'data': problem_data
                })
            # Check problem-specific keywords
            elif problem_name == 'split_nights' and ('2 hours' in query_lower or 'middle of the night' in query_lower):
                results['matched_problems'].append({
                    'problem': problem_name,
                    'match_score': 8,
                    'data': problem_data
                })
            elif problem_name == 'short_naps' and ('30 minute' in query_lower or '45 minute' in query_lower):
                results['matched_problems'].append({
                    'problem': problem_name,
                    'match_score': 8,
                    'data': problem_data
                })
            elif problem_name == 'early_rising' and ('5am' in query_lower or '5 am' in query_lower or 'early' in query_lower):
                results['matched_problems'].append({
                    'problem': problem_name,
                    'match_score': 8,
                    'data': problem_data
                })
            elif problem_name == 'false_starts' and ('45 minutes after bedtime' in query_lower or 'after bedtime' in query_lower):
                results['matched_problems'].append({
                    'problem': problem_name,
                    'match_score': 8,
                    'data': problem_data
                })
        
        # Extract potential symptoms from query
        symptoms = []
        for problem_data in self.knowledge_graph['problems'].values():
            for symptom in problem_data.get('symptoms', []):
                if symptom.lower() in query_lower:
                    symptoms.append(symptom)
        
        # Find problems by symptoms if no direct matches
        if symptoms and not results['matched_problems']:
            results['matched_problems'] = self.find_problem_by_symptoms(symptoms)
        
        # Check for concept matches
        for concept_name in self.knowledge_graph['concepts']:
            if concept_name.replace('_', ' ') in query_lower:
                concept_data = self.get_concept(concept_name)
                if concept_data:
                    results['concepts'].append({
                        'name': concept_name,
                        'data': concept_data
                    })
        
        # Check for method matches
        for method_name in self.knowledge_graph['sleep_methods']:
            if method_name.replace('_', ' ') in query_lower:
                method_data = self.get_sleep_method(method_name)
                if method_data:
                    results['methods'].append({
                        'name': method_name,
                        'data': method_data
                    })
        
        # Add age-specific information if provided
        if child_age:
            results['age_specific'] = self.get_age_specific_info(child_age)
        
        # Generate recommendations based on findings
        if results['matched_problems']:
            top_problem = results['matched_problems'][0]
            solutions = top_problem['data'].get('solutions', {})
            
            if 'immediate' in solutions:
                results['recommendations'].append({
                    'type': 'immediate_action',
                    'actions': solutions['immediate']
                })
            
            if 'long_term' in solutions:
                results['recommendations'].append({
                    'type': 'long_term_plan',
                    'actions': solutions['long_term']
                })
        
        return results


# Create tool function for ADK agent
def create_sleep_knowledge_tool():
    """Create a tool function that can be used by ADK agent"""
    kb = SleepKnowledgeBaseTool()
    
    def sleep_knowledge_search(query: str, child_age: Optional[str] = None) -> str:
        """
        Search the sleep knowledge base for information.
        
        Args:
            query: The sleep-related question or symptoms
            child_age: Optional age of the child (e.g., "6 months", "2 years")
        
        Returns:
            Relevant sleep information and recommendations
        """
        results = kb.search(query, child_age)
        
        # Format results for agent response
        response_parts = []
        
        if results['matched_problems']:
            response_parts.append("Based on the symptoms described, here are possible issues:")
            for match in results['matched_problems']:
                problem = match['problem']
                definition = match['data'].get('definition', '')
                response_parts.append(f"\n**{problem.replace('_', ' ').title()}**: {definition}")
                
                # Add immediate solutions
                solutions = match['data'].get('solutions', {})
                if 'immediate' in solutions:
                    response_parts.append("\nImmediate steps to try:")
                    for action in solutions['immediate']:
                        if isinstance(action, dict):
                            response_parts.append(f"- {action.get('action', '')}")
                            for detail in action.get('details', []):
                                response_parts.append(f"  • {detail}")
                        else:
                            response_parts.append(f"- {action}")
        
        if results['age_specific'] and child_age:
            response_parts.append(f"\nFor a {child_age} old:")
            if results['age_specific']['wake_windows']:
                ww = results['age_specific']['wake_windows']
                response_parts.append(f"- Wake windows: {ww.get('wake_window', 'Not specified')}")
                response_parts.append(f"- Expected naps: {ww.get('naps', 'Not specified')}")
            
            if results['age_specific']['schedule']:
                schedule = results['age_specific']['schedule']
                response_parts.append(f"- Total sleep needed: {schedule.get('total_sleep', 'Not specified')}")
                response_parts.append(f"- Night sleep: {schedule.get('night_sleep', 'Not specified')}")
                response_parts.append(f"- Day sleep: {schedule.get('day_sleep', 'Not specified')}")
        
        if results['concepts']:
            response_parts.append("\nRelevant information:")
            for concept in results['concepts']:
                response_parts.append(f"\n**{concept['name'].replace('_', ' ').title()}**")
                # Add key points from concept
                data = concept['data']
                if 'definition' in data:
                    response_parts.append(data['definition'])
        
        return '\n'.join(response_parts) if response_parts else "I couldn't find specific information for that query. Could you provide more details about the sleep issue you're experiencing?"
    
    return sleep_knowledge_search