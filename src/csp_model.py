from typing import Dict, List, Tuple, Set, Any, Optional
from dataclasses import dataclass
import pandas as pd

@dataclass
class CSPVariable:
    """
    Represents a variable in our CSP - a course section that needs scheduling
    """
    variable_id: str           # Unique identifier: "CSC111_S1"
    course_id: str            # Course ID: "CSC111"
    section_id: str           # Section ID: "S1"
    course_type: str          # "Lecture", "Lab", "Lecture and Lab"
    required_slots: int       # Number of time slots needed per week

class TimetableCSP:
    """
    Main CSP model for timetable generation
    Implements professional CSP formulation according to CS188 principles
    """
    
    def __init__(self, data_loader):
        """
        Initialize CSP with data from DataLoader
        """
        self.data_loader = data_loader
        
        # Core CSP components
        self.variables: List[CSPVariable] = []
        self.domains: Dict[str, List[Tuple]] = {}  # variable_id -> [(timeslot, room, instructor)]
        self.assignments: Dict[str, Tuple] = {}    # Current assignments
        
        # Optimization tracking
        self.backtrack_count = 0
        self.domain_pruning_count = 0
        
        # Initialize the CSP
        self._initialize_csp()
    
    def _initialize_csp(self):
        """
        Step 1: Create CSP variables from course sections
        Each variable = one course section that needs scheduling
        """
        self.variables = []
        
        for _, section in self.data_loader.sections_df.iterrows():
            course_id = section['CourseID']
            course_info = self.data_loader.courses_df[
                self.data_loader.courses_df['CourseID'] == course_id
            ].iloc[0]
            
            variable = CSPVariable(
                variable_id=section['SectionID'],
                course_id=course_id,
                section_id=section['SectionID'].split('_')[-1],
                course_type=course_info['Type'],
                required_slots=1  # Each section needs one time slot
            )
            self.variables.append(variable)
        
        # Step 2: Initialize domains for each variable
        self._initialize_domains()
        
        print(f"✅ CSP Initialized: {len(self.variables)} variables, domains size: {sum(len(d) for d in self.domains.values())} total possibilities")
    
    def _initialize_domains(self):
        """
        Step 2: Create initial domains for each variable
        Domain = all possible (timeslot, room, instructor) combinations
        that satisfy basic unary constraints
        """
        self.domains = {}
        
        for variable in self.variables:
            domain = []
            course_id = variable.course_id
            course_type = variable.course_type
            
            # Generate all possible valid combinations
            for _, timeslot in self.data_loader.timeslots_df.iterrows():
                timeslot_id = timeslot['TimeslotID']
                
                # Get compatible rooms based on course type
                compatible_rooms = self._get_compatible_rooms(course_type)
                
                # Get qualified instructors for this course
                qualified_instructors = self._get_qualified_instructors(course_id)
                
                # Generate all combinations
                for room_id in compatible_rooms:
                    for instructor_id in qualified_instructors:
                        # Check basic instructor availability
                        if self._is_instructor_available(instructor_id, timeslot_id):
                            domain.append((timeslot_id, room_id, instructor_id))
            
            self.domains[variable.variable_id] = domain
            
            if len(domain) == 0:
                print(f"⚠️ Warning: Variable {variable.variable_id} has empty domain!")
    
    def _get_compatible_rooms(self, course_type: str) -> List[str]:
        """
        Find rooms compatible with course type
        - Lab courses need lab rooms
        - Lecture courses need lecture rooms
        - Lecture and Lab courses prefer lab rooms
        """
        rooms_df = self.data_loader.rooms_df
        
        if course_type == "Lab":
            return rooms_df[rooms_df['Type'] == 'Lab']['RoomID'].tolist()
        elif course_type == "Lecture":
            return rooms_df[rooms_df['Type'] == 'Lecture']['RoomID'].tolist()
        else:  # "Lecture and Lab"
            # Prefer lab rooms for mixed types, but allow lecture rooms as fallback
            lab_rooms = rooms_df[rooms_df['Type'] == 'Lab']['RoomID'].tolist()
            if lab_rooms:
                return lab_rooms
            else:
                return rooms_df[rooms_df['Type'] == 'Lecture']['RoomID'].tolist()
    
    def _get_qualified_instructors(self, course_id: str) -> List[str]:
        """
        Find instructors qualified to teach this course
        """
        qualified = []
        for _, instructor in self.data_loader.instructors_df.iterrows():
            if course_id in instructor['QualifiedCourses']:
                qualified.append(instructor['InstructorID'])
        return qualified
    
    def _is_instructor_available(self, instructor_id: str, timeslot_id: str) -> bool:
        """
        Check if instructor is available at this timeslot
        Based on their 'Not on [Day]' preference
        """
        instructor = self.data_loader.instructors_df[
            self.data_loader.instructors_df['InstructorID'] == instructor_id
        ].iloc[0]
        
        unavailable_day = instructor.get('UnavailableDay', '')
        if pd.isna(unavailable_day):
            return True
        
        # Extract day from timeslot (e.g., "Monday 9:00 AM-10:30 AM" -> "Monday")
        timeslot_day = timeslot_id.split()[0]
        
        return timeslot_day != unavailable_day
    
    def is_complete(self) -> bool:
        """Check if all variables are assigned"""
        return len(self.assignments) == len(self.variables)
    
    def get_unassigned_variables(self) -> List[CSPVariable]:
        """Get list of unassigned variables"""
        return [var for var in self.variables if var.variable_id not in self.assignments]
    
    def get_domain_size(self, variable_id: str) -> int:
        """Get current domain size for a variable"""
        return len(self.domains.get(variable_id, []))
    
    def get_assignment_summary(self) -> Dict:
        """Get summary of current assignments"""
        return {
            'assigned': len(self.assignments),
            'total': len(self.variables),
            'completion': f"{len(self.assignments)}/{len(self.variables)}",
            'backtracks': self.backtrack_count
        }