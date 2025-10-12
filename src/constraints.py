from typing import Dict, List, Tuple, Set
import pandas as pd

class HardConstraints:
    """
    Implementation of hard constraints that MUST be satisfied
    These make solutions valid/invalid
    """
    
    @staticmethod
    def check_all_constraints(assignment: Dict, new_variable: str, new_value: Tuple, csp) -> bool:
        """
        Check all hard constraints for a new assignment
        Returns: True if all constraints satisfied, False otherwise
        """
        new_timeslot, new_room, new_instructor = new_value
        
        # Constraint 1: No instructor double-booking
        if not HardConstraints.no_instructor_double_booking(assignment, new_variable, new_value):
            return False
        
        # Constraint 2: No room double-booking
        if not HardConstraints.no_room_double_booking(assignment, new_variable, new_value):
            return False
        
        # Constraint 3: Room type compatibility (handled in domain initialization)
        # Constraint 4: Instructor qualification (handled in domain initialization)
        
        return True
    
    @staticmethod
    def no_instructor_double_booking(assignment: Dict, new_variable: str, new_value: Tuple) -> bool:
        """
        Constraint 1: No instructor can teach two classes simultaneously
        """
        new_timeslot, _, new_instructor = new_value
        
        for existing_var, existing_value in assignment.items():
            existing_timeslot, _, existing_instructor = existing_value
            
            # If same instructor and same timeslot → violation
            if existing_instructor == new_instructor and existing_timeslot == new_timeslot:
                return False
        
        return True
    
    @staticmethod
    def no_room_double_booking(assignment: Dict, new_variable: str, new_value: Tuple) -> bool:
        """
        Constraint 2: No room can host two classes simultaneously
        """
        new_timeslot, new_room, _ = new_value
        
        for existing_var, existing_value in assignment.items():
            existing_timeslot, existing_room, _ = existing_value
            
            if existing_room == new_room and existing_timeslot == new_timeslot:
                return False
        
        return True

class SoftConstraints:
    """
    Soft constraints for optimization - preferences that improve solution quality
    These don't make solutions invalid, but we prefer lower penalty scores
    """
    
    @staticmethod
    def calculate_solution_penalty(assignment: Dict, csp) -> int:
        """
        Calculate total penalty for soft constraint violations
        Lower penalty = better solution
        """
        penalty = 0
        
        # Penalty for instructor teaching on unavailable days (should be handled in hard constraints)
        penalty += SoftConstraints._instructor_preference_penalty(assignment, csp)
        
        # Penalty for unbalanced distribution across days
        penalty += SoftConstraints._daily_distribution_penalty(assignment, csp)
        
        # Penalty for using extreme time slots (very early or very late)
        penalty += SoftConstraints._time_preference_penalty(assignment, csp)
        
        return penalty
    
    @staticmethod
    def _instructor_preference_penalty(assignment: Dict, csp) -> int:
        """
        Penalize assignments that go against instructor preferences
        """
        penalty = 0
        # This is mainly handled in hard constraints via domain reduction
        return penalty
    
    @staticmethod
    def _daily_distribution_penalty(assignment: Dict, csp) -> int:
        """
        Penalize unbalanced distribution of classes across weekdays
        """
        day_counts = {}
        
        for _, value in assignment.items():
            timeslot, _, _ = value
            day = timeslot.split()[0]  # Extract day name
            
            day_counts[day] = day_counts.get(day, 0) + 1
        
        # Calculate penalty based on distribution unevenness
        if day_counts:
            avg_classes = sum(day_counts.values()) / len(day_counts)
            penalty = sum(abs(count - avg_classes) for count in day_counts.values())
            return int(penalty)
        
        return 0
    
    @staticmethod
    def _time_preference_penalty(assignment: Dict, csp) -> int:
        """
        Penalize use of undesirable time slots
        """
        penalty = 0
        
        for _, value in assignment.items():
            timeslot, _, _ = value
            
            # Penalize very early (8 AM) or very late (after 3 PM) classes
            if '8:00' in timeslot or '3:45' in timeslot:
                penalty += 2
            elif '9:00' in timeslot or '2:15' in timeslot:
                penalty += 1
        
        return penalty

class ForwardChecking:
    """
    Forward checking constraint propagation
    Reduces domains of unassigned variables when new assignments are made
    """
    
    @staticmethod
    def do_forward_checking(assignment: Dict, variable: str, value: Tuple, domains: Dict, csp) -> bool:
        """
        Perform forward checking after assignment
        Returns: True if consistent, False if domain wipeout detected
        """
        new_timeslot, new_room, new_instructor = value
        
        for unassigned_var in csp.get_unassigned_variables():
            unassigned_id = unassigned_var.variable_id
            original_domain_size = len(domains[unassigned_id])
            
            # Remove inconsistent values from domain
            domains[unassigned_id] = [
                val for val in domains[unassigned_id]
                if ForwardChecking._is_value_consistent(val, new_timeslot, new_room, new_instructor)
            ]
            
            # Check for domain wipeout
            if len(domains[unassigned_id]) == 0:
                return False
        
        return True
    
    @staticmethod
    def _is_value_consistent(value: Tuple, new_timeslot: str, new_room: str, new_instructor: str) -> bool:
        """
        Check if a value is consistent with the new assignment
        """
        timeslot, room, instructor = value
        
        # Inconsistent if same timeslot and same instructor
        if timeslot == new_timeslot and instructor == new_instructor:
            return False
        
        # Inconsistent if same timeslot and same room
        if timeslot == new_timeslot and room == new_room:
            return False
        
        return True