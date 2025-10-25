# [file name]: new_solver.py
import time
from typing import Dict, List, Tuple, Optional, Set
from csp_model import TimetableCSP
import streamlit as st

class BacktrackingSolver:
    """
    NEW Solver based on friend's working forward checking algorithm
    """
    
    def __init__(self, csp: TimetableCSP):
        self.csp = csp
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.start_time = 0
        self.solution = None
        self.performance_metrics = {}
        
    def solve(self, timeout: int = 120) -> Optional[Dict]:
        """
        Main solving method using friend's forward checking search
        """
        self._reset_counters()
        self.start_time = time.time()
        
        # Create progress tracking
        progress_placeholder = st.empty()
        
        try:
            # Use friend's forward checking search algorithm
            solution = self._forward_checking_search(timeout, progress_placeholder)
            
            # Clear progress placeholder
            progress_placeholder.empty()
            
            self.solution = solution
            return solution
            
        except Exception as e:
            progress_placeholder.empty()
            st.error(f"❌ Solver error: {str(e)}")
            return None
    
    def _reset_counters(self):
        """Reset performance counters"""
        self.backtrack_count = 0
        self.constraint_checks = 0
        self.solution = None
        self.performance_metrics = {}
    
    def _forward_checking_search(self, timeout: int, progress_placeholder) -> Optional[Dict]:
        """
        Friend's working forward checking search implementation
        """
        assignment = {}
        
        # Pre-compute constraint neighbors - variables that share any timeslot
        var_timeslots = {}
        for v in self.csp.variables:
            ts_set = set()
            for val in self.csp.domains[v.variable_id]:
                ts_set.add(val['timeslot'])
            var_timeslots[v.variable_id] = ts_set
        
        constraint_neighbors = {}
        for v in self.csp.variables:
            neighbors = []
            v_ts = var_timeslots[v.variable_id]
            for other in self.csp.variables:
                if other.variable_id != v.variable_id and v_ts & var_timeslots[other.variable_id]:
                    neighbors.append(other.variable_id)
            constraint_neighbors[v.variable_id] = neighbors
        
        # Cache for faster lookups - tracks THREE resource types (friend's key insight!)
        assigned_by_timeslot = {}  # timeslot -> {instructor: set(), room: set(), sections: set()}
        local_domains = {v.variable_id: list(self.csp.domains[v.variable_id]) for v in self.csp.variables}
        
        st.info(f"🔍 Constraint graph: {len(constraint_neighbors)} variables, avg neighbors: {sum(len(n) for n in constraint_neighbors.values())/len(constraint_neighbors):.1f}")
        
        def consistent(var_id, val):
            """Fast consistency check using cached timeslot assignments"""
            ts = val['timeslot']
            if ts not in assigned_by_timeslot:
                return True
            
            ts_data = assigned_by_timeslot[ts]
            # Check for instructor, room, AND section conflicts (friend's triple check!)
            var_sections = set(self.csp.meta[var_id]['sections'])
            
            if val['instructor'] in ts_data['instructor']:
                return False
            if val['room'] in ts_data['room']:
                return False
            # Check if any section in this variable's group is already assigned at this timeslot
            if var_sections & ts_data['sections']:
                return False
            return True

        def select_unassigned_var():
            """MRV + Degree heuristic (friend's implementation)"""
            unassigned = [v for v in self.csp.variables if v.variable_id not in assignment]
            if not unassigned:
                return None
            
            def heuristic(x):
                domain_size = len(local_domains.get(x.variable_id, []))
                if domain_size == 0:
                    return (0, 0)  # Dead end - prioritize to fail fast
                # Count unassigned neighbors
                unassigned_neighbors = sum(1 for n in constraint_neighbors.get(x.variable_id, []) 
                                        if n not in assignment)
                return (domain_size, -unassigned_neighbors)
            
            return min(unassigned, key=heuristic)
        
        def order_domain_values(var):
            """Order domain values - friend's simplified LCV"""
            domain_vals = local_domains.get(var.variable_id, [])
            
            # For small domains, return as-is
            if len(domain_vals) <= 10:
                return domain_vals
            
            # For larger domains, prioritize timeslots with fewer assignments
            def timeslot_score(val):
                ts = val['timeslot']
                ts_data = assigned_by_timeslot.get(ts, {})
                # Count resources already used in this timeslot
                used_count = len(ts_data.get('instructor', set())) + len(ts_data.get('room', set()))
                return used_count
            
            # Sort by timeslot usage (least constraining first)
            return sorted(domain_vals, key=timeslot_score)

        backtrack_calls = [0]
        max_depth = [0]
        
        def backtrack(depth=0):
            backtrack_calls[0] += 1
            max_depth[0] = max(max_depth[0], depth)
            
            # Check timeout
            if time.time() - self.start_time > timeout:
                return None
            
            # Update progress every 10 assignments
            if len(assignment) % 10 == 0:
                progress = len(assignment) / len(self.csp.variables)
                elapsed = time.time() - self.start_time
                progress_placeholder.info(
                    f"**Search Progress:** {len(assignment)}/{len(self.csp.variables)} "
                    f"({progress:.1%}) | Time: {elapsed:.1f}s | Backtracks: {self.backtrack_count}"
                )
            
            # Check if complete
            if len(assignment) == len(self.csp.variables):
                return assignment.copy()
            
            var = select_unassigned_var()
            if var is None:
                return None
            
            # Check if domain is empty (dead end)
            domain_vals = order_domain_values(var)
            if not domain_vals:
                return None
            
            for val in domain_vals:
                self.constraint_checks += 1
                
                if not consistent(var.variable_id, val):
                    continue
                
                # Make assignment
                assignment[var.variable_id] = val
                ts = val['timeslot']
                
                # Update timeslot tracking - add instructor, room, AND sections
                if ts not in assigned_by_timeslot:
                    assigned_by_timeslot[ts] = {'instructor': set(), 'room': set(), 'sections': set()}
                assigned_by_timeslot[ts]['instructor'].add(val['instructor'])
                assigned_by_timeslot[ts]['room'].add(val['room'])
                # Add all sections from this variable's group to the timeslot
                for section in self.csp.meta[var.variable_id]['sections']:
                    assigned_by_timeslot[ts]['sections'].add(section)
                
                removed = {}
                failure = False
                
                # Forward checking - prune inconsistent values from neighbor domains
                for neighbor_id in constraint_neighbors.get(var.variable_id, []):
                    if neighbor_id in assignment:
                        continue
                    
                    # Get sections for the neighbor variable
                    neighbor_sections = set(self.csp.meta[neighbor_id]['sections'])
                    
                    new_domain = []
                    for nval in local_domains.get(neighbor_id, []):
                        # Keep if different timeslot or no conflicts
                        if nval['timeslot'] != ts:
                            new_domain.append(nval)
                        elif (nval['instructor'] != val['instructor'] and 
                              nval['room'] != val['room'] and 
                              not (neighbor_sections & assigned_by_timeslot[ts]['sections'])):
                            new_domain.append(nval)
                    
                    if len(new_domain) == 0:
                        failure = True
                        break
                    
                    if len(new_domain) < len(local_domains[neighbor_id]):
                        removed[neighbor_id] = local_domains[neighbor_id]
                        local_domains[neighbor_id] = new_domain
                
                if not failure:
                    result = backtrack(depth + 1)
                    if result is not None:
                        return result
                
                # Restore domains
                for k, v in removed.items():
                    local_domains[k] = v
                
                # Restore timeslot tracking - remove instructor, room, AND sections
                assigned_by_timeslot[ts]['instructor'].discard(val['instructor'])
                assigned_by_timeslot[ts]['room'].discard(val['room'])
                for section in self.csp.meta[var.variable_id]['sections']:
                    assigned_by_timeslot[ts]['sections'].discard(section)
                if not assigned_by_timeslot[ts]['instructor'] and not assigned_by_timeslot[ts]['room'] and not assigned_by_timeslot[ts]['sections']:
                    del assigned_by_timeslot[ts]
                
                del assignment[var.variable_id]
                self.backtrack_count += 1
            
            return None

        st.info("🚀 Starting forward checking search...")
        success = backtrack()
        
        # Store performance metrics
        self.performance_metrics = {
            'backtrack_calls': backtrack_calls[0],
            'max_depth': max_depth[0],
            'constraint_checks': self.constraint_checks,
            'search_time': time.time() - self.start_time
        }
        
        st.info(f"✅ Search complete: {backtrack_calls[0]} backtracks, {max_depth[0]} max depth")
        
        return success

    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics"""
        return {
            'backtrack_count': self.backtrack_count,
            'constraint_checks': self.constraint_checks,
            'variables_assigned': len(self.solution) if self.solution else 0,
            'total_variables': len(self.csp.variables),
            'search_time': self.performance_metrics.get('search_time', 0),
            'backtrack_calls': self.performance_metrics.get('backtrack_calls', 0),
            'max_depth': self.performance_metrics.get('max_depth', 0),
            'completion_percentage': (len(self.solution) / len(self.csp.variables) * 100) if self.solution else 0
        }