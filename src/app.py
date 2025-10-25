# [file name]: app.py (UPDATED FOR NEW SYSTEM)
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
src_dir = current_dir  # Since we're in src folder
sys.path.append(src_dir)

# Import our NEW CSP modules
try:
    from data_loader import DataLoader
    from csp_model import TimetableCSP
    from solver import BacktrackingSolver
    from performance_analysis import PerformanceAnalyzer
    from utils import format_timetable_for_display, export_timetable_to_csv
    st.success("✅ All modules imported successfully!")
except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.error("Please make sure all required files are in the src/ directory")
    st.stop()

def main():
    st.title("🎓 CSIT Automated Timetable Generator")
    st.markdown("**Using Constraint Satisfaction Problems (CSP) - Working Implementation**")
    
    # Initialize session state
    if 'data_loader' not in st.session_state:
        st.session_state.data_loader = DataLoader()
    if 'timetable' not in st.session_state:
        st.session_state.timetable = None
    if 'generation_time' not in st.session_state:
        st.session_state.generation_time = None
    if 'solver' not in st.session_state:
        st.session_state.solver = None
    if 'csp' not in st.session_state:
        st.session_state.csp = None
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", [
        "📊 Data Management", 
        "⚙️ Generate Timetable", 
        "📅 View Results",
        "📊 Performance Analysis"
    ])
    
    if page == "📊 Data Management":
        show_data_management()
    elif page == "⚙️ Generate Timetable":
        show_generation_page()
    elif page == "📅 View Results":
        show_results_page()
    elif page == "📊 Performance Analysis":
        show_performance_analysis()

def show_data_management():
    st.header("📊 Data Management")
    
    st.info("""
    **Required CSV Files Structure (Your Friend's Format):**
    - **courses.csv**: CourseID, CourseName, Type, Year
    - **instructors.csv**: InstructorID, Name, Role, QualifiedCourses  
    - **rooms.csv**: RoomID, Type, Capacity
    - **timeslots.csv**: Day, StartTime, EndTime
    - **sections.csv**: SectionID, Capacity
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
        
        if st.button("🚀 Load All Data", type="primary", use_container_width=True):
            if (uploaded_courses and uploaded_instructors and uploaded_rooms and 
                uploaded_timeslots and uploaded_sections):
                
                with st.spinner("Loading and validating data..."):
                    success = st.session_state.data_loader.load_all_data(
                        uploaded_courses, uploaded_instructors, uploaded_rooms, 
                        uploaded_timeslots, uploaded_sections
                    )
                    
                    if success:
                        # Validate data consistency
                        st.session_state.data_loader.validate_data_consistency()
                        st.success("🎉 All data loaded successfully! Proceed to Generate Timetable.")
                        st.balloons()
                    else:
                        st.error("❌ Failed to load data. Please check file formats.")
            else:
                st.error("❌ Please upload all 5 required CSV files!")
    
    with tab2:
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
        st.subheader("📊 Data Summary")
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
    
    # Display problem complexity
    if st.session_state.data_loader.sections_df is not None:
        total_sections = len(st.session_state.data_loader.sections_df)
        st.info(f"📊 Problem Size: {total_sections} sections across all years")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Algorithm Configuration")
        
        st.markdown("**Working Features (Friend's Implementation)**")
        with st.expander("View Implementation Details", expanded=True):
            st.write("✅ **Course-Group-Session Variables**: Course::G0::Lecture format")
            st.write("✅ **Smart Section Grouping**: Lectures(3-4), Labs(2), TUTs(1)")
            st.write("✅ **Triple Constraint Checking**: Instructor + Room + Sections")
            st.write("✅ **Department-Based Assignment**: Years 3-4 department matching")
            st.write("✅ **Strict Role Assignment**: Professors→Lectures, Assistants→Labs/TUTs")
            st.write("✅ **Forward Checking + MRV + LCV**: Advanced search heuristics")
        
        st.markdown("**Search Algorithm**")
        st.info("Using forward checking with backtracking, MRV, and degree heuristics")
    
    with col2:
        st.subheader("Solver Configuration")
        
        timeout = st.slider("Timeout (seconds)", min_value=30, max_value=300, value=120, 
                           help="Maximum time to spend searching for solution")
        
        st.markdown("---")
        
        if st.button("🎯 Generate Timetable", type="primary", use_container_width=True):
            generate_timetable(timeout)
        
        if st.button("🔄 Clear Previous Results", use_container_width=True):
            st.session_state.timetable = None
            st.session_state.solver = None
            st.session_state.csp = None
            st.session_state.generation_time = None
            st.success("Previous results cleared!")

def generate_timetable(timeout):
    """Generate timetable using NEW CSP solver"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Initializing CSP model...")
        progress_bar.progress(10)
        
        # Initialize CSP with friend's working architecture
        csp = TimetableCSP(st.session_state.data_loader)
        st.session_state.csp = csp
        
        # Show debug information
        with st.expander("🔍 CSP Configuration Details", expanded=False):
            csp.print_debug_info()
        
        status_text.text("Initializing solver...")
        progress_bar.progress(30)
        
        # Initialize solver with friend's forward checking
        solver = BacktrackingSolver(csp)
        st.session_state.solver = solver
        
        status_text.text("Solving with Forward Checking + MRV + LCV...")
        st.info("This uses your friend's working algorithm. Please wait...")
        progress_bar.progress(50)
        
        # Start timer
        start_time = time.time()
        
        # Solve using friend's algorithm
        solution = solver.solve(timeout=timeout)
        
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
            
            # Show quick stats
            st.success(f"**Generated {len(solution)} assignments in {generation_time:.2f} seconds**")
            
            # Auto-navigate to results page
            st.rerun()
        else:
            status_text.text("⚠️ No solution found within timeout.")
            st.error("""
            **Possible reasons:**
            - Not enough timeslots/rooms/instructors
            - Overly strict constraints
            - Try increasing timeout or checking CSP debug info
            """)
        
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
    
    st.success(f"✅ Timetable generated in {st.session_state.generation_time:.2f} seconds!")
    
    # Display timetable statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Assignments", len(st.session_state.timetable))
    with col2:
        st.metric("Generation Time", f"{st.session_state.generation_time:.2f}s")
    with col3:
        st.metric("Backtracks", st.session_state.solver.backtrack_count)
    with col4:
        st.metric("Constraint Checks", st.session_state.solver.constraint_checks)
    
    # Format timetable for display
    timetable_df = format_timetable_for_display(
        st.session_state.timetable, 
        st.session_state.data_loader,
        st.session_state.csp
    )
    
    # Display metrics
    if not timetable_df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            lectures = len(timetable_df[timetable_df['Session'] == 'Lecture'])
            st.metric("Lectures", lectures)
        with col2:
            labs = len(timetable_df[timetable_df['Session'] == 'Lab'])
            st.metric("Labs", labs)
        with col3:
            tuts = len(timetable_df[timetable_df['Session'] == 'TUT'])
            st.metric("Tutorials", tuts)
    
    # Display timetable in different formats
    st.subheader("Timetable Views")
    view_option = st.radio("View as:", 
                          ["Table View", "By Day", "By Room", "By Instructor", "By Year"], 
                          horizontal=True)
    
    if view_option == "Table View":
        display_timetable_table(timetable_df)
    elif view_option == "By Day":
        display_by_day(timetable_df)
    elif view_option == "By Room":
        display_by_room(timetable_df)
    elif view_option == "By Instructor":
        display_by_instructor(timetable_df)
    elif view_option == "By Year":
        display_by_year(timetable_df)
    
    # Export section
    st.subheader("Export & Download")
    col1, col2 = st.columns(2)
    
    with col1:
        # Download as CSV
        if not timetable_df.empty:
            csv_data = export_timetable_to_csv(timetable_df)
            st.download_button(
                "📥 Download as CSV",
                csv_data,
                "csit_timetable.csv",
                "text/csv",
                use_container_width=True
            )
    
    with col2:
        if st.button("📊 Go to Performance Analysis", use_container_width=True):
            st.session_state.page = "📊 Performance Analysis"
            st.rerun()

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

def display_by_year(timetable_df):
    """Display timetable organized by year"""
    # Extract year from SectionID (e.g., "1/5" -> 1, "3/CNC/1" -> 3)
    def extract_year(section_id):
        try:
            return int(str(section_id).split('/')[0])
        except:
            return 0
    
    timetable_df['Year'] = timetable_df['SectionID'].apply(extract_year)
    year = st.selectbox("Select year", sorted(timetable_df['Year'].unique()))
    year_data = timetable_df[timetable_df['Year'] == year].sort_values(['Day', 'Start Time'])
    st.dataframe(year_data.drop('Year', axis=1), use_container_width=True)

def show_performance_analysis():
    st.header("📊 Performance Analysis")
    
    if st.session_state.timetable is None or st.session_state.solver is None:
        st.warning("No timetable generated yet. Generate a timetable first to see performance analysis.")
        return
    
    # Get performance metrics
    solver_metrics = st.session_state.solver.get_performance_metrics()
    
    # Run comprehensive analysis
    analysis = PerformanceAnalyzer.analyze_solution_performance(
        st.session_state.timetable,
        st.session_state.csp,
        solver_metrics,
        st.session_state.data_loader
    )
    
    # Display performance dashboard
    PerformanceAnalyzer.create_performance_dashboard(analysis)
    
    # Additional detailed metrics
    st.subheader("🔍 Detailed Solver Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Backtrack Calls", solver_metrics.get('backtrack_calls', 0))
    with col2:
        st.metric("Max Search Depth", solver_metrics.get('max_depth', 0))
    with col3:
        st.metric("Completion %", f"{solver_metrics.get('completion_percentage', 0):.1f}%")
    with col4:
        st.metric("Variables/Second", f"{solver_metrics.get('variables_assigned', 0) / solver_metrics.get('search_time', 1):.1f}")

if __name__ == "__main__":
    main()