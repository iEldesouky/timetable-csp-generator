# constraints.py - CORRECTED VERSION

from typing import Dict, List, Tuple, Set
import pandas as pd

class HardConstraints:
    """
    Hard constraints that MUST be satisfied for CSIT timetable
    """
    
    @staticmethod
    def check_all_constraints(assignment: Dict, new_variable: str, new_value: Tuple, csp) -> bool:
        """
        Check all hard constraints for a new assignment
        """
        new_timeslot, new_room, new_instructor = new_value
        
        # Get the variable object
        var = csp.get_variable_by_id(new_variable)
        if not var:
            return False

        # Constraint 1: No instructor double-booking
        if not HardConstraints.no_instructor_double_booking(assignment, new_variable, new_value):
            return False
        
        # Constraint 2: No room double-booking  
        if not HardConstraints.no_room_double_booking(assignment, new_variable, new_value):
            return False
        
        # Constraint 3: Room capacity check
        if not HardConstraints.room_capacity_constraint(var, new_room, csp):
            return False
        
        # Constraint 4: Room type compatibility
        if not HardConstraints.room_type_constraint(var, new_room, csp):
            return False
        
        # Constraint 5: Elective course coordination
        if not HardConstraints.elective_coordination_constraint(assignment, new_variable, new_value, csp):
            return False
        
        # Constraint 6: Same course lectures for same group
        if not HardConstraints.same_course_lecture_constraint(assignment, new_variable, new_value, csp):
            return False

        return True
    
    @staticmethod
    def no_instructor_double_booking(assignment: Dict, new_variable: str, new_value: Tuple) -> bool:
        """No instructor can teach two classes simultaneously"""
        new_timeslot, _, new_instructor = new_value
        
        for existing_var, existing_value in assignment.items():
            existing_timeslot, _, existing_instructor = existing_value
            
            if existing_instructor == new_instructor and existing_timeslot == new_timeslot:
                return False
        
        return True
    
    @staticmethod
    def no_room_double_booking(assignment: Dict, new_variable: str, new_value: Tuple) -> bool:
        """No room can host two classes simultaneously"""
        new_timeslot, new_room, _ = new_value
        
        for existing_var, existing_value in assignment.items():
            existing_timeslot, existing_room, _ = existing_value
            
            if existing_room == new_room and existing_timeslot == new_timeslot:
                return False
        
        return True
    
    @staticmethod
    def room_capacity_constraint(variable, room_id: str, csp) -> bool:
        """Room must have sufficient capacity for students"""
        room_capacity = csp.data_loader.get_room_capacity(room_id)
        return room_capacity >= variable.student_count
    
    @staticmethod
    def room_type_constraint(variable, room_id: str, csp) -> bool:
        """Room type must match activity type"""
        if csp.data_loader.rooms_df is None:
            return True
            
        room_data = csp.data_loader.rooms_df[csp.data_loader.rooms_df['room_id'] == room_id]
        if room_data.empty:
            return False
            
        room_type = room_data['type'].iloc[0]
        activity_type = variable.activity_type
        
        # Map activity types to room types
        activity_to_room = {
            'Lecture': 'Lecture',
            'Lab': 'Lab',
            'Tutorial': 'Tutorial'
        }
        
        required_room_type = activity_to_room.get(activity_type, 'Lecture')
        return room_type == required_room_type
    
    @staticmethod
    def elective_coordination_constraint(assignment: Dict, new_variable: str, new_value: Tuple, csp) -> bool:
        """Elective courses should be scheduled simultaneously"""
        new_timeslot, _, _ = new_value
        var = csp.get_variable_by_id(new_variable)
        
        if not var:
            return True
        
        course_id = var.course_id
        
        # Check if this course is part of an elective pair
        for elective1, elective2 in csp.elective_pairs:
            if course_id == elective1 or course_id == elective2:
                other_elective = elective2 if course_id == elective1 else elective1
                
                # Check if any section of the other elective is already scheduled
                for assigned_var, assigned_value in assignment.items():
                    assigned_var_obj = csp.get_variable_by_id(assigned_var)
                    if assigned_var_obj and assigned_var_obj.course_id == other_elective:
                        assigned_timeslot, _, _ = assigned_value
                        if assigned_timeslot != new_timeslot:
                            return False
        
        return True
    
    @staticmethod
    def same_course_lecture_constraint(assignment: Dict, new_variable: str, new_value: Tuple, csp) -> bool:
        """Same course lectures for different groups should be coordinated"""
        var = csp.get_variable_by_id(new_variable)
        
        if not var or var.activity_type != "Lecture":
            return True
        
        new_timeslot, _, new_instructor = new_value
        course_id = var.course_id
        year = var.year
        
        # Find all lecture variables for same course and year (different groups)
        for variable in csp.variables:
            if (variable.activity_type == "Lecture" and 
                variable.course_id == course_id and 
                variable.year == year and
                variable.variable_id != new_variable and
                variable.variable_id in assignment):
                
                assigned_timeslot, _, assigned_instructor = assignment[variable.variable_id]
                
                # Should have same timeslot and instructor for consistency
                if assigned_timeslot != new_timeslot or assigned_instructor != new_instructor:
                    return False
        
        return True

class SoftConstraints:
    """
    Soft constraints for optimization
    """
    
    @staticmethod
    def calculate_solution_penalty(assignment: Dict, csp) -> int:
        """Calculate total penalty for soft constraint violations"""
        penalty = 0
        
        # Penalty for unbalanced distribution across days
        penalty += SoftConstraints._daily_distribution_penalty(assignment, csp)
        
        # Penalty for using extreme time slots
        penalty += SoftConstraints._time_preference_penalty(assignment, csp)
        
        # Penalty for instructor overload
        penalty += SoftConstraints._instructor_workload_penalty(assignment, csp)
        
        return penalty
    
    @staticmethod
    def _daily_distribution_penalty(assignment: Dict, csp) -> int:
        """Penalize unbalanced distribution of classes across weekdays"""
        day_counts = {}
        
        for _, value in assignment.items():
            timeslot, _, _ = value
            day = timeslot.split('_')[0]  # Extract day from timeslot_id like "sun_9:00_10:30"
            
            day_counts[day] = day_counts.get(day, 0) + 1
        
        # Calculate penalty based on distribution unevenness
        if day_counts:
            avg_classes = sum(day_counts.values()) / len(day_counts)
            penalty = sum(abs(count - avg_classes) for count in day_counts.values())
            return int(penalty * 2)
        
        return 0
    
    @staticmethod
    def _time_preference_penalty(assignment: Dict, csp) -> int:
        """Penalize use of undesirable time slots"""
        penalty = 0
        
        for _, value in assignment.items():
            timeslot, _, _ = value
            
            # Penalize very early (8 AM) or very late (after 3 PM) classes
            if '8:00' in timeslot:
                penalty += 3
            elif '15:45' in timeslot or '16:' in timeslot:
                penalty += 3
            elif '9:00' in timeslot:
                penalty += 1
        
        return penalty
    
    @staticmethod
    def _instructor_workload_penalty(assignment: Dict, csp) -> int:
        """Penalize uneven distribution of classes among instructors"""
        instructor_counts = {}
        
        for _, value in assignment.items():
            _, _, instructor_id = value
            instructor_counts[instructor_id] = instructor_counts.get(instructor_id, 0) + 1
        
        if instructor_counts:
            avg_workload = sum(instructor_counts.values()) / len(instructor_counts)
            penalty = sum(abs(count - avg_workload) for count in instructor_counts.values())
            return int(penalty)
        
        return 0

class ForwardChecking:
    """
    Forward checking constraint propagation
    """
    
    @staticmethod
    def do_forward_checking(assignment: Dict, variable: str, value: Tuple, domains: Dict, csp) -> bool:
        """Perform forward checking after assignment"""
        new_timeslot, new_room, new_instructor = value
        
        for unassigned_var in csp.get_unassigned_variables():
            unassigned_id = unassigned_var.variable_id
            
            # Remove inconsistent values from domain
            domains[unassigned_id] = [
                val for val in domains[unassigned_id]
                if ForwardChecking._is_value_consistent(val, new_timeslot, new_room, new_instructor, csp)
            ]
            
            # Check for domain wipeout
            if len(domains[unassigned_id]) == 0:
                return False
        
        return True
    
    @staticmethod
    def _is_value_consistent(value: Tuple, new_timeslot: str, new_room: str, new_instructor: str, csp) -> bool:
        """Check if a value is consistent with the new assignment"""
        timeslot, room, instructor = value
        
        # Basic double-booking constraints
        if timeslot == new_timeslot:
            if instructor == new_instructor:  # Same instructor
                return False
            if room == new_room:  # Same room
                return False
        
        return True