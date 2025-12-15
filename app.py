"""
CSIT Timetable Generator - Streamlit Interface
Author: Student Project
Course: Constraint Satisfaction Problems - CSIT Department

Web interface for generating university timetables using CSP algorithms.
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import io

# Import CSP solver
import os
import tempfile
try:
    from csp_solver import generate_timetable_from_uploads
except ImportError:
    st.error("Error: csp_solver.py not found in current directory")
    st.stop()


def generate_timetable(courses_df, instructors_df, rooms_df, timeslots_df, sections_df, 
                      force_permissive=False, timeout=60):
    """
    Wrapper function to call the new CSP solver with uploaded dataframes
    """
    # Create temporary directory to save CSV files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save all dataframes as CSV files
        courses_df.to_csv(os.path.join(temp_dir, 'courses.csv'), index=False)
        instructors_df.to_csv(os.path.join(temp_dir, 'instructors.csv'), index=False)
        rooms_df.to_csv(os.path.join(temp_dir, 'rooms.csv'), index=False)
        timeslots_df.to_csv(os.path.join(temp_dir, 'timeslots.csv'), index=False)
        sections_df.to_csv(os.path.join(temp_dir, 'sections.csv'), index=False)
        
        # Call the actual CSP solver
        try:
            timetable_df = generate_timetable_from_uploads(temp_dir)
            
            # Return result in the format app.py expects
            return {
                'solution': timetable_df,
                'meta': {},
                'course_to_section_groups': {},
                'total_variables': len(timetable_df)
            }
        except RuntimeError as e:
            st.error(f"Timetable generation failed: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return None


def format_timetable_for_display(solution, meta, courses_df, instructors_df, course_to_section_groups):
    """
    Format the timetable solution for display (the new solver already returns a DataFrame)
    """
    # The new solver already returns a properly formatted DataFrame
    if isinstance(solution, pd.DataFrame):
        return solution
    return pd.DataFrame()

# ==================== PAGE CONFIGURATION ====================

st.set_page_config(
    page_title="CSIT Timetable Generator",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== HELPER FUNCTIONS ====================

def validate_csv_files(courses_df, instructors_df, rooms_df, timeslots_df, sections_df):
    """
    Validate uploaded CSV files for required columns and data quality
    """
    errors = []
    warnings = []
    
    # Check courses.csv
    required_courses = ['CourseID', 'CourseName', 'Year', 'Type']
    missing = [col for col in required_courses if col not in courses_df.columns]
    if missing:
        errors.append(f"courses.csv missing: {', '.join(missing)}")
    
    # Check instructors.csv
    required_instructors = ['Name', 'Role', 'QualifiedCourses']
    missing = [col for col in required_instructors if col not in instructors_df.columns]
    if missing:
        errors.append(f"instructors.csv missing: {', '.join(missing)}")
    else:
        # Check for empty qualifications
        empty_quals = instructors_df[instructors_df['QualifiedCourses'].isna() | 
                                     (instructors_df['QualifiedCourses'] == '')]
        if len(empty_quals) > 0:
            warnings.append(f"{len(empty_quals)} instructors have no qualifications")
    
    # Check rooms.csv
    required_rooms = ['RoomID', 'Type', 'Capacity']
    missing = [col for col in required_rooms if col not in rooms_df.columns]
    if missing:
        errors.append(f"rooms.csv missing: {', '.join(missing)}")
    else:
        # Check room types
        room_types = rooms_df['Type'].unique()
        if 'Lecture' not in room_types:
            warnings.append("No Lecture rooms found")
        if 'Lab' not in room_types:
            warnings.append("No Lab rooms found")
        if 'TUT' not in room_types:
            warnings.append("No TUT rooms found")
    
    # Check timeslots.csv
    required_timeslots = ['Day', 'StartTime', 'EndTime']
    missing = [col for col in required_timeslots if col not in timeslots_df.columns]
    if missing:
        errors.append(f"timeslots.csv missing: {', '.join(missing)}")
    
    # Check sections.csv
    required_sections = ['SectionID', 'Capacity']
    missing = [col for col in required_sections if col not in sections_df.columns]
    if missing:
        errors.append(f"sections.csv missing: {', '.join(missing)}")
    
    return errors, warnings


def create_weekly_grid(timetable_df, selected_section=None):
    """
    Create weekly grid view of timetable
    """
    if timetable_df.empty:
        return pd.DataFrame()
    
    df = timetable_df.copy()
    if selected_section and selected_section != "All":
        df = df[df['SectionID'] == selected_section]
    
    if df.empty:
        return pd.DataFrame()
    
    # Define day order (Sunday to Thursday)
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    
    # Get unique timeslots
    timeslots = df[['StartTime', 'EndTime']].drop_duplicates().values.tolist()
    
    # Sort timeslots by time
    def time_to_minutes(time_str):
        try:
            time_part, period = time_str.strip().split()
            hours, minutes = map(int, time_part.split(':'))
            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0
            return hours * 60 + minutes
        except:
            return 9999
    
    timeslots.sort(key=lambda x: time_to_minutes(x[0]))
    
    # Create grid
    grid_data = []
    for start_time, end_time in timeslots:
        row = {'Time': f"{start_time} - {end_time}"}
        
        for day in day_order:
            day_classes = df[(df['Day'] == day) & 
                           (df['StartTime'] == start_time) & 
                           (df['EndTime'] == end_time)]
            
            if not day_classes.empty:
                class_info = []
                for _, class_row in day_classes.iterrows():
                    display_text = (f"{class_row['CourseID']}\n"
                                   f"{class_row['SessionType']}\n"
                                   f"{class_row['Instructor']}\n"
                                   f"Room: {class_row['Room']}")
                    class_info.append(display_text)
                row[day] = "\n\n".join(class_info)
            else:
                row[day] = ""
        
        grid_data.append(row)
    
    return pd.DataFrame(grid_data)


def display_colorful_grid(grid_df):
    """
    Display timetable as colored HTML grid
    """
    if grid_df.empty:
        st.info("No schedule data to display")
        return
    
    html = """
    <style>
    .timetable {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 12px;
        border: 2px solid #2c3e50;
    }
    .timetable th {
        background-color: #2c3e50;
        color: white;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        border: 1px solid #34495e;
    }
    .timetable td {
        border: 1px solid #ddd;
        padding: 8px;
        vertical-align: top;
        min-height: 100px;
        border: 1px solid #bdc3c7;
    }
    .time-cell {
        background-color: #34495e;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    .lecture {
        background-color: #cfe2ff;
        border-left: 5px solid #0d6efd !important;
        color: #084298;
    }
    .lab {
        background-color: #ffe5cc;
        border-left: 5px solid #fd7e14 !important;
        color: #9c4000;
    }
    .tut {
        background-color: #d1f2cc;
        border-left: 5px solid #198754 !important;
        color: #0d5027;
    }
    .class-cell {
        padding: 10px;
        margin: 4px 0;
        border-radius: 6px;
        font-size: 12px;
        line-height: 1.6;
        font-weight: 500;
    }
    .class-cell:not(:last-child) {
        margin-bottom: 8px;
    }
    </style>
    <table class='timetable'>
        <thead>
            <tr>
                <th style="width: 150px;">Time Slot</th>
                <th>Sunday</th>
                <th>Monday</th>
                <th>Tuesday</th>
                <th>Wednesday</th>
                <th>Thursday</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in grid_df.iterrows():
        html += f"<tr><td class='time-cell'>{row['Time']}</td>"
        
        for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']:
            cell_content = row[day]
            if cell_content and cell_content.strip():
                # Split multiple classes (separated by double newline)
                classes = cell_content.split('\n\n')
                
                html += "<td>"
                for class_text in classes:
                    # Determine session type for styling
                    if "Lecture" in class_text:
                        cell_class = "lecture"
                    elif "Lab" in class_text:
                        cell_class = "lab"
                    else:
                        cell_class = "tut"
                    
                    # Escape any HTML in the content and preserve line breaks
                    formatted_text = class_text.replace('\n', '<br>')
                    html += f"<div class='class-cell {cell_class}'>{formatted_text}</div>"
                
                html += "</td>"
            else:
                html += "<td></td>"
        
        html += "</tr>"
    
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


# ==================== MAIN APPLICATION ====================

def main():
    """
    Main application function
    """
    st.title("📅 CSIT Timetable Generator")
    st.markdown("### Constraint Satisfaction Problem (CSP) Based Solution")
    
    # Initialize session state
    if 'timetable_data' not in st.session_state:
        st.session_state.timetable_data = None
    if 'generation_stats' not in st.session_state:
        st.session_state.generation_stats = {}
    if 'generation_time' not in st.session_state:
        st.session_state.generation_time = None
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Upload & Generate", "View Timetables", "Statistics"]
    )
    
    # Page routing
    if page == "Upload & Generate":
        show_generation_page()
    elif page == "View Timetables":
        show_view_page()
    elif page == "Statistics":
        show_statistics_page()


def show_generation_page():
    """
    Display timetable generation page
    """
    st.header("📤 Data Upload & Timetable Generation")
    
    st.info("""
    **Academic Rules Implemented:**
    - Lectures: 3-4 sections grouped together
    - Labs: 2 sections grouped together
    - Tutorials: Individual sections
    - Room capacity constraints enforced
    - Instructor qualifications checked
    - No double-booking for instructors, rooms, or sections
    - Year 1 electives scheduled simultaneously
    """)
    
    # File upload section
    st.subheader("Upload Required CSV Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        courses_file = st.file_uploader("Courses.csv", type=["csv"], 
                                       help="Required columns: CourseID, CourseName, Year, Type, Shared")
        instructors_file = st.file_uploader("Instructors.csv", type=["csv"],
                                          help="Required columns: Name, Role, QualifiedCourses, PreferredSlots")
        rooms_file = st.file_uploader("Rooms.csv", type=["csv"],
                                     help="Required columns: RoomID, Type, Capacity")
    
    with col2:
        timeslots_file = st.file_uploader("Timeslots.csv", type=["csv"],
                                         help="Required columns: Day, StartTime, EndTime, Duration")
        sections_file = st.file_uploader("Sections.csv", type=["csv"],
                                        help="Required columns: SectionID, Capacity")
    
    # Generation settings
    st.subheader("Generation Settings")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        timeout = st.slider("Timeout (seconds)", 30, 300, 120, 
                           help="Maximum time allowed for CSP search")
    with col2:
        permissive_mode = st.checkbox("Permissive Mode", value=False,
                                     help="Relax some constraints if needed")
    with col3:
        display_debug = st.checkbox("Show Debug Info", value=False,
                                   help="Display detailed CSP debugging information")
    
    # Data validation
    if st.button("🔍 Validate Data", type="secondary"):
        if not all([courses_file, instructors_file, rooms_file, timeslots_file, sections_file]):
            st.error("Please upload all 5 CSV files first")
        else:
            validate_uploaded_data(courses_file, instructors_file, rooms_file, 
                                 timeslots_file, sections_file)
    
    # Generation button
    if st.button("🚀 Generate Timetable", type="primary", use_container_width=True):
        if not all([courses_file, instructors_file, rooms_file, timeslots_file, sections_file]):
            st.error("Please upload all 5 CSV files")
            return
        
        generate_timetable_process(courses_file, instructors_file, rooms_file,
                                 timeslots_file, sections_file, timeout,
                                 permissive_mode, display_debug)


def validate_uploaded_data(courses_file, instructors_file, rooms_file, timeslots_file, sections_file):
    """
    Validate uploaded CSV files
    """
    with st.spinner("Validating data..."):
        try:
            # Load data
            courses_df = pd.read_csv(courses_file)
            instructors_df = pd.read_csv(instructors_file)
            rooms_df = pd.read_csv(rooms_file)
            timeslots_df = pd.read_csv(timeslots_file)
            sections_df = pd.read_csv(sections_file)
            
            # Run validation
            errors, warnings = validate_csv_files(courses_df, instructors_df, rooms_df,
                                               timeslots_df, sections_df)
            
            # Display results
            if not errors and not warnings:
                st.success("✅ All data validation checks passed!")
                
                # Show data summary
                with st.expander("📊 Data Summary", expanded=True):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Courses", len(courses_df))
                    col2.metric("Instructors", len(instructors_df))
                    col3.metric("Rooms", len(rooms_df))
                    col4.metric("Timeslots", len(timeslots_df))
                    col5.metric("Sections", len(sections_df))
            else:
                if errors:
                    st.error("❌ Critical errors found:")
                    for error in errors:
                        st.error(f"• {error}")
                
                if warnings:
                    st.warning("⚠️ Warnings found:")
                    for warning in warnings:
                        st.warning(f"• {warning}")
        
        except Exception as e:
            st.error(f"Error validating data: {str(e)}")


def generate_timetable_process(courses_file, instructors_file, rooms_file, timeslots_file,
                             sections_file, timeout, permissive_mode, display_debug):
    """
    Generate timetable using CSP solver
    """
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Load data
        status_text.text("Loading CSV files...")
        progress_bar.progress(10)
        
        courses_df = pd.read_csv(courses_file)
        instructors_df = pd.read_csv(instructors_file)
        rooms_df = pd.read_csv(rooms_file)
        timeslots_df = pd.read_csv(timeslots_file)
        sections_df = pd.read_csv(sections_file)
        
        # Validate data
        status_text.text("Validating data...")
        progress_bar.progress(20)
        
        errors, warnings = validate_csv_files(courses_df, instructors_df, rooms_df,
                                           timeslots_df, sections_df)
        if errors:
            st.error("Cannot generate timetable with invalid data")
            return
        
        # Generate timetable
        status_text.text("Running CSP solver...")
        progress_bar.progress(40)
        
        start_time = time.time()
        
        result = generate_timetable(
            courses_df=courses_df,
            instructors_df=instructors_df,
            rooms_df=rooms_df,
            timeslots_df=timeslots_df,
            sections_df=sections_df,
            force_permissive=permissive_mode,
            timeout=timeout
        )
        
        generation_time = time.time() - start_time
        
        if result is None:
            progress_bar.progress(100)
            status_text.text("Generation failed")
            st.error("""
            Could not generate a valid timetable.
            
            **Possible reasons:**
            1. Insufficient qualified instructors
            2. Not enough rooms or timeslots
            3. Constraint conflicts
            
            **Try:**
            - Enable Permissive Mode
            - Increase timeout
            - Check instructor qualifications
            - Verify room capacities
            """)
            return
        
        # Format results
        status_text.text("Formatting results...")
        progress_bar.progress(80)
        
        timetable_df = format_timetable_for_display(
            result['solution'],
            result['meta'],
            courses_df,
            instructors_df,
            result['course_to_section_groups']
        )
        
        progress_bar.progress(100)
        status_text.text("✅ Generation complete!")
        
        # Store in session state
        st.session_state.timetable_data = timetable_df
        st.session_state.generation_time = generation_time
        st.session_state.generation_stats = {
            'total_classes': len(timetable_df),
            'variables': result['total_variables'],
            'coverage': (len(result['solution']) / result['total_variables'] * 100),
            'generation_time': generation_time,
            'courses_scheduled': timetable_df['CourseID'].nunique(),
            'sections_covered': timetable_df['SectionID'].nunique()
        }
        
        # Display success metrics
        st.success(f"✅ Timetable generated successfully in {generation_time:.1f} seconds!")
        
        # Performance metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Classes Scheduled", len(timetable_df))
        col2.metric("Coverage", f"{st.session_state.generation_stats['coverage']:.1f}%")
        col3.metric("Generation Time", f"{generation_time:.1f}s")
        col4.metric("Courses", timetable_df['CourseID'].nunique())
        
        # Session type breakdown
        st.subheader("📊 Session Type Distribution")
        session_counts = timetable_df['SessionType'].value_counts()
        
        col1, col2, col3 = st.columns(3)
        if 'Lecture' in session_counts:
            col1.metric("Lectures", session_counts['Lecture'])
        if 'Lab' in session_counts:
            col2.metric("Labs", session_counts['Lab'])
        if 'TUT' in session_counts:
            col3.metric("Tutorials", session_counts['TUT'])
        
        st.info("Go to 'View Timetables' page to explore the generated schedule")
        
        # Show debug info if requested
        if display_debug:
            with st.expander("🔍 Debug Information", expanded=False):
                st.write(f"Total variables: {result['total_variables']}")
                st.write(f"Variables assigned: {len(result['solution'])}")
                st.write(f"Elective constraints: {len(result.get('elective_constraints', []))}")
                
                # Show sample assignments
                st.write("Sample assignments:")
                for i, (var, val) in enumerate(list(result['solution'].items())[:5]):
                    st.write(f"{i+1}. {var}: {val['timeslot'][0]} {val['timeslot'][1]}-{val['timeslot'][2]}, "
                            f"Room {val['room']}, Instructor {val['instructor']}")
    
    except Exception as e:
        st.error(f"Error during generation: {str(e)}")


def show_view_page():
    """
    Display timetable viewing page
    """
    st.header("📅 View Generated Timetables")
    
    if st.session_state.timetable_data is None:
        st.warning("No timetable generated yet. Please generate one first.")
        return
    
    df = st.session_state.timetable_data
    
    # View selection
    view_option = st.selectbox(
        "Select View Type",
        ["Student Section View", "Instructor Schedule", "Room Schedule", "Complete Schedule"]
    )
    
    if view_option == "Student Section View":
        show_student_view(df)
    elif view_option == "Instructor Schedule":
        show_instructor_view(df)
    elif view_option == "Room Schedule":
        show_room_view(df)
    else:
        show_complete_view(df)


def show_student_view(df):
    """
    Display student section timetable
    """
    st.subheader("🎓 Student Section Timetable")
    
    # Year filter
    years = sorted(df['CourseYear'].unique())
    selected_year = st.selectbox("Select Year", years)
    
    # Section filter
    year_sections = df[df['CourseYear'] == selected_year]['SectionID'].unique()
    selected_section = st.selectbox("Select Section", sorted(year_sections))
    
    # Filter data
    section_df = df[df['SectionID'] == selected_section].copy()
    
    if section_df.empty:
        st.info(f"No classes scheduled for section {selected_section}")
        return
    
    # Display as weekly grid
    st.markdown(f"### 📅 Weekly Schedule for Section {selected_section} (Year {selected_year})")
    grid_df = create_weekly_grid(df, selected_section)
    if not grid_df.empty:
        display_colorful_grid(grid_df)


def show_instructor_view(df):
    """
    Display instructor schedule
    """
    st.subheader("👨‍🏫 Instructor Schedule")
    
    instructors = sorted(df['Instructor'].unique())
    selected_instructor = st.selectbox("Select Instructor", instructors)
    
    # Filter instructor's classes
    instructor_df = df[df['Instructor'] == selected_instructor].copy()
    
    if instructor_df.empty:
        st.info(f"No classes scheduled for {selected_instructor}")
        return
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Classes", len(instructor_df))
    col2.metric("Courses", instructor_df['CourseID'].nunique())
    col3.metric("Sections", instructor_df['SectionID'].nunique())
    
    # Display as weekly grid
    st.markdown(f"### 📅 Weekly Schedule for {selected_instructor}")
    
    # Create filtered dataframe for grid
    filtered_df = df[df['Instructor'] == selected_instructor]
    
    # Get unique timeslots and create grid
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    timeslots = filtered_df[['StartTime', 'EndTime']].drop_duplicates().values.tolist()
    
    def time_to_minutes(time_str):
        try:
            time_part, period = time_str.strip().split()
            hours, minutes = map(int, time_part.split(':'))
            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0
            return hours * 60 + minutes
        except:
            return 9999
    
    timeslots.sort(key=lambda x: time_to_minutes(x[0]))
    
    grid_data = []
    for start_time, end_time in timeslots:
        row = {'Time': f"{start_time} - {end_time}"}
        
        for day in day_order:
            day_classes = filtered_df[(filtered_df['Day'] == day) & 
                                     (filtered_df['StartTime'] == start_time) & 
                                     (filtered_df['EndTime'] == end_time)]
            
            if not day_classes.empty:
                class_info = []
                for _, class_row in day_classes.iterrows():
                    display_text = (f"{class_row['CourseID']}\n"
                                   f"{class_row['SessionType']}\n"
                                   f"Section: {class_row['SectionID']}\n"
                                   f"Room: {class_row['Room']}")
                    class_info.append(display_text)
                row[day] = "\n\n".join(class_info)
            else:
                row[day] = ""
        
        grid_data.append(row)
    
    grid_df = pd.DataFrame(grid_data)
    if not grid_df.empty:
        display_colorful_grid(grid_df)


def show_room_view(df):
    """
    Display room utilization
    """
    st.subheader("🏫 Room Schedule")
    
    rooms = sorted(df['Room'].unique())
    selected_room = st.selectbox("Select Room", rooms)
    
    # Filter room's classes
    room_df = df[df['Room'] == selected_room].copy()
    
    if room_df.empty:
        st.info(f"No classes scheduled in {selected_room}")
        return
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Classes", len(room_df))
    col2.metric("Instructors", room_df['Instructor'].nunique())
    col3.metric("Sections", room_df['SectionID'].nunique())
    
    # Display as weekly grid
    st.markdown(f"### 📅 Weekly Schedule for Room {selected_room}")
    
    # Create filtered dataframe for grid
    filtered_df = df[df['Room'] == selected_room]
    
    # Get unique timeslots and create grid
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    timeslots = filtered_df[['StartTime', 'EndTime']].drop_duplicates().values.tolist()
    
    def time_to_minutes(time_str):
        try:
            time_part, period = time_str.strip().split()
            hours, minutes = map(int, time_part.split(':'))
            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0
            return hours * 60 + minutes
        except:
            return 9999
    
    timeslots.sort(key=lambda x: time_to_minutes(x[0]))
    
    grid_data = []
    for start_time, end_time in timeslots:
        row = {'Time': f"{start_time} - {end_time}"}
        
        for day in day_order:
            day_classes = filtered_df[(filtered_df['Day'] == day) & 
                                     (filtered_df['StartTime'] == start_time) & 
                                     (filtered_df['EndTime'] == end_time)]
            
            if not day_classes.empty:
                class_info = []
                for _, class_row in day_classes.iterrows():
                    display_text = (f"{class_row['CourseID']}\n"
                                   f"{class_row['SessionType']}\n"
                                   f"{class_row['Instructor']}\n"
                                   f"Section: {class_row['SectionID']}")
                    class_info.append(display_text)
                row[day] = "\n\n".join(class_info)
            else:
                row[day] = ""
        
        grid_data.append(row)
    
    grid_df = pd.DataFrame(grid_data)
    if not grid_df.empty:
        display_colorful_grid(grid_df)


def show_complete_view(df):
    """
    Display complete timetable with filters
    """
    st.subheader("📊 Complete Timetable")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        years = ["All"] + sorted([str(y) for y in df['CourseYear'].unique()])
        year_filter = st.selectbox("Filter by Year", years)
    with col2:
        sections = ["All"] + sorted(df['SectionID'].unique())
        section_filter = st.selectbox("Filter by Section", sections)
    with col3:
        sessions = ["All"] + sorted(df['SessionType'].unique())
        session_filter = st.selectbox("Filter by Session Type", sessions)
    
    # Apply filters
    filtered_df = df.copy()
    if year_filter != "All":
        filtered_df = filtered_df[filtered_df['CourseYear'] == int(year_filter)]
    if section_filter != "All":
        filtered_df = filtered_df[filtered_df['SectionID'] == section_filter]
    if session_filter != "All":
        filtered_df = filtered_df[filtered_df['SessionType'] == session_filter]
    
    if filtered_df.empty:
        st.info("No classes match the selected filters")
        return
    
    # Display as weekly grid
    st.markdown(f"### 📅 Complete Weekly Schedule")
    if year_filter != "All":
        st.caption(f"Showing: Year {year_filter}" + 
                  (f" | Section {section_filter}" if section_filter != "All" else "") +
                  (f" | {session_filter}" if session_filter != "All" else ""))
    
    # Create grid
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    timeslots = filtered_df[['StartTime', 'EndTime']].drop_duplicates().values.tolist()
    
    def time_to_minutes(time_str):
        try:
            time_part, period = time_str.strip().split()
            hours, minutes = map(int, time_part.split(':'))
            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0
            return hours * 60 + minutes
        except:
            return 9999
    
    timeslots.sort(key=lambda x: time_to_minutes(x[0]))
    
    grid_data = []
    for start_time, end_time in timeslots:
        row = {'Time': f"{start_time} - {end_time}"}
        
        for day in day_order:
            day_classes = filtered_df[(filtered_df['Day'] == day) & 
                                     (filtered_df['StartTime'] == start_time) & 
                                     (filtered_df['EndTime'] == end_time)]
            
            if not day_classes.empty:
                class_info = []
                for _, class_row in day_classes.iterrows():
                    display_text = (f"{class_row['CourseID']}\n"
                                   f"{class_row['SessionType']}\n"
                                   f"{class_row['Instructor']}\n"
                                   f"Section: {class_row['SectionID']}\n"
                                   f"Room: {class_row['Room']}")
                    class_info.append(display_text)
                row[day] = "\n\n".join(class_info)
            else:
                row[day] = ""
        
        grid_data.append(row)
    
    grid_df = pd.DataFrame(grid_data)
    if not grid_df.empty:
        display_colorful_grid(grid_df)


def show_statistics_page():
    """
    Display generation statistics
    """
    st.header("📈 Generation Statistics")
    
    if st.session_state.timetable_data is None:
        st.warning("No timetable generated yet")
        return
    
    df = st.session_state.timetable_data
    stats = st.session_state.generation_stats
    
    # Performance metrics
    st.subheader("⚡ Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Classes", stats['total_classes'])
    col2.metric("Coverage", f"{stats['coverage']:.1f}%")
    col3.metric("Generation Time", f"{stats['generation_time']:.1f}s")
    col4.metric("Courses Scheduled", stats['courses_scheduled'])
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Session type distribution
        session_counts = df['SessionType'].value_counts()
        fig = px.pie(
            values=session_counts.values,
            names=session_counts.index,
            title="Session Type Distribution",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Daily distribution
        day_counts = df['Day'].value_counts()
        fig = px.bar(
            x=day_counts.index,
            y=day_counts.values,
            title="Classes per Day",
            labels={'x': 'Day', 'y': 'Number of Classes'},
            color=day_counts.values,
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed statistics table
    st.subheader("📋 Detailed Statistics")
    
    stats_table = pd.DataFrame({
        'Metric': [
            'Total Classes Generated',
            'Unique Courses',
            'Unique Sections',
            'Unique Instructors',
            'Unique Rooms',
            'Average Classes per Day',
            'Generation Coverage',
            'Generation Time'
        ],
        'Value': [
            len(df),
            df['CourseID'].nunique(),
            df['SectionID'].nunique(),
            df['Instructor'].nunique(),
            df['Room'].nunique(),
            f"{len(df) / df['Day'].nunique():.1f}",
            f"{stats['coverage']:.1f}%",
            f"{stats['generation_time']:.1f}s"
        ]
    })
    
    st.dataframe(stats_table, use_container_width=True, hide_index=True)




if __name__ == "__main__":
    main()