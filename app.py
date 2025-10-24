# app.py - FIXED STREAMLIT CONFIGURATION

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Set page config MUST be the first Streamlit command
st.set_page_config(
    page_title="CSIT Timetable Generator", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add the src directory to Python path to find our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

# Import our CSP modules from src folder
try:
    from data_loader import DataLoader
    from csp_model import TimetableCSP
    from solver import BacktrackingSolver
    from utils import (format_timetable_for_display, calculate_solution_metrics, 
                      create_timetable_visualization, create_instructor_workload_chart,
                      export_timetable_to_csv, validate_solution_completeness,
                      generate_solution_report)
    st.success("✅ All modules imported successfully!")
except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.error(f"Looking for modules in: {src_dir}")
    st.error("Files found in src/:")
    try:
        src_files = os.listdir(src_dir)
        for file in src_files:
            st.error(f"  - {file}")
    except:
        st.error("Could not list src/ directory")
    st.stop()

def main():
    st.title("🎓 CSIT Automated Timetable Generator")
    st.markdown("**Using Constraint Satisfaction Problems (CSP) - Exact Excel Structure**")
    
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
        "📅 View Results"
    ])
    
    if page == "📊 Data Management":
        show_data_management()
    elif page == "⚙️ Generate Timetable":
        show_generation_page()
    elif page == "📅 View Results":
        show_results_page()

def show_data_management():
    st.header("📊 Data Management")
    
    st.info("""
    **Required CSV Files Structure (from Excel):**
    - **Courses.csv**: course_id, course_name, type
    - **Instructors.csv**: instructor_id, name, role, qualifications  
    - **Rooms.csv**: room_id, type, capacity
    - **TimeSlots.csv**: time_slot_id, day, start_time, end_time
    - **Sections.csv**: section_id, group_number, year, student_count
    - **Curriculum.csv**: year, course_id
    """)
    
    tab1, tab2 = st.tabs(["📁 Upload Data", "👀 View Current Data"])
    
    with tab1:
        st.subheader("Upload Your CSV Files")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Required Files**")
            uploaded_courses = st.file_uploader("Courses CSV", type="csv", key="courses_upload")
            uploaded_instructors = st.file_uploader("Instructors CSV", type="csv", key="instructors_upload")
            uploaded_rooms = st.file_uploader("Rooms CSV", type="csv", key="rooms_upload")
        
        with col2:
            st.markdown("**Required Files**")
            uploaded_timeslots = st.file_uploader("TimeSlots CSV", type="csv", key="timeslots_upload")
            uploaded_sections = st.file_uploader("Sections CSV", type="csv", key="sections_upload")
            uploaded_curriculum = st.file_uploader("Curriculum CSV", type="csv", key="curriculum_upload")
        
        if st.button("🚀 Load All Data", type="primary", use_container_width=True):
            if (uploaded_courses and uploaded_instructors and uploaded_rooms and 
                uploaded_timeslots and uploaded_sections and uploaded_curriculum):
                
                with st.spinner("Loading and validating CSIT data..."):
                    success = st.session_state.data_loader.load_all_data(
                        uploaded_courses, uploaded_instructors, uploaded_rooms, 
                        uploaded_timeslots, uploaded_sections, uploaded_curriculum
                    )
                    
                    if success:
                        # Validate data consistency
                        st.session_state.data_loader.validate_data_consistency()
                        st.success("🎉 All data loaded successfully! Proceed to Generate Timetable.")
                        st.balloons()
            else:
                st.error("❌ Please upload all 6 required CSV files!")
    
    with tab2:
        st.subheader("Current Dataset Preview")
        
        if st.session_state.data_loader.courses_df is None:
            st.warning("No data loaded yet. Please upload data first.")
            return
        
        data_type = st.selectbox("Select data to view", 
                                ["Courses", "Instructors", "Rooms", "TimeSlots", "Sections", "Curriculum"])
        
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
        elif data_type == "Curriculum":
            st.dataframe(st.session_state.data_loader.curriculum_df, use_container_width=True)
        
        # Show data summary
        st.subheader("📊 Data Summary")
        summary = st.session_state.data_loader.get_data_summary()
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
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
        with col6:
            st.metric("Curriculum", summary['curriculum_entries'])

def show_generation_page():
    st.header("⚙️ Generate Timetable")
    
    # Check if data is loaded
    if st.session_state.data_loader.courses_df is None:
        st.error("❌ No data loaded! Please go to 'Data Management' and upload your data first.")
        return
    
    st.success("✅ Data loaded and ready for timetable generation!")
    
    # Display problem complexity
    if st.session_state.data_loader.sections_df is not None:
        total_sections = len(st.session_state.data_loader.sections_df)
        st.info(f"📊 Problem Size: {total_sections} sections across all years")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Constraint Configuration")
        
        st.markdown("**Hard Constraints** (Always enforced)")
        with st.expander("View Hard Constraints", expanded=True):
            st.write("✅ No instructor double-booking")
            st.write("✅ No room double-booking")
            st.write("✅ Room type compatibility")
            st.write("✅ Room capacity constraints")
            st.write("✅ Instructor qualifications")
            st.write("✅ Elective course coordination (LRA104/LRA105)")
            st.write("✅ Same course lecture consistency")
        
        st.markdown("**Soft Constraints** (Preferences)")
        with st.expander("Configure Soft Constraints"):
            st.checkbox("Avoid gaps in student schedules", value=True, disabled=True)
            st.checkbox("Avoid early morning/late evening", value=True, disabled=True)
            st.checkbox("Distribute classes evenly across week", value=True, disabled=True)
            st.checkbox("Balance instructor workload", value=True, disabled=True)
    
    with col2:
        st.subheader("Solver Configuration")
        
        timeout = st.slider("Timeout (seconds)", min_value=30, max_value=300, value=120, 
                           help="Maximum time to spend searching for solution")
        
        st.markdown("---")
        
        if st.button("🎯 Generate Timetable", type="primary", use_container_width=True):
            generate_timetable(timeout)
        
        # Add this button in the generation page, next to the main generate button
    if st.button("🧪 Test with Small Subset", use_container_width=True):
        test_with_small_subset()

    def test_with_small_subset():
        """Test with a smaller subset of data for debugging"""
        # Create a minimal test case
        st.info("Testing with minimal data subset...")
    
        # We'll use the existing data but show what's being processed
        if st.session_state.data_loader.courses_df is not None:
            st.write("**Courses available:**", len(st.session_state.data_loader.courses_df))
            st.write("**Sections available:**", len(st.session_state.data_loader.sections_df))
            st.write("**Timeslots available:**", len(st.session_state.data_loader.timeslots_df))
            st.write("**Rooms available:**", len(st.session_state.data_loader.rooms_df))
            st.write("**Instructors available:**", len(st.session_state.data_loader.instructors_df))

        # Quick actions
        st.markdown("### Quick Actions")
        if st.button("🔄 Clear Results", use_container_width=True):
            st.session_state.timetable = None
            st.session_state.solver = None
            st.success("Results cleared!")

def generate_timetable(timeout):
    """Generate timetable using CSP solver with debug info"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Initializing CSP model...")
        progress_bar.progress(10)
        
        # Initialize CSP
        csp = TimetableCSP(st.session_state.data_loader)
        
        # Show debug information
        with st.expander("🔍 CSP Configuration Details", expanded=False):
            csp.print_debug_info()
        
        status_text.text("Initializing solver...")
        progress_bar.progress(30)
        
        # Initialize solver
        st.session_state.solver = BacktrackingSolver(csp)
        
        status_text.text("Solving with Backtracking + MRV + LCV + Forward Checking...")
        st.info("This may take a few minutes for large problems...")
        progress_bar.progress(50)
        
        # Start timer
        start_time = time.time()
        
        # Solve
        solution = st.session_state.solver.backtracking_search(timeout=timeout)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        progress_bar.progress(90)
        status_text.text("Formatting results...")
        
        # Store results
        st.session_state.timetable = solution
        st.session_state.generation_time = generation_time
        
        progress_bar.progress(100)
        
        if solution:
            status_text.text("✅ Timetable generated successfully!")
            st.balloons()
        else:
            status_text.text("⚠️ No solution found within timeout. Try increasing timeout or check CSP debug info.")
        
        # Auto-navigate to results page
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error generating timetable: {str(e)}")
        import traceback
        st.error(f"Debug: {traceback.format_exc()}")
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
    
    # Calculate and display solution metrics
    timetable_df = format_timetable_for_display(st.session_state.timetable, st.session_state.data_loader)
    metrics = calculate_solution_metrics(st.session_state.timetable, st.session_state.data_loader)
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Lectures", metrics['lectures_count'])
    with col2:
        st.metric("Labs", metrics['labs_count'])
    with col3:
        st.metric("Tutorials", metrics['tutorials_count'])
    
    # Display timetable in different formats
    st.subheader("Timetable Views")
    view_option = st.radio("View as:", 
                          ["Table View", "By Day", "By Room", "By Instructor", "Visualization"], 
                          horizontal=True)
    
    if view_option == "Table View":
        display_timetable_table(timetable_df)
    elif view_option == "By Day":
        display_by_day(timetable_df)
    elif view_option == "By Room":
        display_by_room(timetable_df)
    elif view_option == "By Instructor":
        display_by_instructor(timetable_df)
    elif view_option == "Visualization":
        display_timetable_visualization(timetable_df)
    
    # Export and analysis section
    st.subheader("Export & Analysis")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Download as CSV
        csv_data = export_timetable_to_csv(timetable_df)
        st.download_button(
            "📥 Download as CSV",
            csv_data,
            "csit_timetable.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col2:
        # Generate report
        if st.button("📋 Generate Report", use_container_width=True):
            report = generate_solution_report(
                st.session_state.timetable, 
                st.session_state.data_loader,
                st.session_state.solver.get_performance_metrics()
            )
            st.text_area("Solution Report", report, height=300)
    
    with col3:
        # Validation
        if st.button("✅ Validate Solution", use_container_width=True):
            validation = validate_solution_completeness(st.session_state.timetable, st.session_state.solver.csp)
            if validation['is_complete']:
                st.success("Solution is 100% complete!")
            else:
                st.warning(f"Solution is {validation['completion_percentage']:.1f}% complete")
                st.write(f"Missing {len(validation['missing_assignments'])} assignments")
    
    # Performance analysis
    st.subheader("Performance Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Day distribution chart
        if 'day_distribution' in metrics:
            fig = px.bar(x=list(metrics['day_distribution'].keys()), 
                        y=list(metrics['day_distribution'].values()),
                        title="Classes Distribution by Day",
                        labels={'x': 'Day', 'y': 'Number of Classes'})
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Instructor workload
        workload_chart = create_instructor_workload_chart(metrics)
        if workload_chart:
            st.plotly_chart(workload_chart, use_container_width=True)

def display_timetable_table(timetable_df):
    """Display timetable as a searchable and filterable table"""
    st.dataframe(timetable_df, use_container_width=True)
    
    # Add filters
    st.subheader("Filter Timetable")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days = st.multiselect("Filter by Day", options=timetable_df['Day'].unique())
    with col2:
        rooms = st.multiselect("Filter by Room", options=timetable_df['Room'].unique())
    with col3:
        instructors = st.multiselect("Filter by Instructor", options=timetable_df['Instructor'].unique())
    
    # Apply filters
    filtered_df = timetable_df
    if days:
        filtered_df = filtered_df[filtered_df['Day'].isin(days)]
    if rooms:
        filtered_df = filtered_df[filtered_df['Room'].isin(rooms)]
    if instructors:
        filtered_df = filtered_df[filtered_df['Instructor'].isin(instructors)]
    
    if len(filtered_df) < len(timetable_df):
        st.write(f"Showing {len(filtered_df)} of {len(timetable_df)} classes")
        st.dataframe(filtered_df, use_container_width=True)

def display_by_day(timetable_df):
    """Display timetable organized by day"""
    day = st.selectbox("Select day", sorted(timetable_df['Day'].unique()))
    day_data = timetable_df[timetable_df['Day'] == day].sort_values('Start Time')
    st.dataframe(day_data, use_container_width=True)

def display_by_room(timetable_df):
    """Display timetable organized by room"""
    room = st.selectbox("Select room", sorted(timetable_df['Room'].unique()))
    room_data = timetable_df[timetable_df['Room'] == room].sort_values(['Day', 'Start Time'])
    st.dataframe(room_data, use_container_width=True)

def display_by_instructor(timetable_df):
    """Display timetable organized by instructor"""
    instructor = st.selectbox("Select instructor", sorted(timetable_df['Instructor'].unique()))
    instructor_data = timetable_df[timetable_df['Instructor'] == instructor].sort_values(['Day', 'Start Time'])
    st.dataframe(instructor_data, use_container_width=True)

def display_timetable_visualization(timetable_df):
    """Display timetable visualization"""
    try:
        fig = create_timetable_visualization(timetable_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No visualization available for the current data")
    except Exception as e:
        st.error(f"Could not generate visualization: {str(e)}")

if __name__ == "__main__":
    main()