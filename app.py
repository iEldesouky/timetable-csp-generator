import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sys
import os

# Set page config MUST be the first Streamlit command
st.set_page_config(
    page_title="CSIT Timetable Generator", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import CSP solver
try:
    from csp_solver import generate_timetable, format_timetable_for_display
    st.success("✅ CSP Solver imported successfully!")
except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.error("Please make sure csp_solver.py is in the same directory")
    st.stop()

def main():
    st.title("🎓 CSIT Automated Timetable Generator")
    st.markdown("**Using Constraint Satisfaction Problems (CSP) - Proven Implementation**")
    
    # Initialize session state
    if 'timetable_df' not in st.session_state:
        st.session_state.timetable_df = None
    if 'generation_time' not in st.session_state:
        st.session_state.generation_time = None
    if 'generation_stats' not in st.session_state:
        st.session_state.generation_stats = None
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", [
        "📊 Data Upload & Generate", 
        "📅 View Timetable",
        "📈 Statistics"
    ])
    
    if page == "📊 Data Upload & Generate":
        show_upload_and_generate()
    elif page == "📅 View Timetable":
        show_timetable_view()
    elif page == "📈 Statistics":
        show_statistics()

def show_upload_and_generate():
    st.header("📊 Upload Data & Generate Timetable")
    
    st.info("""
    **Required CSV Files:**
    - **courses.csv**: CourseID, CourseName, Credits, Type, Year, Shared
    - **instructors.csv**: InstructorID, Name, Role, PreferredSlots, QualifiedCourses  
    - **rooms.csv**: RoomID, Type, Capacity
    - **timeslots.csv**: Day, StartTime, EndTime, Duration
    - **sections.csv**: SectionID, Capacity
    """)
    
    # File uploaders
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 Core Data Files")
        courses_file = st.file_uploader("Upload Courses CSV", type="csv", key="courses")
        instructors_file = st.file_uploader("Upload Instructors CSV", type="csv", key="instructors")
        rooms_file = st.file_uploader("Upload Rooms CSV", type="csv", key="rooms")
    
    with col2:
        st.subheader("📁 Scheduling Files")
        timeslots_file = st.file_uploader("Upload Timeslots CSV", type="csv", key="timeslots")
        sections_file = st.file_uploader("Upload Sections CSV", type="csv", key="sections")
    
    # Generation settings
    st.subheader("⚙️ Generation Settings")
    col1, col2 = st.columns(2)
    with col1:
        timeout = st.slider("Search Timeout (seconds)", 30, 300, 120, 30)
    with col2:
        enable_permissive = st.checkbox("Enable Permissive Mode (if strict fails)", value=False)
    
    # Generate button
    if st.button("🚀 Generate Timetable", type="primary", use_container_width=True):
        # Check all files uploaded
        if not all([courses_file, instructors_file, rooms_file, timeslots_file, sections_file]):
            st.error("❌ Please upload all 5 CSV files before generating")
            return
        
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Load data
            status_text.text("📂 Loading CSV files...")
            progress_bar.progress(10)
            
            courses_df = pd.read_csv(courses_file)
            instructors_df = pd.read_csv(instructors_file)
            rooms_df = pd.read_csv(rooms_file)
            timeslots_df = pd.read_csv(timeslots_file)
            sections_df = pd.read_csv(sections_file)
            
            status_text.text("✅ Data loaded successfully")
            progress_bar.progress(20)
            
            # Show data summary
            with st.expander("📊 Data Summary", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Courses", len(courses_df))
                    st.metric("Instructors", len(instructors_df))
                with col2:
                    st.metric("Rooms", len(rooms_df))
                    st.metric("Timeslots", len(timeslots_df))
                with col3:
                    st.metric("Sections", len(sections_df))
            
            # Step 2: Generate timetable
            status_text.text("🔄 Running CSP solver (this may take a while)...")
            progress_bar.progress(30)
            
            start_time = time.time()
            
            result = generate_timetable(
                courses_df=courses_df,
                instructors_df=instructors_df,
                rooms_df=rooms_df,
                timeslots_df=timeslots_df,
                sections_df=sections_df,
                force_permissive=enable_permissive,
                timeout=timeout
            )
            
            generation_time = time.time() - start_time
            
            if result is None:
                progress_bar.progress(100)
                status_text.text("❌ Generation failed")
                st.error("❌ Could not find a valid timetable. Try enabling permissive mode or check your data.")
                return
            
            progress_bar.progress(70)
            status_text.text("📊 Formatting results...")
            
            # Step 3: Format for display
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
            st.session_state.timetable_df = timetable_df
            st.session_state.generation_time = generation_time
            st.session_state.generation_stats = {
                'total_assignments': len(result['solution']),
                'variables': result['total_variables'],
                'completion_rate': (len(result['solution']) / result['total_variables'] * 100) if result['total_variables'] > 0 else 0,
                'generation_time': generation_time
            }
            
            # Show success metrics
            st.success(f"✅ Timetable generated successfully in {generation_time:.2f} seconds!")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Classes", len(result['solution']))
            with col2:
                st.metric("Completion", f"{st.session_state.generation_stats['completion_rate']:.1f}%")
            with col3:
                st.metric("Time Taken", f"{generation_time:.2f}s")
            with col4:
                st.metric("Classes Scheduled", len(timetable_df))
            
            st.info("📅 Go to 'View Timetable' to see your generated schedule!")
            
        except Exception as e:
            progress_bar.progress(100)
            status_text.text("❌ Error occurred")
            st.error(f"❌ Error during generation: {str(e)}")
            import traceback
            with st.expander("🔍 Error Details"):
                st.code(traceback.format_exc())

def show_timetable_view():
    st.header("📅 View Generated Timetable")
    
    if st.session_state.timetable_df is None or st.session_state.timetable_df.empty:
        st.warning("⚠️ No timetable generated yet. Please go to 'Data Upload & Generate' first.")
        return
    
    df = st.session_state.timetable_df
    
    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        years = ["All"] + sorted([str(y) for y in df['CourseYear'].unique()])
        selected_year = st.selectbox("Year", years)
    
    with col2:
        days = ["All"] + sorted(df['Day'].unique())
        selected_day = st.selectbox("Day", days)
    
    with col3:
        sessions = ["All"] + sorted(df['SessionType'].unique())
        selected_session = st.selectbox("Session Type", sessions)
    
    with col4:
        rooms = ["All"] + sorted(df['Room'].unique())
        selected_room = st.selectbox("Room", rooms)
    
    # Apply filters
    filtered_df = df.copy()
    if selected_year != "All":
        filtered_df = filtered_df[filtered_df['CourseYear'] == int(selected_year)]
    if selected_day != "All":
        filtered_df = filtered_df[filtered_df['Day'] == selected_day]
    if selected_session != "All":
        filtered_df = filtered_df[filtered_df['SessionType'] == selected_session]
    if selected_room != "All":
        filtered_df = filtered_df[filtered_df['Room'] == selected_room]
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Full Schedule",
        "📅 By Day",
        "🏫 By Room", 
        "👨‍🏫 By Instructor",
        "🎓 By Year"
    ])
    
    with tab1:
        st.subheader("Complete Timetable")
        st.dataframe(
            filtered_df[['CourseID', 'CourseName', 'SectionID', 'SessionType', 
                        'Day', 'StartTime', 'EndTime', 'Room', 'Instructor']],
            use_container_width=True,
            height=500
        )
        st.info(f"Showing {len(filtered_df)} of {len(df)} classes")
    
    with tab2:
        st.subheader("Schedule by Day")
        day_select = st.selectbox("Select Day:", sorted(df['Day'].unique()), key="day_view")
        day_df = df[df['Day'] == day_select].sort_values('StartTime')
        st.dataframe(
            day_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                   'StartTime', 'EndTime', 'Room', 'Instructor']],
            use_container_width=True,
            height=500
        )
    
    with tab3:
        st.subheader("Schedule by Room")
        room_select = st.selectbox("Select Room:", sorted(df['Room'].unique()), key="room_view")
        room_df = df[df['Room'] == room_select].sort_values(['Day', 'StartTime'])
        st.dataframe(
            room_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                    'Day', 'StartTime', 'EndTime', 'Instructor']],
            use_container_width=True,
            height=500
        )
    
    with tab4:
        st.subheader("Schedule by Instructor")
        instructor_select = st.selectbox("Select Instructor:", sorted(df['Instructor'].unique()), key="instructor_view")
        instructor_df = df[df['Instructor'] == instructor_select].sort_values(['Day', 'StartTime'])
        st.dataframe(
            instructor_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                          'Day', 'StartTime', 'EndTime', 'Room']],
            use_container_width=True,
            height=500
        )
    
    with tab5:
        st.subheader("Schedule by Year")
        year_select = st.selectbox("Select Year:", sorted(df['CourseYear'].unique()), key="year_view")
        year_df = df[df['CourseYear'] == year_select].sort_values(['Day', 'StartTime'])
        st.dataframe(
            year_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                    'Day', 'StartTime', 'EndTime', 'Room', 'Instructor']],
            use_container_width=True,
            height=500
        )
    
    # Export functionality
    st.subheader("💾 Export Timetable")
    csv_data = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Complete Timetable (CSV)",
        data=csv_data,
        file_name=f"timetable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

def show_statistics():
    st.header("📈 Timetable Statistics")
    
    if st.session_state.timetable_df is None or st.session_state.timetable_df.empty:
        st.warning("⚠️ No timetable generated yet. Please generate a timetable first.")
        return
    
    df = st.session_state.timetable_df
    stats = st.session_state.generation_stats
    
    # Generation Stats
    st.subheader("⚡ Generation Performance")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Classes", stats['total_assignments'])
    with col2:
        st.metric("Completion Rate", f"{stats['completion_rate']:.1f}%")
    with col3:
        st.metric("Generation Time", f"{stats['generation_time']:.2f}s")
    with col4:
        st.metric("Classes/Second", f"{stats['total_assignments']/stats['generation_time']:.1f}")
    
    # Session Type Distribution
    st.subheader("📊 Session Type Distribution")
    session_counts = df['SessionType'].value_counts()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.bar_chart(session_counts)
    
    with col2:
        for session_type, count in session_counts.items():
            st.metric(session_type, count)
    
    # Daily Distribution
    st.subheader("📅 Classes per Day")
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    day_counts = df['Day'].value_counts().reindex(day_order, fill_value=0)
    st.bar_chart(day_counts)
    
    # Room Utilization
    st.subheader("🏫 Room Utilization (Top 15)")
    room_counts = df['Room'].value_counts().head(15)
    st.bar_chart(room_counts)
    
    # Instructor Workload
    st.subheader("👨‍🏫 Instructor Workload (Top 15)")
    instructor_counts = df['Instructor'].value_counts().head(15)
    st.bar_chart(instructor_counts)
    
    # Year Distribution
    st.subheader("🎓 Classes by Year")
    year_counts = df['CourseYear'].value_counts().sort_index()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.bar_chart(year_counts)
    
    with col2:
        for year, count in year_counts.items():
            st.metric(f"Year {year}", count)

if __name__ == "__main__":
    main()