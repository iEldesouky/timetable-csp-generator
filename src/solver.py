# solver.py - IMPROVED WITH DEBUGGING AND OPTIMIZATION

import time
from typing import Dict, List, Tuple, Optional
from csp_model import TimetableCSP
from constraints import HardConstraints, ForwardChecking, SoftConstraints
import streamlit as st

class BacktrackingSolver:
    """
    CSP solver with improved debugging and optimization
    """
    
    def __init__(self, csp: TimetableCSP):
        self.csp = csp
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.start_time = 0
        self.best_solution = None
        self.best_penalty = float('inf')
        self.assignment_history = []
        
    def backtracking_search(self, timeout: int = 120) -> Optional[Dict]:
        """
        Main backtracking search with debugging and progress tracking
        """
        self._reset_counters()
        self.start_time = time.time()
        
        # Create a copy of domains for forward checking
        domains_copy = {var_id: list(domain) for var_id, domain in self.csp.domains.items()}
        
        # Create progress placeholder
        progress_placeholder = st.empty()
        
        solution = self._recursive_backtracking({}, domains_copy, timeout, progress_placeholder)
        
        # Clear progress placeholder
        progress_placeholder.empty()
        
        # Return best solution found
        return self.best_solution if self.best_solution else solution
    
    def _reset_counters(self):
        """Reset performance counters"""
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.best_solution = None
        self.best_penalty = float('inf')
        self.assignment_history = []
    
    def _recursive_backtracking(self, assignment: Dict, domains: Dict, timeout: int, progress_placeholder) -> Optional[Dict]:
        """
        Recursive backtracking with progress tracking and timeout
        """
        # Check timeout
        current_time = time.time()
        if current_time - self.start_time > timeout:
            return None
        
        # If assignment is complete, return it
        if len(assignment) == len(self.csp.variables):
            penalty = SoftConstraints.calculate_solution_penalty(assignment, self.csp)
            if penalty < self.best_penalty:
                self.best_solution = assignment.copy()
                self.best_penalty = penalty
            return assignment
        
        # Update progress every 10 assignments or 2 seconds
        if len(assignment) % 10 == 0 or (current_time - self.start_time) % 2 < 0.1:
            self._update_progress(assignment, progress_placeholder)
        
        # Select variable using MRV heuristic
        var = self._select_unassigned_variable_mrv(assignment, domains)
        if not var:
            return None
        
        # Order values using LCV heuristic
        values = self._order_domain_values_lcv(var, assignment, domains)
        
        for value in values:
            # Check timeout inside loop
            if time.time() - self.start_time > timeout:
                return None
                
            # Check constraints
            self.constraint_checks += 1
            if HardConstraints.check_all_constraints(assignment, var.variable_id, value, self.csp):
                # Make assignment
                assignment[var.variable_id] = value
                self.csp.assignments[var.variable_id] = value
                
                # Do forward checking
                domains_before_fc = {var_id: list(domain) for var_id, domain in domains.items()}
                fc_success = ForwardChecking.do_forward_checking(assignment, var.variable_id, value, domains, self.csp)
                
                if fc_success:
                    result = self._recursive_backtracking(assignment, domains, timeout, progress_placeholder)
                    if result is not None:
                        return result
                
                # Restore domains and backtrack
                assignment.pop(var.variable_id)
                if var.variable_id in self.csp.assignments:
                    del self.csp.assignments[var.variable_id]
                domains.update(domains_before_fc)
                self.backtrack_count += 1
        
        return None
    
    def _update_progress(self, assignment: Dict, progress_placeholder):
        """Update progress display"""
        progress = len(assignment) / len(self.csp.variables)
        elapsed_time = time.time() - self.start_time
        
        progress_text = f"""
        **Search Progress:**
        - Variables assigned: {len(assignment)}/{len(self.csp.variables)} ({progress:.1%})
        - Backtracks: {self.backtrack_count}
        - Constraint checks: {self.constraint_checks}
        - Time elapsed: {elapsed_time:.1f}s
        """
        
        if self.best_solution:
            progress_text += f"- Best solution quality: {self.best_penalty}"
        
        progress_placeholder.info(progress_text)
    
    def _select_unassigned_variable_mrv(self, assignment: Dict, domains: Dict):
        """
        MRV heuristic: choose variable with smallest domain
        Also consider degree heuristic as tie-breaker
        """
        unassigned_vars = [var for var in self.csp.variables if var.variable_id not in assignment]
        
        if not unassigned_vars:
            return None
        
        # Find variables with minimum remaining values
        min_domain_size = min(len(domains[var.variable_id]) for var in unassigned_vars)
        mrv_vars = [var for var in unassigned_vars if len(domains[var.variable_id]) == min_domain_size]
        
        # If tie, use degree heuristic (variable involved in most constraints)
        if len(mrv_vars) > 1:
            return max(mrv_vars, key=self._calculate_variable_degree)
        
        return mrv_vars[0]
    
    def _calculate_variable_degree(self, variable):
        """
        Calculate how constrained a variable is (degree heuristic)
        """
        degree = 0
        for other_var in self.csp.variables:
            if other_var.variable_id != variable.variable_id:
                # Count constraints with other variables
                if (variable.course_id == other_var.course_id or
                    variable.activity_type == other_var.activity_type):
                    degree += 1
        return degree
    
    def _order_domain_values_lcv(self, var, assignment: Dict, domains: Dict) -> List[Tuple]:
        """
        LCV heuristic: order values by how constraining they are
        """
        # For large domains, sample to avoid performance issues
        domain_values = domains[var.variable_id]
        if len(domain_values) > 100:  # Limit for performance
            domain_values = domain_values[:100]
        
        value_constraints = []
        
        for value in domain_values:
            constraint_count = 0
            
            # Sample other variables to avoid O(n^2) complexity
            other_vars_sample = [v for v in self.csp.variables 
                               if v.variable_id != var.variable_id and v.variable_id not in assignment]
            if len(other_vars_sample) > 50:  # Limit sampling
                import random
                other_vars_sample = random.sample(other_vars_sample, 50)
            
            for other_var in other_vars_sample:
                # Sample domain values for other variable
                other_domain = domains[other_var.variable_id]
                if len(other_domain) > 20:  # Limit sampling
                    other_domain = other_domain[:20]
                
                for other_value in other_domain:
                    if not self._are_values_consistent(value, other_value):
                        constraint_count += 1
            
            value_constraints.append((value, constraint_count))
        
        # Sort by constraint count (ascending - least constraining first)
        value_constraints.sort(key=lambda x: x[1])
        return [value for value, _ in value_constraints]
    
    def _are_values_consistent(self, value1: Tuple, value2: Tuple) -> bool:
        """
        Check if two values are consistent with each other
        """
        timeslot1, room1, instructor1 = value1
        timeslot2, room2, instructor2 = value2
        
        # Basic double-booking constraints
        if timeslot1 == timeslot2:
            if instructor1 == instructor2:  # Same instructor
                return False
            if room1 == room2:  # Same room
                return False
        
        return True
    
    def get_performance_metrics(self) -> Dict:
        """
        Get comprehensive performance metrics
        """
        return {
            'backtrack_count': self.backtrack_count,
            'constraint_checks': self.constraint_checks,
            'solution_quality': self.best_penalty if self.best_solution else None,
            'variables_assigned': len(self.best_solution) if self.best_solution else 0,
            'total_variables': len(self.csp.variables),
            'search_time': time.time() - self.start_time if self.start_time > 0 else 0
        }