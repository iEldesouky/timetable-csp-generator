# csp_model.py - CORRECTED VERSION

from typing import Dict, List, Tuple, Set, Any, Optional
from dataclasses import dataclass
import pandas as pd
import streamlit as st

@dataclass
class CSPVariable:
    """
    Represents a variable in our CSP - a course activity that needs scheduling
    Matches the exact structure from Excel files
    """
    variable_id: str           # Format: "COURSEID_TYPE_YEAR_GROUP_SECTION"
    course_id: str            # Course ID from Courses.csv
    activity_type: str        # "Lecture", "Lab", "Tutorial"
    year: int                # Year from Sections.csv
    group_number: int        # Group number from Sections.csv  
    section_id: int          # Section ID from Sections.csv
    student_count: int       # Number of students

class TimetableCSP:
    """
    Main CSP model for CSIT timetable generation using exact Excel structure
    """
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.variables: List[CSPVariable] = []
        self.domains: Dict[str, List[Tuple]] = {}  # variable_id -> [(timeslot_id, room_id, instructor_id)]
        self.assignments: Dict[str, Tuple] = {}    # Current assignments
        self.elective_pairs: List[Tuple[str, str]] = []
        
        # Initialize the CSP
        self._initialize_csp()
    
    def _initialize_csp(self):
        """Initialize CSP variables based on exact Excel structure"""
        try:
            self.variables = []
            
            # Validate data
            if (self.data_loader.sections_df is None or 
                self.data_loader.courses_df is None or 
                self.data_loader.curriculum_df is None):
                st.error("❌ Missing required data: sections, courses, or curriculum")
                return
            
            # Create variables for each section and their courses
            for _, section in self.data_loader.sections_df.iterrows():
                section_id = section['section_id']
                group_number = section['group_number']
                year = section['year']
                student_count = section['student_count']
                
                # Get courses for this year from curriculum
                year_courses = self.data_loader.get_courses_for_year(year)
                
                for course_id in year_courses:
                    # Get course details
                    course_data = self.data_loader.courses_df[
                        self.data_loader.courses_df['course_id'] == course_id
                    ]
                    
                    if course_data.empty:
                        st.warning(f"⚠️ Course {course_id} not found in courses database")
                        continue
                    
                    course_info = course_data.iloc[0]
                    course_type = course_info['type']
                    
                    # Create variables based on course type
                    if 'Lecture' in course_type:
                        # Create lecture variable for the GROUP (all sections in group attend)
                        lecture_var_id = f"{course_id}_LEC_{year}_{group_number}"
                        if not any(v.variable_id == lecture_var_id for v in self.variables):
                            # Calculate total students in group
                            group_sections = self.data_loader.sections_df[
                                (self.data_loader.sections_df['year'] == year) & 
                                (self.data_loader.sections_df['group_number'] == group_number)
                            ]
                            group_student_count = group_sections['student_count'].sum()
                            
                            variable = CSPVariable(
                                variable_id=lecture_var_id,
                                course_id=course_id,
                                activity_type="Lecture",
                                year=year,
                                group_number=group_number,
                                section_id=group_number,  # Use group number as section ID for lectures
                                student_count=group_student_count
                            )
                            self.variables.append(variable)
                    
                    if 'Lab' in course_type:
                        # Create lab variable for individual SECTION
                        lab_var_id = f"{course_id}_LAB_{year}_{group_number}_{section_id}"
                        variable = CSPVariable(
                            variable_id=lab_var_id,
                            course_id=course_id,
                            activity_type="Lab", 
                            year=year,
                            group_number=group_number,
                            section_id=section_id,
                            student_count=student_count
                        )
                        self.variables.append(variable)
                    
                    if 'Tutorial' in course_type:
                        # Create tutorial variable for individual SECTION
                        tutorial_var_id = f"{course_id}_TUT_{year}_{group_number}_{section_id}"
                        variable = CSPVariable(
                            variable_id=tutorial_var_id,
                            course_id=course_id,
                            activity_type="Tutorial",
                            year=year,
                            group_number=group_number,
                            section_id=section_id,
                            student_count=student_count
                        )
                        self.variables.append(variable)
            
            # Identify elective pairs (LRA104 and LRA105 for Year 1)
            self._identify_elective_pairs()
            
            # Initialize domains
            self._initialize_domains()
            
            st.success(f"✅ CSP Initialized: {len(self.variables)} variables created")
            
            # Show breakdown
            lecture_count = sum(1 for v in self.variables if v.activity_type == "Lecture")
            lab_count = sum(1 for v in self.variables if v.activity_type == "Lab")
            tutorial_count = sum(1 for v in self.variables if v.activity_type == "Tutorial")
            
            st.info(f"   - Lectures: {lecture_count}")
            st.info(f"   - Labs: {lab_count}") 
            st.info(f"   - Tutorials: {tutorial_count}")
            
        except Exception as e:
            st.error(f"❌ Error initializing CSP: {str(e)}")
            import traceback
            st.error(f"Debug: {traceback.format_exc()}")
    
    def _identify_elective_pairs(self):
        """Identify pairs of elective courses that should be scheduled simultaneously"""
        # LRA104 and LRA105 for Year 1 should be at same time
        self.elective_pairs = [("LRA104", "LRA105")]
        st.info(f"✅ Identified {len(self.elective_pairs)} elective course pairs")
    
    def _initialize_domains(self):
        """Create initial domains for each variable"""
        try:
            self.domains = {}
            
            # Validate data
            if (self.data_loader.timeslots_df is None or 
                self.data_loader.rooms_df is None or 
                self.data_loader.instructors_df is None):
                st.error("❌ Missing timeslots, rooms, or instructors data")
                return
            
            variables_with_empty_domains = []
            
            for variable in self.variables:
                domain = []
                course_id = variable.course_id
                activity_type = variable.activity_type
                student_count = variable.student_count
                
                # Generate all possible valid combinations
                for _, timeslot in self.data_loader.timeslots_df.iterrows():
                    timeslot_id = timeslot['time_slot_id']
                    
                    # Get compatible rooms
                    compatible_rooms = self.data_loader.get_compatible_rooms(activity_type, student_count)
                    
                    if not compatible_rooms:
                        continue
                    
                    # Get qualified instructors
                    qualified_instructors = self.data_loader.get_qualified_instructors(course_id)
                    
                    if not qualified_instructors:
                        continue
                    
                    # Generate all combinations
                    for room_id in compatible_rooms:
                        for instructor_id in qualified_instructors:
                            domain.append((timeslot_id, room_id, instructor_id))
                
                self.domains[variable.variable_id] = domain
                
                if len(domain) == 0:
                    variables_with_empty_domains.append(variable.variable_id)
                    st.warning(f"⚠️ Variable {variable.variable_id} has empty domain!")
            
            if variables_with_empty_domains:
                st.error(f"❌ {len(variables_with_empty_domains)} variables have empty domains")
                
            total_domain_size = sum(len(d) for d in self.domains.values())
            st.info(f"✅ Domains initialized: {total_domain_size} total possibilities")
            
        except Exception as e:
            st.error(f"❌ Error initializing domains: {str(e)}")
    
    def is_complete(self) -> bool:
        """Check if all variables are assigned"""
        return len(self.assignments) == len(self.variables)
    
    def get_unassigned_variables(self) -> List[CSPVariable]:
        """Get list of unassigned variables"""
        return [var for var in self.variables if var.variable_id not in self.assignments]
    
    def get_variable_by_id(self, variable_id: str) -> Optional[CSPVariable]:
        """Get variable by its ID"""
        for var in self.variables:
            if var.variable_id == variable_id:
                return var
        return None
    
    def print_debug_info(self):
        """Print debug information about the CSP"""
        st.subheader("🔍 CSP Debug Information")
        
        st.write(f"**Total Variables:** {len(self.variables)}")
        
        # Variable breakdown
        lecture_vars = [v for v in self.variables if v.activity_type == "Lecture"]
        lab_vars = [v for v in self.variables if v.activity_type == "Lab"]
        tutorial_vars = [v for v in self.variables if v.activity_type == "Tutorial"]
        
        st.write(f"- Lectures: {len(lecture_vars)}")
        st.write(f"- Labs: {len(lab_vars)}")
        st.write(f"- Tutorials: {len(tutorial_vars)}")
        
        # Domain sizes
        domain_sizes = [len(domain) for domain in self.domains.values()]
        st.write(f"**Domain Sizes:**")
        st.write(f"- Min: {min(domain_sizes) if domain_sizes else 0}")
        st.write(f"- Max: {max(domain_sizes) if domain_sizes else 0}")
        st.write(f"- Average: {sum(domain_sizes)/len(domain_sizes) if domain_sizes else 0:.1f}")
        
        # Variables with empty domains
        empty_domains = [var_id for var_id, domain in self.domains.items() if len(domain) == 0]
        if empty_domains:
            st.error(f"❌ {len(empty_domains)} variables have empty domains!")
            for var_id in empty_domains[:5]:  # Show first 5
                st.write(f"  - {var_id}")
        
        # Show first few variables and their domain sizes
        st.write("**Sample Variables:**")
        for i, variable in enumerate(self.variables[:5]):
            domain_size = len(self.domains.get(variable.variable_id, []))
            st.write(f"- {variable.variable_id}: {domain_size} possible assignments")
    
    def get_assignment_summary(self) -> Dict:
        """Get summary of current assignments"""
        lectures_assigned = sum(1 for var_id in self.assignments if "_LEC_" in var_id)
        labs_assigned = sum(1 for var_id in self.assignments if "_LAB_" in var_id)
        tutorials_assigned = sum(1 for var_id in self.assignments if "_TUT_" in var_id)
        
        return {
            'assigned': len(self.assignments),
            'total': len(self.variables),
            'lectures_assigned': lectures_assigned,
            'labs_assigned': labs_assigned,
            'tutorials_assigned': tutorials_assigned,
            'completion': f"{len(self.assignments)}/{len(self.variables)}"
        }