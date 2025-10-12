import time
from typing import Dict, List, Tuple, Optional
from csp_model import TimetableCSP
from constraints import HardConstraints, ForwardChecking

class BacktrackingSolver:
    """
    CSP solver implementing backtracking search with various optimizations
    Based on CS188 backtracking algorithms
    """
    
    def __init__(self, csp: TimetableCSP):
        self.csp = csp
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.start_time = 0
        
    def backtracking_search(self, timeout: int = 60) -> Optional[Dict]:
        """
        Basic backtracking search algorithm
        Returns: Complete assignment or None if no solution found
        """
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.start_time = time.time()
        
        return self._recursive_backtracking({}, timeout)
    
    def _recursive_backtracking(self, assignment: Dict, timeout: int) -> Optional[Dict]:
        """
        Recursive backtracking helper function
        """
        # Check timeout
        if time.time() - self.start_time > timeout:
            return None
        
        # If assignment is complete, return it
        if self.csp.is_complete():
            return assignment
        
        # Select unassigned variable (basic ordering)
        var = self._select_unassigned_variable(assignment)
        
        # Try each value in the domain
        for value in self.csp.domains[var.variable_id]:
            # Check constraints
            self.constraint_checks += 1
            if HardConstraints.check_all_constraints(assignment, var.variable_id, value, self.csp):
                # Assign the value
                assignment[var.variable_id] = value
                
                # Recursive call
                result = self._recursive_backtracking(assignment, timeout)
                if result is not None:
                    return result
                
                # Backtrack
                del assignment[var.variable_id]
                self.backtrack_count += 1
        
        return None
    
    def backtracking_with_mrv(self, timeout: int = 60) -> Optional[Dict]:
        """
        Backtracking with Minimum Remaining Values heuristic
        """
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.start_time = time.time()
        
        return self._recursive_backtracking_mrv({}, timeout)
    
    def _recursive_backtracking_mrv(self, assignment: Dict, timeout: int) -> Optional[Dict]:
        """
        Backtracking with MRV variable ordering
        """
        if time.time() - self.start_time > timeout:
            return None
        
        if self.csp.is_complete():
            return assignment
        
        # MRV: Select variable with smallest domain
        var = self._select_unassigned_variable_mrv(assignment)
        
        for value in self.csp.domains[var.variable_id]:
            self.constraint_checks += 1
            if HardConstraints.check_all_constraints(assignment, var.variable_id, value, self.csp):
                assignment[var.variable_id] = value
                
                result = self._recursive_backtracking_mrv(assignment, timeout)
                if result is not None:
                    return result
                
                del assignment[var.variable_id]
                self.backtrack_count += 1
        
        return None
    
    def backtracking_with_mrv_lcv(self, timeout: int = 60) -> Optional[Dict]:
        """
        Backtracking with MRV + LCV (Least Constraining Value) heuristics
        """
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.start_time = time.time()
        
        return self._recursive_backtracking_mrv_lcv({}, timeout)
    
    def _recursive_backtracking_mrv_lcv(self, assignment: Dict, timeout: int) -> Optional[Dict]:
        """
        Backtracking with MRV and LCV
        """
        if time.time() - self.start_time > timeout:
            return None
        
        if self.csp.is_complete():
            return assignment
        
        var = self._select_unassigned_variable_mrv(assignment)
        
        # LCV: Order values by how many options they leave for other variables
        values = self._order_domain_values_lcv(var, assignment)
        
        for value in values:
            self.constraint_checks += 1
            if HardConstraints.check_all_constraints(assignment, var.variable_id, value, self.csp):
                assignment[var.variable_id] = value
                
                result = self._recursive_backtracking_mrv_lcv(assignment, timeout)
                if result is not None:
                    return result
                
                del assignment[var.variable_id]
                self.backtrack_count += 1
        
        return None
    
    def backtracking_with_forward_checking(self, timeout: int = 60) -> Optional[Dict]:
        """
        Backtracking with forward checking
        """
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.start_time = time.time()
        
        # Create a copy of domains for forward checking
        domains_copy = {var_id: list(domain) for var_id, domain in self.csp.domains.items()}
        
        return self._recursive_backtracking_fc({}, domains_copy, timeout)
    
    def _recursive_backtracking_fc(self, assignment: Dict, domains: Dict, timeout: int) -> Optional[Dict]:
        """
        Backtracking with forward checking
        """
        if time.time() - self.start_time > timeout:
            return None
        
        if len(assignment) == len(self.csp.variables):
            return assignment
        
        var = self._select_unassigned_variable_mrv(assignment)
        
        for value in domains[var.variable_id]:
            self.constraint_checks += 1
            if HardConstraints.check_all_constraints(assignment, var.variable_id, value, self.csp):
                # Make assignment
                assignment[var.variable_id] = value
                
                # Do forward checking
                domains_before_fc = {var_id: list(domain) for var_id, domain in domains.items()}
                fc_success = ForwardChecking.do_forward_checking(assignment, var.variable_id, value, domains, self.csp)
                
                if fc_success:
                    result = self._recursive_backtracking_fc(assignment, domains, timeout)
                    if result is not None:
                        return result
                
                # Restore domains and backtrack
                assignment.pop(var.variable_id)
                domains.update(domains_before_fc)
                self.backtrack_count += 1
        
        return None
    
    def _select_unassigned_variable(self, assignment: Dict):
        """
        Basic variable selection - first unassigned variable
        """
        for var in self.csp.variables:
            if var.variable_id not in assignment:
                return var
        return None
    
    def _select_unassigned_variable_mrv(self, assignment: Dict):
        """
        MRV heuristic: choose variable with smallest domain
        """
        unassigned_vars = [var for var in self.csp.variables if var.variable_id not in assignment]
        
        if not unassigned_vars:
            return None
        
        # Find variable with minimum remaining values
        return min(unassigned_vars, key=lambda var: len(self.csp.domains[var.variable_id]))
    
    def _order_domain_values_lcv(self, var, assignment: Dict) -> List[Tuple]:
        """
        LCV heuristic: order values by how constraining they are
        Lower constraint count = better (less constraining)
        """
        value_constraints = []
        
        for value in self.csp.domains[var.variable_id]:
            # Count how many values this would eliminate from other variables' domains
            constraint_count = 0
            
            for other_var in self.csp.variables:
                if other_var.variable_id != var.variable_id and other_var.variable_id not in assignment:
                    for other_value in self.csp.domains[other_var.variable_id]:
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
        
        # Same timeslot conflicts
        if timeslot1 == timeslot2:
            if instructor1 == instructor2:  # Same instructor
                return False
            if room1 == room2:  # Same room
                return False
        
        return True