import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Optional, Union
import os

class DataLoader:
    """
    Professional data loader that supports both local files and Streamlit uploads
    """
    
    def __init__(self):
        self.courses_df = None
        self.instructors_df = None
        self.rooms_df = None
        self.timeslots_df = None
        self.sections_df = None
        
    def load_all_data(self, 
                     courses_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     instructors_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile], 
                     rooms_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     timeslots_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     sections_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile] = None) -> bool:
        """
        Load all data files - supports both file paths and Streamlit uploaded files
        
        Parameters:
        - courses_file: Can be either a file path string OR a Streamlit UploadedFile object
        - instructors_file: Same as above
        - rooms_file: Same as above  
        - timeslots_file: Same as above
        - sections_file: Same as above (optional)
        """
        try:
            # Load courses
            if courses_file:
                self.courses_df = self._load_courses(courses_file)
                st.success(f"✅ Loaded {len(self.courses_df)} courses")
            
            # Load instructors
            if instructors_file:
                self.instructors_df = self._load_instructors(instructors_file)
                st.success(f"✅ Loaded {len(self.instructors_df)} instructors")
            
            # Load rooms
            if rooms_file:
                self.rooms_df = self._load_rooms(rooms_file)
                st.success(f"✅ Loaded {len(self.rooms_df)} rooms")
            
            # Load timeslots
            if timeslots_file:
                self.timeslots_df = self._load_timeslots(timeslots_file)
                st.success(f"✅ Loaded {len(self.timeslots_df)} timeslots")
            
            # Load sections (optional)
            if sections_file:
                self.sections_df = self._load_csv_generic(sections_file)
                st.success(f"✅ Loaded {len(self.sections_df)} sections")
            else:
                # Create default sections if not provided
                self._create_default_sections()
                
            return self._validate_data_consistency()
            
        except Exception as e:
            st.error(f"❌ Error loading data: {str(e)}")
            return False

    def _load_csv_generic(self, file_input: Union[str, st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
        """
        Generic CSV loader that handles both file paths and Streamlit uploaded files
        
        Explanation:
        - If file_input is a string: it's a file path like "data/Courses.csv"
        - If file_input has a 'type' attribute: it's a Streamlit UploadedFile object
        """
        try:
            # Check if it's a Streamlit uploaded file (has 'type' attribute)
            if hasattr(file_input, 'type') and file_input.type is not None:
                # It's a Streamlit UploadedFile object - read directly
                return pd.read_csv(file_input)
            else:
                # It's a file path string - use relative path from project root
                return pd.read_csv(file_input)
        except Exception as e:
            raise ValueError(f"Failed to load CSV file: {str(e)}")

    def _load_courses(self, file_input: Union[str, st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
        """Load and validate courses data from either file path or uploaded file"""
        courses = self._load_csv_generic(file_input)
        
        # Validate required columns
        required_columns = ['CourseID', 'CourseName', 'Credits', 'Type']
        self._validate_columns(courses, required_columns, "Courses")
        
        # Clean and standardize data
        courses['Type'] = courses['Type'].str.strip().str.title()
        
        # Validate course types
        valid_types = ['Lecture', 'Lab', 'Lecture And Lab']
        invalid_types = [t for t in courses['Type'].unique() if t not in valid_types]
        if invalid_types:
            raise ValueError(f"Invalid course types: {invalid_types}. Must be one of: {valid_types}")
        
        return courses
    
    def _load_instructors(self, file_input: Union[str, st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
        """Load and process instructors data from either file path or uploaded file"""
        instructors = self._load_csv_generic(file_input)
        
        # Validate required columns
        required_columns = ['InstructorID', 'Name', 'Role', 'PreferredSlots', 'QualifiedCourses']
        self._validate_columns(instructors, required_columns, "Instructors")
        
        # Parse qualified courses (comma-separated list)
        instructors['QualifiedCourses'] = instructors['QualifiedCourses'].apply(
            lambda x: [course.strip() for course in str(x).split(',')] if pd.notna(x) else []
        )
        
        # Extract unavailable day from PreferredSlots
        instructors['UnavailableDay'] = instructors['PreferredSlots'].str.extract(r'Not on (.*)')
        
        return instructors
    
    def _load_rooms(self, file_input: Union[str, st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
        """Load and validate rooms data from either file path or uploaded file"""
        rooms = self._load_csv_generic(file_input)
        
        # Validate required columns
        required_columns = ['RoomID', 'Type', 'Capacity']
        self._validate_columns(rooms, required_columns, "Rooms")
        
        # Validate room types
        valid_types = ['Lecture', 'Lab']
        invalid_types = [t for t in rooms['Type'].unique() if t not in valid_types]
        if invalid_types:
            raise ValueError(f"Invalid room types: {invalid_types}. Must be one of: {valid_types}")
        
        return rooms
    
    def _load_timeslots(self, file_input: Union[str, st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
        """Load and process timeslots data from either file path or uploaded file"""
        timeslots = self._load_csv_generic(file_input)
        
        # Validate required columns
        required_columns = ['Day', 'StartTime', 'EndTime']
        self._validate_columns(timeslots, required_columns, "TimeSlots")
        
        # Create unique timeslot identifier
        timeslots['TimeslotID'] = timeslots['Day'] + ' ' + timeslots['StartTime'] + '-' + timeslots['EndTime']
        
        return timeslots

    # ... (keep the rest of the methods the same as before)
    def _create_default_sections(self):
        """Create default sections if not provided"""
        sections_data = []
        for _, course in self.courses_df.iterrows():
            sections_data.append({
                'SectionID': f"{course['CourseID']}_S1",
                'CourseID': course['CourseID'],
                'Semester': 'Fall2025',
                'StudentCount': 30
            })
        self.sections_df = pd.DataFrame(sections_data)
        st.info("ℹ️ Created default sections (1 section per course)")
    
    def _validate_columns(self, df: pd.DataFrame, required_columns: List[str], data_type: str):
        """Validate that DataFrame contains required columns"""
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing columns in {data_type}: {missing_columns}")
    
    def _validate_data_consistency(self) -> bool:
        """Validate that all datasets are consistent"""
        checks = []
        
        if self.courses_df is not None:
            checks.append(f"✅ Courses: {len(self.courses_df)}")
        else:
            checks.append("❌ Courses: Not loaded")
        
        if self.instructors_df is not None:
            checks.append(f"✅ Instructors: {len(self.instructors_df)}")
        else:
            checks.append("❌ Instructors: Not loaded")
        
        if self.rooms_df is not None:
            checks.append(f"✅ Rooms: {len(self.rooms_df)}")
        else:
            checks.append("❌ Rooms: Not loaded")
        
        if self.timeslots_df is not None:
            checks.append(f"✅ TimeSlots: {len(self.timeslots_df)}")
        else:
            checks.append("❌ TimeSlots: Not loaded")
        
        if self.sections_df is not None:
            checks.append(f"✅ Sections: {len(self.sections_df)}")
        else:
            checks.append("❌ Sections: Not loaded")
        
        for check in checks:
            if check.startswith("✅"):
                st.success(check)
            else:
                st.error(check)
        
        return all(check.startswith("✅") for check in checks)
    
    def get_data_summary(self) -> Dict:
        """Get summary statistics of loaded data"""
        return {
            'courses_count': len(self.courses_df) if self.courses_df is not None else 0,
            'instructors_count': len(self.instructors_df) if self.instructors_df is not None else 0,
            'rooms_count': len(self.rooms_df) if self.rooms_df is not None else 0,
            'timeslots_count': len(self.timeslots_df) if self.timeslots_df is not None else 0,
            'sections_count': len(self.sections_df) if self.sections_df is not None else 0
        }