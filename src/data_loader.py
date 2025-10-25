# [file name]: data_loader.py (CORRECTED - No Curriculum)
import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Optional, Union
import os

class DataLoader:
    """
    CORRECTED Data loader matching friend's dataset structure (NO CURRICULUM)
    """
    
    def __init__(self):
        self.courses_df = None
        self.instructors_df = None
        self.rooms_df = None
        self.timeslots_df = None
        self.sections_df = None
        # No curriculum_df - friend doesn't use it
    
    def load_all_data(self, 
                     courses_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     instructors_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile], 
                     rooms_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     timeslots_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile],
                     sections_file: Union[str, st.runtime.uploaded_file_manager.UploadedFile]) -> bool:
        """
        Load only 5 required CSV files (NO CURRICULUM)
        """
        try:
            success_count = 0
            
            # Load courses (friend's structure)
            if courses_file:
                self.courses_df = self._load_csv_generic(courses_file)
                if self.courses_df is not None and not self.courses_df.empty:
                    # Validate required columns
                    if 'CourseID' not in self.courses_df.columns:
                        st.error("❌ Courses CSV must contain 'CourseID' column")
                        return False
                    if 'Type' not in self.courses_df.columns:
                        st.error("❌ Courses CSV must contain 'Type' column")
                        return False
                    st.success(f"✅ Loaded {len(self.courses_df)} courses")
                    success_count += 1
                else:
                    st.error("❌ Failed to load courses data")
                    return False
            
            # Load instructors (friend's structure)
            if instructors_file:
                self.instructors_df = self._load_instructors(instructors_file)
                if self.instructors_df is not None and not self.instructors_df.empty:
                    st.success(f"✅ Loaded {len(self.instructors_df)} instructors")
                    success_count += 1
                else:
                    st.error("❌ Failed to load instructors data")
                    return False
            
            # Load rooms (friend's structure)
            if rooms_file:
                self.rooms_df = self._load_rooms(rooms_file)
                if self.rooms_df is not None and not self.rooms_df.empty:
                    st.success(f"✅ Loaded {len(self.rooms_df)} rooms")
                    success_count += 1
                else:
                    st.error("❌ Failed to load rooms data")
                    return False
            
            # Load timeslots (friend's structure)
            if timeslots_file:
                self.timeslots_df = self._load_timeslots(timeslots_file)
                if self.timeslots_df is not None and not self.timeslots_df.empty:
                    st.success(f"✅ Loaded {len(self.timeslots_df)} timeslots")
                    success_count += 1
                else:
                    st.error("❌ Failed to load timeslots data")
                    return False
            
            # Load sections (friend's structure)
            if sections_file:
                self.sections_df = self._load_sections(sections_file)
                if self.sections_df is not None and not self.sections_df.empty:
                    st.success(f"✅ Loaded {len(self.sections_df)} sections")
                    success_count += 1
                else:
                    st.error("❌ Failed to load sections data")
                    return False
            
            return success_count == 5  # All 5 files loaded successfully
            
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
        """Load instructors with friend's qualifications parsing"""
        try:
            instructors = self._load_csv_generic(file_input)
            if instructors is None or instructors.empty:
                return None
            
            # Parse qualified courses (friend's comma-separated format)
            if 'QualifiedCourses' in instructors.columns:
                instructors['qualifications'] = instructors['QualifiedCourses'].apply(
                    lambda x: [course.strip() for course in str(x).split(',')] 
                    if pd.notna(x) and str(x).strip() != '' else []
                )
            
            # Ensure required columns - friend uses InstructorID and Name
            if 'InstructorID' not in instructors.columns and 'Name' in instructors.columns:
                # Use Name as InstructorID if not present
                instructors['InstructorID'] = instructors['Name']
            
            return instructors
            
        except Exception as e:
            st.error(f"❌ Error loading instructors: {str(e)}")
            return None

    def _load_rooms(self, file_input) -> pd.DataFrame:
        """Load rooms data - friend's structure"""
        try:
            rooms = self._load_csv_generic(file_input)
            if rooms is None or rooms.empty:
                return None
                
            # Validate required columns
            if 'RoomID' not in rooms.columns:
                st.error("❌ Rooms CSV must contain 'RoomID' column")
                return None
            if 'Type' not in rooms.columns:
                st.error("❌ Rooms CSV must contain 'Type' column")
                return None
            if 'Capacity' not in rooms.columns:
                st.error("❌ Rooms CSV must contain 'Capacity' column")
                return None
                
            return rooms
        except Exception as e:
            st.error(f"❌ Error loading rooms: {str(e)}")
            return None

    def _load_timeslots(self, file_input) -> pd.DataFrame:
        """Load timeslots data - friend's structure"""
        try:
            timeslots = self._load_csv_generic(file_input)
            if timeslots is None or timeslots.empty:
                return None
                
            # Validate required columns
            required_cols = ['Day', 'StartTime', 'EndTime']
            for col in required_cols:
                if col not in timeslots.columns:
                    st.error(f"❌ Timeslots CSV must contain '{col}' column")
                    return None
            return timeslots
        except Exception as e:
            st.error(f"❌ Error loading timeslots: {str(e)}")
            return None

    def _load_sections(self, file_input) -> pd.DataFrame:
        """Load sections data with friend's structure"""
        try:
            sections = self._load_csv_generic(file_input)
            if sections is None or sections.empty:
                return None
                
            # Validate required columns
            if 'SectionID' not in sections.columns:
                st.error("❌ Sections CSV must contain 'SectionID' column")
                return None
            if 'Capacity' not in sections.columns:
                st.error("❌ Sections CSV must contain 'Capacity' column")
                return None
                
            return sections
        except Exception as e:
            st.error(f"❌ Error loading sections: {str(e)}")
            return None

    # REMOVED: get_courses_for_year() - friend doesn't use curriculum

    def get_qualified_instructors(self, course_id: str) -> List[str]:
        """Get instructors qualified to teach a course"""
        if self.instructors_df is None:
            return []
        
        qualified = []
        for _, instructor in self.instructors_df.iterrows():
            quals = instructor.get('qualifications', [])
            if course_id in quals:
                qualified.append(instructor['InstructorID'])
        
        return qualified

    def get_room_capacity(self, room_id: str) -> int:
        """Get room capacity"""
        if self.rooms_df is None:
            return 0
        
        room_data = self.rooms_df[self.rooms_df['RoomID'] == room_id]
        if room_data.empty:
            return 0
        
        return room_data['Capacity'].iloc[0]

    def get_compatible_rooms(self, activity_type: str, min_capacity: int) -> List[str]:
        """Get rooms compatible with activity type and capacity"""
        if self.rooms_df is None:
            return []
        
        # Map activity types to room types (friend's mapping)
        room_type_map = {
            'Lecture': 'Lecture',
            'Lab': 'Lab', 
            'TUT': 'TUT'
        }
        
        target_room_type = room_type_map.get(activity_type, 'Lecture')
        
        compatible_rooms = self.rooms_df[
            (self.rooms_df['Type'] == target_room_type) & 
            (self.rooms_df['Capacity'] >= min_capacity)
        ]['RoomID'].tolist()
        
        return compatible_rooms

    def validate_data_consistency(self) -> bool:
        """Validate that all datasets are consistent"""
        try:
            checks = []
            datasets = [
                (self.courses_df, "Courses"),
                (self.instructors_df, "Instructors"), 
                (self.rooms_df, "Rooms"),
                (self.timeslots_df, "TimeSlots"),
                (self.sections_df, "Sections")
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
            
            return all(check.startswith("✅") for check in checks)  # All 5 required
            
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
            'sections_count': len(self.sections_df) if self.sections_df is not None else 0
        }