import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Optional, Union
import os

class DataLoader:
    """
    Data loader for CSIT timetable generation that matches the exact Excel structure
    """
    
    def __init__(self):
        self.courses_df = None
        self.instructors_df = None
        self.rooms_df = None
        self.timeslots_df = None
        self.sections_df = None
        self.curriculum_df = None
        
    def load_all_data(self, 
                     courses_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     instructors_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile], 
                     rooms_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     timeslots_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     sections_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     curriculum_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile]) -> bool:
        """
        Load all 6 required CSV files with exact Excel structure
        """
        try:
            success_count = 0
            
            # Load courses
            if courses_file:
                self.courses_df = self._load_csv_generic(courses_file)
                if self.courses_df is not None:
                    st.success(f"✅ Loaded {len(self.courses_df)} courses")
                    success_count += 1
                else:
                    st.error("❌ Failed to load courses data")
                    return False
            
            # Load instructors
            if instructors_file:
                self.instructors_df = self._load_instructors(instructors_file)
                if self.instructors_df is not None:
                    st.success(f"✅ Loaded {len(self.instructors_df)} instructors")
                    success_count += 1
                else:
                    st.error("❌ Failed to load instructors data")
                    return False
            
            # Load rooms
            if rooms_file:
                self.rooms_df = self._load_rooms(rooms_file)
                if self.rooms_df is not None:
                    st.success(f"✅ Loaded {len(self.rooms_df)} rooms")
                    success_count += 1
                else:
                    st.error("❌ Failed to load rooms data")
                    return False
            
            # Load timeslots
            if timeslots_file:
                self.timeslots_df = self._load_timeslots(timeslots_file)
                if self.timeslots_df is not None:
                    st.success(f"✅ Loaded {len(self.timeslots_df)} timeslots")
                    success_count += 1
                else:
                    st.error("❌ Failed to load timeslots data")
                    return False
            
            # Load sections
            if sections_file:
                self.sections_df = self._load_sections(sections_file)
                if self.sections_df is not None:
                    st.success(f"✅ Loaded {len(self.sections_df)} sections")
                    success_count += 1
                else:
                    st.error("❌ Failed to load sections data")
                    return False
            
            # Load curriculum
            if curriculum_file:
                self.curriculum_df = self._load_csv_generic(curriculum_file)
                if self.curriculum_df is not None:
                    st.success(f"✅ Loaded curriculum for {len(self.curriculum_df)} year-course combinations")
                    success_count += 1
                else:
                    st.error("❌ Failed to load curriculum data")
                    return False
            
            return success_count == 6
            
        except Exception as e:
            st.error(f"❌ Error loading data: {str(e)}")
            import traceback
            st.error(f"Debug: {traceback.format_exc()}")
            return False

    def _load_csv_generic(self, file_input) -> pd.DataFrame:
        """Generic CSV loader"""
        try:
            if hasattr(file_input, 'read'):  # Streamlit UploadedFile
                df = pd.read_csv(file_input)
            else:  # File path
                df = pd.read_csv(file_input)
            
            if df.empty:
                st.warning("⚠️ Loaded an empty CSV file")
            
            return df
            
        except Exception as e:
            st.error(f"❌ Failed to load CSV file: {str(e)}")
            return None

    def _load_instructors(self, file_input) -> pd.DataFrame:
        """Load instructors with qualifications parsing"""
        try:
            instructors = self._load_csv_generic(file_input)
            if instructors is None:
                return None
            
            # Parse qualified courses (comma-separated list)
            if 'qualifications' in instructors.columns:
                instructors['qualifications'] = instructors['qualifications'].apply(
                    lambda x: [course.strip() for course in str(x).split(',')] 
                    if pd.notna(x) and str(x).strip() != '' else []
                )
            
            return instructors
            
        except Exception as e:
            st.error(f"❌ Error loading instructors: {str(e)}")
            return None

    def _load_rooms(self, file_input) -> pd.DataFrame:
        """Load rooms data"""
        try:
            rooms = self._load_csv_generic(file_input)
            return rooms
        except Exception as e:
            st.error(f"❌ Error loading rooms: {str(e)}")
            return None

    def _load_timeslots(self, file_input) -> pd.DataFrame:
        """Load timeslots data"""
        try:
            timeslots = self._load_csv_generic(file_input)
            return timeslots
        except Exception as e:
            st.error(f"❌ Error loading timeslots: {str(e)}")
            return None

    def _load_sections(self, file_input) -> pd.DataFrame:
        """Load sections data"""
        try:
            sections = self._load_csv_generic(file_input)
            return sections
        except Exception as e:
            st.error(f"❌ Error loading sections: {str(e)}")
            return None

    def get_courses_for_year(self, year: int) -> List[str]:
        """Get all courses for a specific year from curriculum"""
        if self.curriculum_df is None:
            return []
        
        courses = self.curriculum_df[self.curriculum_df['year'] == year]['course_id'].tolist()
        return courses

    def get_qualified_instructors(self, course_id: str) -> List[str]:
        """Get instructors qualified to teach a course"""
        if self.instructors_df is None:
            return []
        
        qualified = []
        for _, instructor in self.instructors_df.iterrows():
            if 'qualifications' in instructor and course_id in instructor['qualifications']:
                qualified.append(instructor['instructor_id'])
        
        return qualified

    def get_room_capacity(self, room_id: str) -> int:
        """Get room capacity"""
        if self.rooms_df is None:
            return 0
        
        room_data = self.rooms_df[self.rooms_df['room_id'] == room_id]
        if room_data.empty:
            return 0
        
        return room_data['capacity'].iloc[0]

    def get_compatible_rooms(self, activity_type: str, min_capacity: int) -> List[str]:
        """Get rooms compatible with activity type and capacity"""
        if self.rooms_df is None:
            return []
        
        # Map course types to room types
        room_type_map = {
            'Lecture': 'Lecture',
            'Lab': 'Lab', 
            'Tutorial': 'Tutorial',
            'Lecture,Lab': 'Lab',  # For lab component
            'Lecture,Tutorial': 'Tutorial',  # For tutorial component
            'Lecture,Lab,Tutorial': 'Tutorial'  # For tutorial component
        }
        
        target_room_type = room_type_map.get(activity_type, 'Lecture')
        
        compatible_rooms = self.rooms_df[
            (self.rooms_df['type'] == target_room_type) & 
            (self.rooms_df['capacity'] >= min_capacity)
        ]['room_id'].tolist()
        
        return compatible_rooms

    def validate_data_consistency(self) -> bool:
        """Validate that all datasets are consistent"""
        try:
            checks = []
            
            # Check all datasets are loaded
            datasets = [
                (self.courses_df, "Courses"),
                (self.instructors_df, "Instructors"), 
                (self.rooms_df, "Rooms"),
                (self.timeslots_df, "TimeSlots"),
                (self.sections_df, "Sections"),
                (self.curriculum_df, "Curriculum")
            ]
            
            for df, name in datasets:
                if df is not None and not df.empty:
                    checks.append(f"✅ {name}: {len(df)} records")
                else:
                    checks.append(f"❌ {name}: Not loaded or empty")
            
            # Display checks
            for check in checks:
                if check.startswith("✅"):
                    st.success(check)
                else:
                    st.error(check)
            
            # Validate curriculum references
            if self.curriculum_df is not None and self.courses_df is not None:
                curriculum_courses = set(self.curriculum_df['course_id'].unique())
                available_courses = set(self.courses_df['course_id'].unique())
                missing_courses = curriculum_courses - available_courses
                
                if missing_courses:
                    st.warning(f"⚠️ Curriculum references {len(missing_courses)} courses not in courses dataset")
            
            return all(check.startswith("✅") for check in checks)
            
        except Exception as e:
            st.error(f"❌ Error during data validation: {str(e)}")
            return False

    def get_data_summary(self) -> Dict:
        """Get comprehensive summary of loaded data"""
        return {
            'courses_count': len(self.courses_df) if self.courses_df is not None else 0,
            'instructors_count': len(self.instructors_df) if self.instructors_df is not None else 0,
            'rooms_count': len(self.rooms_df) if self.rooms_df is not None else 0,
            'timeslots_count': len(self.timeslots_df) if self.timeslots_df is not None else 0,
            'sections_count': len(self.sections_df) if self.sections_df is not None else 0,
            'curriculum_entries': len(self.curriculum_df) if self.curriculum_df is not None else 0
        }