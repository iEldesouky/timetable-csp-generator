import streamlit as st
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import sys
import os

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import our CSP modules
from data_loader import DataLoader
from csp_model import TimetableCSP
from constraints import HardConstraints, SoftConstraints, ForwardChecking
from solver import BacktrackingSolver
from utils import format_timetable_for_display, calculate_solution_metrics

def main():
    st.set_page_config(
        page_title="CSIT Timetable Generator", 
        page_icon="🎓", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎓 CSIT Automated Timetable Generator")
    st.markdown("**Intelligent Systems Project - Constraint Satisfaction Problem (CSP) Implementation**")
    
    # Initialize session state
    if 'data_loader' not in st.session_state:
        st.session_state.data_loader = DataLoader()
    if 'timetable' not in st.session_state:
        st.session_state.timetable = None
    if 'generation_time' not in st.session_state:
        st.session_state.generation_time = None
    if 'solver' not in st.session_state:
        st.session_state.solver = None
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", [
        "📊 Data Management", 
        "⚙️ Generate Timetable", 
        "📅 View Results",
        "📈 Performance Analysis"
    ])
    
    if page == "📊 Data Management":
        show_data_management()
    elif page == "⚙️ Generate Timetable":
        show_generation_page()
    elif page == "📅 View Results":
        show_results_page()
    elif page == "📈 Performance Analysis":
        show_analysis_page()

def show_data_management():
    st.header("📊 Data Management")
    
    tab1, tab2, tab3 = st.tabs(["📁 Upload Data", "✏️ Quick Load (Development)", "👀 View Current Data"])
    
    with tab1:
        st.subheader("Upload Your Dataset Files")
        st.info("Upload the required CSV files for timetable generation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Required Files**")
            uploaded_courses = st.file_uploader("Courses CSV", type="csv", key="courses_upload")
            uploaded_instructors = st.file_uploader("Instructors CSV", type="csv", key="instructors_upload")
            uploaded_rooms = st.file_uploader("Rooms CSV", type="csv", key="rooms_upload")
        
        with col2:
            st.markdown("**Required Files**")
            uploaded_timeslots = st.file_uploader("TimeSlots CSV", type="csv", key="timeslots_upload")
            st.markdown("**Optional Files**")
            uploaded_sections = st.file_uploader("Sections CSV (Optional)", type="csv", key="sections_upload")
        
        if st.button("🚀 Load All Uploaded Data", type="primary", use_container_width=True):
            if uploaded_courses and uploaded_instructors and uploaded_rooms and uploaded_timeslots:
                with st.spinner("Loading and validating data..."):
                    success = st.session_state.data_loader.load_all_data(
                        uploaded_courses, uploaded_instructors, uploaded_rooms, 
                        uploaded_timeslots, uploaded_sections
                    )
                if success:
                    st.success("🎉 All data loaded successfully! Proceed to Generate Timetable.")
                    st.balloons()
            else:
                st.error("❌ Please upload all required CSV files first!")
    
    with tab2:
        st.subheader("Quick Load for Development")
        st.info("Use this to quickly load the sample data from the 'data' folder")
        
        if st.button("📂 Load Sample Data from data/ folder", use_container_width=True):
            try:
                # Use relative paths to load from data folder
                success = st.session_state.data_loader.load_all_data(
                    "data/Courses.csv",
                    "data/Instructors.csv", 
                    "data/Rooms.csv",
                    "data/TimeSlots.csv",
                    None  # No sections file, will create default
                )
                if success:
                    st.success("✅ Sample data loaded from data/ folder!")
            except Exception as e:
                st.error(f"❌ Error loading sample data: {str(e)}")
                st.info("Make sure your CSV files are in the 'data' folder")
    
    with tab3:
        st.subheader("Current Dataset Preview")
        
        if st.session_state.data_loader.courses_df is None:
            st.warning("No data loaded yet. Please upload data first.")
            return
        
        data_type = st.selectbox("Select data to view", 
                                ["Courses", "Instructors", "Rooms", "TimeSlots", "Sections"])
        
        if data_type == "Courses":
            st.dataframe(st.session_state.data_loader.courses_df, use_container_width=True)
        elif data_type == "Instructors":
            st.dataframe(st.session_state.data_loader.instructors_df, use_container_width=True)
        elif data_type == "Rooms":
            st.dataframe(st.session_state.data_loader.rooms_df, use_container_width=True)
        elif data_type == "TimeSlots":
            st.dataframe(st.session_state.data_loader.timeslots_df, use_container_width=True)
        elif data_type == "Sections":
            st.dataframe(st.session_state.data_loader.sections_df, use_container_width=True)
        
        # Show data summary
        st.subheader("Data Summary")
        summary = st.session_state.data_loader.get_data_summary()
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Courses", summary['courses_count'])
        with col2:
            st.metric("Instructors", summary['instructors_count'])
        with col3:
            st.metric("Rooms", summary['rooms_count'])
        with col4:
            st.metric("TimeSlots", summary['timeslots_count'])
        with col5:
            st.metric("Sections", summary['sections_count'])

def show_generation_page():
    st.header("⚙️ Generate Timetable")
    
    # Check if data is loaded
    if st.session_state.data_loader.courses_df is None:
        st.error("❌ No data loaded! Please go to 'Data Management' and upload your data first.")
        return
    
    st.success("✅ Data loaded and ready for timetable generation!")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Constraint Configuration")
        
        st.markdown("**Hard Constraints** (Always enforced)")
        st.checkbox("No instructor double-booking", value=True, disabled=True)
        st.checkbox("No room double-booking", value=True, disabled=True)
        st.checkbox("Room type compatibility", value=True, disabled=True)
        st.checkbox("Instructor qualifications", value=True, disabled=True)
        st.checkbox("Instructor availability", value=True, disabled=True)
        
        st.markdown("**Soft Constraints** (Preferences)")
        avoid_gaps = st.checkbox("Avoid gaps in student schedules", value=True)
        avoid_extreme_times = st.checkbox("Avoid early morning/late evening", value=True)
        even_distribution = st.checkbox("Distribute classes evenly across week", value=True)
    
    with col2:
        st.subheader("Solver Configuration")
        solver_choice = st.selectbox("Algorithm", 
                                   ["Backtracking (Basic)", 
                                    "Backtracking + MRV", 
                                    "Backtracking + MRV + LCV",
                                    "Backtracking + Forward Checking"])
        
        timeout = st.slider("Timeout (seconds)", min_value=10, max_value=300, value=60)
        
        if st.button("🎯 Generate Timetable", type="primary", use_container_width=True):
            generate_timetable(solver_choice, timeout)

def generate_timetable(solver_choice, timeout):
    """Generate timetable using CSP solver"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Initializing CSP model...")
        progress_bar.progress(10)
        
        # Initialize CSP
        csp = TimetableCSP(st.session_state.data_loader)
        
        status_text.text("Initializing solver...")
        progress_bar.progress(30)
        
        # Initialize solver
        st.session_state.solver = BacktrackingSolver(csp)
        
        status_text.text(f"Solving with {solver_choice}...")
        progress_bar.progress(50)
        
        # Start timer
        start_time = time.time()
        
        # Solve based on chosen algorithm
        if solver_choice == "Backtracking (Basic)":
            solution = st.session_state.solver.backtracking_search(timeout=timeout)
        elif solver_choice == "Backtracking + MRV":
            solution = st.session_state.solver.backtracking_with_mrv(timeout=timeout)
        elif solver_choice == "Backtracking + MRV + LCV":
            solution = st.session_state.solver.backtracking_with_mrv_lcv(timeout=timeout)
        else:  # Backtracking + Forward Checking
            solution = st.session_state.solver.backtracking_with_forward_checking(timeout=timeout)
        
        end_time = time.time()
        
        progress_bar.progress(90)
        status_text.text("Formatting results...")
        
        # Store results
        st.session_state.timetable = solution
        st.session_state.generation_time = end_time - start_time
        
        progress_bar.progress(100)
        status_text.text("✅ Timetable generated successfully!")
        
        # Auto-navigate to results page
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error generating timetable: {str(e)}")
        status_text.text("Generation failed!")

def show_results_page():
    st.header("📅 Generated Timetable")
    
    if st.session_state.timetable is None:
        st.warning("No timetable generated yet. Go to the 'Generate Timetable' page to create one.")
        return
    
    st.success(f"Timetable generated successfully in {st.session_state.generation_time:.2f} seconds!")
    
    # Display timetable statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Classes Scheduled", len(st.session_state.timetable))
    with col2:
        st.metric("Generation Time", f"{st.session_state.generation_time:.2f}s")
    with col3:
        st.metric("Backtracks", st.session_state.solver.backtrack_count)
    with col4:
        st.metric("Constraint Checks", st.session_state.solver.constraint_checks)
    
    # Display timetable in different formats
    view_option = st.radio("View as:", ["Table View", "By Day", "By Room", "By Instructor"], horizontal=True)
    
    if view_option == "Table View":
        display_timetable_table()
    elif view_option == "By Day":
        display_by_day()
    elif view_option == "By Room":
        display_by_room()
    elif view_option == "By Instructor":
        display_by_instructor()
    
    # Export options
    st.subheader("Export Timetable")
    col1, col2 = st.columns(2)
    
    with col1:
        # Convert to DataFrame for download
        timetable_df = format_solution_to_dataframe(st.session_state.timetable)
        st.download_button(
            "📥 Download as CSV",
            timetable_df.to_csv(index=False),
            "generated_timetable.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col2:
        if st.button("🔄 Generate New Timetable", use_container_width=True):
            st.session_state.timetable = None
            st.rerun()

def display_timetable_table():
    """Display timetable as a table"""
    timetable_df = format_solution_to_dataframe(st.session_state.timetable)
    st.dataframe(timetable_df, use_container_width=True)

def display_by_day():
    """Display timetable organized by day"""
    timetable_df = format_solution_to_dataframe(st.session_state.timetable)
    if 'Day' in timetable_df.columns:
        day = st.selectbox("Select day", sorted(timetable_df['Day'].unique()))
        day_data = timetable_df[timetable_df['Day'] == day]
        st.dataframe(day_data, use_container_width=True)

def display_by_room():
    """Display timetable organized by room"""
    timetable_df = format_solution_to_dataframe(st.session_state.timetable)
    if 'Room' in timetable_df.columns:
        room = st.selectbox("Select room", sorted(timetable_df['Room'].unique()))
        room_data = timetable_df[timetable_df['Room'] == room]
        st.dataframe(room_data, use_container_width=True)

def display_by_instructor():
    """Display timetable organized by instructor"""
    timetable_df = format_solution_to_dataframe(st.session_state.timetable)
    if 'Instructor' in timetable_df.columns:
        instructor = st.selectbox("Select instructor", sorted(timetable_df['Instructor'].unique()))
        instructor_data = timetable_df[timetable_df['Instructor'] == instructor]
        st.dataframe(instructor_data, use_container_width=True)

def format_solution_to_dataframe(solution):
    """Convert CSP solution to pandas DataFrame for display"""
    rows = []
    for variable_id, assignment in solution.items():
        timeslot, room, instructor = assignment
        day = timeslot.split()[0]  # Extract day
        
        # Get course name
        course_id = variable_id.split('_')[0]
        course_name = st.session_state.data_loader.courses_df[
            st.session_state.data_loader.courses_df['CourseID'] == course_id
        ]['CourseName'].iloc[0]
        
        # Get instructor name
        instructor_name = st.session_state.data_loader.instructors_df[
            st.session_state.data_loader.instructors_df['InstructorID'] == instructor
        ]['Name'].iloc[0]
        
        rows.append({
            'Course Section': variable_id,
            'Course Name': course_name,
            'Day': day,
            'Time Slot': timeslot,
            'Room': room,
            'Instructor': instructor_name,
            'Instructor ID': instructor
        })
    
    return pd.DataFrame(rows)

def show_analysis_page():
    st.header("📈 Performance Analysis")
    
    if st.session_state.timetable is None:
        st.warning("Generate a timetable first to see analysis")
        return
    
    # Performance metrics
    st.subheader("Solver Performance")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Generation Time", f"{st.session_state.generation_time:.2f}s")
    with col2:
        st.metric("Backtrack Count", st.session_state.solver.backtrack_count)
    with col3:
        st.metric("Constraint Checks", st.session_state.solver.constraint_checks)
    with col4:
        success_rate = "100%" if st.session_state.timetable else "0%"
        st.metric("Success Rate", success_rate)
    
    # Visualization
    st.subheader("Distribution Analysis")
    timetable_df = format_solution_to_dataframe(st.session_state.timetable)
    
    # Classes per day
    if 'Day' in timetable_df.columns:
        fig1 = px.histogram(timetable_df, x='Day', title="Classes Distribution by Day")
        st.plotly_chart(fig1, use_container_width=True)
    
    # Classes per instructor
    if 'Instructor' in timetable_df.columns:
        instructor_counts = timetable_df['Instructor'].value_counts().reset_index()
        instructor_counts.columns = ['Instructor', 'Class Count']
        fig2 = px.bar(instructor_counts, x='Instructor', y='Class Count', 
                     title="Classes per Instructor")
        st.plotly_chart(fig2, use_container_width=True)

if __name__ == "__main__":
    main()
