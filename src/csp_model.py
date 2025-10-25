# [file name]: new_csp.py
import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Set, Any, Optional
from dataclasses import dataclass
import itertools
from collections import defaultdict

@dataclass
class CSPVariable:
    """Represents a course-group-session variable following friend's working model"""
    variable_id: str           # Format: "COURSE::G0::Lecture"
    course_id: str            # Course ID
    activity_type: str        # "Lecture", "Lab", "TUT"
    year: int                # Year level
    group_index: int         # Group index (0, 1, 2...)
    sections: List[str]      # List of sections in this group
    student_count: int       # Total students in group

class TimetableCSP:
    """
    NEW CSP model based on friend's working architecture
    """
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.variables: List[CSPVariable] = []
        self.domains: Dict[str, List[Dict]] = {}  # variable_id -> [{'timeslot': (), 'room': '', 'instructor': ''}]
        self.assignments: Dict[str, Dict] = {}    # Current assignments
        self.course_to_section_groups: Dict = {}  # Course -> session_type -> groups
        self.meta: Dict = {}                      # Variable metadata
        
        # Initialize the CSP
        self._initialize_csp()
    
    def _initialize_csp(self):
        """Initialize CSP using friend's working logic"""
        try:
            # Build course to section groups mapping
            self._build_course_section_mapping()
            
            # Create variables for each course-group-session combination
            self._create_variables()
            
            # Initialize domains
            self._initialize_domains()
            
            st.success(f"✅ CSP Initialized: {len(self.variables)} variables created")
            
            # Show breakdown
            lecture_count = sum(1 for v in self.variables if v.activity_type == "Lecture")
            lab_count = sum(1 for v in self.variables if v.activity_type == "Lab") 
            tut_count = sum(1 for v in self.variables if v.activity_type == "TUT")
            
            st.info(f"   - Lectures: {lecture_count}")
            st.info(f"   - Labs: {lab_count}")
            st.info(f"   - Tutorials: {tut_count}")
            
        except Exception as e:
            st.error(f"❌ Error initializing CSP: {str(e)}")
            import traceback
            st.error(f"Debug: {traceback.format_exc()}")
    
    # In new_csp.py - FIX the _build_course_section_mapping method:

def _build_course_section_mapping(self):
    """Build mapping from courses to section groups (friend's direct mapping)"""
    self.course_to_section_groups = defaultdict(dict)
    
    for _, course in self.data_loader.courses_df.iterrows():
        course_id = course['CourseID']
        course_year = course.get('Year', 1)  # Get year from course, not curriculum
        
        # Find ALL sections that match this course based on year/department
        matching_sections = self._find_matching_sections(course_id, course_year)
        
        if matching_sections:
            # Parse course type to determine session types needed
            course_type = course.get('Type', 'Lecture')
            course_type_lower = course_type.lower()
            
            # Create groups for each session type (friend's grouping logic)
            if 'lecture' in course_type_lower:
                self.course_to_section_groups[course_id]['Lecture'] = self._create_section_groups(matching_sections, 'Lecture')
            if 'lab' in course_type_lower:
                self.course_to_section_groups[course_id]['Lab'] = self._create_section_groups(matching_sections, 'Lab')
            if 'tut' in course_type_lower:
                self.course_to_section_groups[course_id]['TUT'] = self._create_section_groups(matching_sections, 'TUT')
            
            # Default to lecture if no session type specified
            if not self.course_to_section_groups[course_id]:
                self.course_to_section_groups[course_id]['Lecture'] = self._create_section_groups(matching_sections, 'Lecture')
    
    def _find_matching_sections(self, course_id: str, course_year: int) -> List[str]:
        """Find sections that match this course based on year and department rules"""
        matching_sections = []
        
        if self.data_loader.sections_df is None:
            return []
        
        for _, section in self.data_loader.sections_df.iterrows():
            section_id = str(section['SectionID'])
            
            # Apply friend's section matching logic
            if self._can_assign_course_to_section(course_id, section_id, course_year):
                matching_sections.append(section_id)
        
        return matching_sections
    
    def _can_assign_course_to_section(self, course_id: str, section_id: str, course_year: int) -> bool:
        """Friend's course-section assignment logic"""
        if not section_id or '/' not in str(section_id):
            return True
        
        parts = str(section_id).split('/')
        if len(parts) < 2:
            return True
        
        try:
            section_year = int(parts[0].strip())
        except ValueError:
            return True
        
        # Check year matching
        if course_year != section_year:
            return False
        
        # Years 1-2: only year matching required
        if course_year in [1, 2]:
            return True
        
        # Years 3-4: department matching required
        if course_year in [3, 4]:
            course_dept = course_id[:3].upper() if len(course_id) >= 3 else ""
            section_dept = parts[1].strip().upper() if len(parts) >= 2 else ""
            return course_dept == section_dept
        
        return True
    
    def _create_section_groups(self, sections: List[str], session_type: str) -> List[List[str]]:
        """Friend's section grouping logic"""
        if session_type == 'TUT':
            group_size = 1  # Individual sections
        elif session_type == 'Lab':
            group_size = 2  # Pairs of sections
        else:  # Lecture
            group_size = 4 if len(sections) % 2 == 0 else 3  # 3-4 sections
        
        groups = []
        for i in range(0, len(sections), group_size):
            group = sections[i:i+group_size]
            groups.append(group)
        
        return groups
    
    def _create_variables(self):
        """Create CSP variables following friend's model"""
        self.variables = []
        
        for course_id, session_groups in self.course_to_section_groups.items():
            for session_type, groups in session_groups.items():
                for group_idx, section_group in enumerate(groups):
                    # Create variable ID: "COURSE::G0::Lecture"
                    var_id = f"{course_id}::G{group_idx}::{session_type}"
                    
                    # Calculate total students in group
                    student_count = self._calculate_group_student_count(section_group)
                    
                    variable = CSPVariable(
                        variable_id=var_id,
                        course_id=course_id,
                        activity_type=session_type,
                        year=self._get_course_year(course_id),
                        group_index=group_idx,
                        sections=section_group,
                        student_count=student_count
                    )
                    
                    self.variables.append(variable)
                    
                    # Store metadata
                    self.meta[var_id] = {
                        'course': course_id,
                        'group_index': group_idx,
                        'sections': section_group,
                        'type': self._get_course_type(course_id)
                    }
    
    def _calculate_group_student_count(self, sections: List[str]) -> int:
        """Calculate total students across all sections in group"""
        if self.data_loader.sections_df is None:
            return 30  # Default
        
        total = 0
        for section_id in sections:
            section_data = self.data_loader.sections_df[
                self.data_loader.sections_df['SectionID'].astype(str) == section_id
            ]
            if not section_data.empty:
                total += section_data.iloc[0].get('Capacity', 30)
        return total
    
    def _get_course_year(self, course_id: str) -> int:
        """Get course year from courses dataframe"""
        course_data = self.data_loader.courses_df[
            self.data_loader.courses_df['CourseID'] == course_id
        ]
        return course_data.iloc[0].get('Year', 1) if not course_data.empty else 1
    
    def _get_course_type(self, course_id: str) -> str:
        """Get course type from courses dataframe"""
        course_data = self.data_loader.courses_df[
            self.data_loader.courses_df['CourseID'] == course_id
        ]
        return course_data.iloc[0].get('Type', 'Lecture') if not course_data.empty else 'Lecture'
    
    def _initialize_domains(self):
        """Initialize domains using friend's domain building logic"""
        try:
            self.domains = {}
            
            # Get available resources
            timeslots = self._get_timeslots()
            rooms = list(self.data_loader.rooms_df.to_dict('records')) if self.data_loader.rooms_df is not None else []
            instructors = list(self.data_loader.instructors_df.to_dict('records')) if self.data_loader.instructors_df is not None else []
            
            # Build domains for each variable
            for variable in self.variables:
                domain = self._build_domain_for_variable(variable, timeslots, rooms, instructors)
                self.domains[variable.variable_id] = domain
            
            # Report domain statistics
            total_domain_size = sum(len(d) for d in self.domains.values())
            empty_domains = [v.variable_id for v in self.variables if len(self.domains.get(v.variable_id, [])) == 0]
            
            st.info(f"✅ Domains initialized: {total_domain_size} total possibilities")
            if empty_domains:
                st.warning(f"⚠️ {len(empty_domains)} variables have empty domains")
            
        except Exception as e:
            st.error(f"❌ Error initializing domains: {str(e)}")
    
    def _get_timeslots(self) -> List[Tuple]:
        """Extract timeslots from timeslots dataframe"""
        timeslots = []
        if self.data_loader.timeslots_df is not None:
            for _, row in self.data_loader.timeslots_df.iterrows():
                timeslot = (row['Day'], row['StartTime'], row['EndTime'])
                timeslots.append(timeslot)
        return timeslots
    
    def _build_domain_for_variable(self, variable: CSPVariable, timeslots: List[Tuple], 
                                 rooms: List[Dict], instructors: List[Dict]) -> List[Dict]:
        """Build domain for a single variable using friend's logic"""
        domain = []
        course_id = variable.course_id
        activity_type = variable.activity_type
        
        # Filter timeslots based on session type and duration
        valid_timeslots = self._filter_timeslots_by_session(timeslots, activity_type, course_id)
        
        # Filter rooms by type and capacity
        valid_rooms = self._filter_rooms_by_type(rooms, activity_type, variable.student_count)
        
        # Filter instructors by qualifications and role
        valid_instructors = self._filter_instructors_by_qualifications(instructors, course_id, activity_type)
        
        # Generate all combinations
        for timeslot in valid_timeslots:
            for room in valid_rooms:
                for instructor in valid_instructors:
                    domain.append({
                        'timeslot': timeslot,
                        'room': room['RoomID'],
                        'instructor': instructor.get('InstructorID', instructor.get('Name', 'Unknown'))
                    })
        
        return domain
    
    def _filter_timeslots_by_session(self, timeslots: List[Tuple], session_type: str, course_id: str) -> List[Tuple]:
        """Filter timeslots based on session type and duration requirements"""
        # Simplified version - you can enhance this with friend's duration logic
        return timeslots
    
    def _filter_rooms_by_type(self, rooms: List[Dict], activity_type: str, min_capacity: int) -> List[Dict]:
        """Filter rooms by type and capacity"""
        valid_rooms = []
        for room in rooms:
            room_type = room.get('Type', 'Lecture')
            capacity = room.get('Capacity', 0)
            
            # Match room type to activity type
            if activity_type == 'Lecture' and room_type == 'Lecture':
                if capacity >= min_capacity:
                    valid_rooms.append(room)
            elif activity_type == 'Lab' and room_type == 'Lab':
                if capacity >= min_capacity:
                    valid_rooms.append(room)
            elif activity_type == 'TUT' and room_type == 'TUT':
                if capacity >= min_capacity:
                    valid_rooms.append(room)
        
        return valid_rooms
    
    def _filter_instructors_by_qualifications(self, instructors: List[Dict], course_id: str, activity_type: str) -> List[Dict]:
        """Filter instructors by qualifications and role"""
        valid_instructors = []
        for instructor in instructors:
            # Check qualifications
            quals = instructor.get('qualifications', [])
            if quals and course_id not in quals:
                continue
            
            # Check role compatibility (friend's strict role logic)
            instructor_role = str(instructor.get('Role', '')).lower()
            is_lab_or_tut = activity_type in ['Lab', 'TUT']
            
            if 'professor' in instructor_role and 'assistant' not in instructor_role and is_lab_or_tut:
                continue  # Professor assigned to lab/tut - not allowed
            if 'assistant' in instructor_role and not is_lab_or_tut:
                continue  # Assistant professor assigned to lecture - not allowed
            
            valid_instructors.append(instructor)
        
        return valid_instructors
    
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
        tut_vars = [v for v in self.variables if v.activity_type == "TUT"]
        
        st.write(f"- Lectures: {len(lecture_vars)}")
        st.write(f"- Labs: {len(lab_vars)}")
        st.write(f"- Tutorials: {len(tut_vars)}")
        
        # Domain sizes
        domain_sizes = [len(domain) for domain in self.domains.values()]
        if domain_sizes:
            st.write(f"**Domain Sizes:**")
            st.write(f"- Min: {min(domain_sizes)}")
            st.write(f"- Max: {max(domain_sizes)}")
            st.write(f"- Average: {sum(domain_sizes)/len(domain_sizes):.1f}")
        
        # Variables with empty domains
        empty_domains = [var_id for var_id, domain in self.domains.items() if len(domain) == 0]
        if empty_domains:
            st.error(f"❌ {len(empty_domains)} variables have empty domains!")
            for var_id in empty_domains[:5]:
                st.write(f"  - {var_id}")