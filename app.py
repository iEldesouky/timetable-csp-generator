# app.py - UPDATED VERSION WITH INSTRUCTOR VIEW RESTORED
import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sys
import os
import plotly.graph_objects as go
import plotly.express as px

# Set page config MUST be the first Streamlit command
st.set_page_config(
    page_title="CSIT Timetable Generator", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add the current directory to Python path
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

def create_weekly_grid(timetable_df, selected_section=None):
    """Create a beautiful weekly grid timetable"""
    if timetable_df is None or timetable_df.empty:
        return None
    
    # Filter by section if provided
    df = timetable_df.copy()
    if selected_section and selected_section != "All":
        df = df[df['SectionID'] == selected_section]
    
    # Define day and time order
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    time_slots = [
        ('9:00 AM', '10:30 AM'),
        ('10:45 AM', '12:15 PM'), 
        ('12:30 PM', '2:00 PM'),
        ('2:15 PM', '3:45 PM'),
    ]
    
    # Create empty grid
    grid_data = []
    for start_time, end_time in time_slots:
        row = {'Time': f"{start_time.split()[0]}-{end_time.split()[0]} {end_time.split()[1]}"}
        for day in day_order:
            day_classes = df[(df['Day'] == day) & 
                           (df['StartTime'] == start_time) & 
                           (df['EndTime'] == end_time)]
            
            if not day_classes.empty:
                class_info = []
                for _, class_row in day_classes.iterrows():
                    class_text = f"{class_row['CourseID']}\n{class_row['SessionType']}\n{class_row['Instructor'].split()[-1]}\n{class_row['Room']}"
                    class_info.append(class_text)
                row[day] = "<br>".join(class_info)
            else:
                row[day] = ""
        grid_data.append(row)
    
    return pd.DataFrame(grid_data)

def create_section_timetable(timetable_df, section_id):
    """Create a dedicated timetable view for a specific section"""
    if timetable_df is None or timetable_df.empty:
        return None
    
    section_df = timetable_df[timetable_df['SectionID'] == section_id].copy()
    if section_df.empty:
        return None
    
    # Sort by day and time
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    section_df['DayOrder'] = section_df['Day'].map(lambda x: day_order.index(x) if x in day_order else 999)
    
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
    
    section_df['TimeOrder'] = section_df['StartTime'].apply(time_to_minutes)
    section_df = section_df.sort_values(['DayOrder', 'TimeOrder']).drop(['DayOrder', 'TimeOrder'], axis=1)
    
    return section_df

def display_colorful_grid(grid_df):
    """Display the timetable as colorful grid"""
    if grid_df is None or grid_df.empty:
        st.warning("No data available for grid display")
        return
    
    styled_df = grid_df.set_index('Time')
    
    # Display with DARK MODE styling
    st.markdown("### 🗓️ Weekly Timetable Grid (Dark Mode)")
    
    # DARK MODE HTML table
    html_table = """
    <style>
    .timetable-grid {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        color: #e0e0e0;
    }
    .timetable-grid th, .timetable-grid td {
        border: 2px solid #555;
        padding: 12px;
        text-align: center;
        vertical-align: top;
    }
    .timetable-grid th {
        background-color: #2d4a2d;
        color: #e0e0e0;
        font-weight: bold;
    }
    .timetable-grid td {
        background-color: #1e1e1e;
        height: 120px;
    }
    .time-header {
        background-color: #1a3a5f !important;
        color: #e0e0e0;
        font-weight: bold;
    }
    .class-cell {
        background-color: #2a2a2a;
        border-radius: 5px;
        padding: 8px;
        margin: 2px;
        color: #e0e0e0;
    }
    .lecture { background-color: #1e3a5a; color: #bbdefb; }
    .lab { background-color: #3a2a4a; color: #e1bee7; }
    .tut { background-color: #2a3a2a; color: #c8e6c9; }
    </style>
    <table class='timetable-grid'>
    <tr>
        <th>Time</th>
        <th>Sunday</th>
        <th>Monday</th>
        <th>Tuesday</th>
        <th>Wednesday</th>
        <th>Thursday</th>
    </tr>
    """
    
    for _, row in grid_df.iterrows():
        html_table += f"<tr><td class='time-header'>{row['Time']}</td>"
        for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']:
            cell_content = row[day]
            if cell_content:
                # Determine session type for coloring
                session_type = "lecture"
                if "Lab" in cell_content:
                    session_type = "lab"
                elif "TUT" in cell_content:
                    session_type = "tut"
                
                html_table += f"<td><div class='class-cell {session_type}'>{cell_content.replace(chr(10), '<br>')}</div></td>"
            else:
                html_table += f"<td></td>"
        html_table += "</tr>"
    
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)

def main():
    st.title("🎓 CSIT Automated Timetable Generator")
    st.markdown("**Optimized CSP Algorithm • Fast Generation • Beautiful Grid Display**")
    
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
        "📅 Grid Timetable View",
        "🎓 Student Section View",
        "👨‍🏫 Instructor View",  # ADDED BACK
        "📈 Statistics"
    ])
    
    if page == "📊 Data Upload & Generate":
        show_upload_and_generate()
    elif page == "📅 Grid Timetable View":
        show_grid_timetable_view()
    elif page == "🎓 Student Section View":
        show_student_section_view()
    elif page == "👨‍🏫 Instructor View":  # ADDED BACK
        show_instructor_view()
    elif page == "📈 Statistics":
        show_statistics()

def show_upload_and_generate():
    st.header("📊 Upload Data & Generate Timetable")
    
    st.info("""
    **Optimized Features:**
    - 🚀 **Faster Generation** (Target: 10-30 seconds)
    - 🎨 **Beautiful Grid Display**
    - 👨‍🎓 **Student Section Views**
    - 👨‍🏫 **Instructor Views**  <!-- ADDED BACK -->
    - 📱 **Mobile-Friendly Design**
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
        timeout = st.slider("Search Timeout (seconds)", 10, 120, 30, 5)
        st.info(f"Target: 10-30 seconds (optimized algorithm)")
    with col2:
        enable_permissive = st.checkbox("Enable Permissive Mode (if strict fails)", value=False)
        enable_fast_mode = st.checkbox("🚀 Enable Fast Mode (Aggressive optimization)", value=True)
    
    # Generate button
    if st.button("🚀 Generate Timetable", type="primary", use_container_width=True):
        if not all([courses_file, instructors_file, rooms_file, timeslots_file, sections_file]):
            st.error("❌ Please upload all 5 CSV files before generating")
            return
        
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        time_tracker = st.empty()
        
        try:
            # Step 1: Load data
            status_text.text("📂 Loading CSV files...")
            progress_bar.progress(10)
            start_load = time.time()
            
            courses_df = pd.read_csv(courses_file)
            instructors_df = pd.read_csv(instructors_file)
            rooms_df = pd.read_csv(rooms_file)
            timeslots_df = pd.read_csv(timeslots_file)
            sections_df = pd.read_csv(sections_file)
            
            load_time = time.time() - start_load
            status_text.text(f"✅ Data loaded successfully ({load_time:.2f}s)")
            progress_bar.progress(25)
            
            # Show data summary
            with st.expander("📊 Data Summary", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Courses", len(courses_df))
                    st.metric("Instructors", len(instructors_df))
                with col2:
                    st.metric("Rooms", len(rooms_df))
                    st.metric("Timeslots", len(timeslots_df))
                with col3:
                    st.metric("Sections", len(sections_df))
                with col4:
                    st.metric("Data Load Time", f"{load_time:.2f}s")
            
            # Step 2: Generate timetable
            status_text.text("🔄 Running OPTIMIZED CSP solver...")
            progress_bar.progress(40)
            
            start_time = time.time()
            
            # Pass fast mode parameter to solver
            result = generate_timetable(
                courses_df=courses_df,
                instructors_df=instructors_df,
                rooms_df=rooms_df,
                timeslots_df=timeslots_df,
                sections_df=sections_df,
                force_permissive=enable_permissive,
                timeout=timeout,
                fast_mode=enable_fast_mode  # New parameter for optimizations
            )
            
            generation_time = time.time() - start_time
            
            if result is None:
                progress_bar.progress(100)
                status_text.text("❌ Generation failed")
                st.error("❌ Could not find a valid timetable. Try enabling permissive mode or check your data.")
                return
            
            progress_bar.progress(80)
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
                'generation_time': generation_time,
                'load_time': load_time
            }
            
            # Show success metrics
            st.success(f"✅ Timetable generated successfully in {generation_time:.2f} seconds!")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Classes", len(result['solution']))
            with col2:
                st.metric("Completion", f"{st.session_state.generation_stats['completion_rate']:.1f}%")
            with col3:
                st.metric("Generation Time", f"{generation_time:.2f}s")
                if generation_time <= 30:
                    st.success("🚀 Fast!")
                elif generation_time <= 60:
                    st.warning("⚡ Moderate")
                else:
                    st.error("🐢 Slow")
            with col4:
                st.metric("Classes Scheduled", len(timetable_df))
            
            st.info("📅 Go to 'Grid Timetable View' to see your beautiful schedule!")
            
        except Exception as e:
            progress_bar.progress(100)
            status_text.text("❌ Error occurred")
            st.error(f"❌ Error during generation: {str(e)}")
            import traceback
            with st.expander("🔍 Error Details"):
                st.code(traceback.format_exc())

def show_grid_timetable_view():
    st.header("📅 Weekly Timetable Grid View")
    
    if st.session_state.timetable_df is None or st.session_state.timetable_df.empty:
        st.warning("⚠️ No timetable generated yet. Please go to 'Data Upload & Generate' first.")
        return
    
    df = st.session_state.timetable_df
    
    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sections = ["All"] + sorted(df['SectionID'].unique().tolist())
        selected_section = st.selectbox("Section", sections)
    
    with col2:
        years = ["All"] + sorted([str(y) for y in df['CourseYear'].unique()])
        selected_year = st.selectbox("Year", years)
    
    with col3:
        sessions = ["All"] + sorted(df['SessionType'].unique())
        selected_session = st.selectbox("Session Type", sessions)
    
    with col4:
        days = ["All"] + sorted(df['Day'].unique())
        selected_day = st.selectbox("Day", days)
    
    # Apply filters
    filtered_df = df.copy()
    if selected_section != "All":
        filtered_df = filtered_df[filtered_df['SectionID'] == selected_section]
    if selected_year != "All":
        filtered_df = filtered_df[filtered_df['CourseYear'] == int(selected_year)]
    if selected_session != "All":
        filtered_df = filtered_df[filtered_df['SessionType'] == selected_session]
    if selected_day != "All":
        filtered_df = filtered_df[filtered_df['Day'] == selected_day]
    
    # Display options
    st.subheader("🎨 Display Options")
    display_mode = st.radio("View Mode", ["Colorful Grid", "Compact Table", "By Day", "By Room", "By Instructor"])  # ADDED INSTRUCTOR OPTION
    
    if display_mode == "Colorful Grid":
        # Create and display grid
        grid_df = create_weekly_grid(filtered_df, selected_section if selected_section != "All" else None)
        if grid_df is not None:
            display_colorful_grid(grid_df)
        else:
            st.warning("No data available for the selected filters")
    
    elif display_mode == "Compact Table":
        st.dataframe(
            filtered_df[['CourseID', 'CourseName', 'SectionID', 'SessionType', 
                        'Day', 'StartTime', 'EndTime', 'Room', 'Instructor']],
            use_container_width=True,
            height=400
        )
    
    elif display_mode == "By Day":
        day_select = st.selectbox("Select Day:", sorted(df['Day'].unique()), key="day_view")
        day_df = df[df['Day'] == day_select].sort_values('StartTime')
        st.dataframe(
            day_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                   'StartTime', 'EndTime', 'Room', 'Instructor']],
            use_container_width=True,
            height=400
        )
    
    elif display_mode == "By Room":
        room_select = st.selectbox("Select Room:", sorted(df['Room'].unique()), key="room_view")
        room_df = df[df['Room'] == room_select].sort_values(['Day', 'StartTime'])
        st.dataframe(
            room_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                    'Day', 'StartTime', 'EndTime', 'Instructor']],
            use_container_width=True,
            height=400
        )
    
    elif display_mode == "By Instructor":  # ADDED BACK
        instructor_select = st.selectbox("Select Instructor:", sorted(df['Instructor'].unique()), key="instructor_view")
        instructor_df = df[df['Instructor'] == instructor_select].sort_values(['Day', 'StartTime'])
        st.dataframe(
            instructor_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                          'Day', 'StartTime', 'EndTime', 'Room']],
            use_container_width=True,
            height=400
        )
    
    # Export functionality
    st.subheader("💾 Export Timetable")
    csv_data = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Timetable (CSV)",
        data=csv_data,
        file_name=f"timetable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

def show_student_section_view():
    st.header("🎓 Student Section Timetable")
    
    if st.session_state.timetable_df is None or st.session_state.timetable_df.empty:
        st.warning("⚠️ No timetable generated yet. Please generate a timetable first.")
        return
    
    df = st.session_state.timetable_df
    
    # Section selection
    st.subheader("Select Your Section")
    sections = sorted(df['SectionID'].unique().tolist())
    selected_section = st.selectbox("Section ID", sections)
    
    if selected_section:
        # Get section timetable
        section_df = create_section_timetable(df, selected_section)
        
        if section_df is not None and not section_df.empty:
            st.success(f"📚 Timetable for Section {selected_section}")
            
            # Display as beautiful cards for each day
            days = sorted(section_df['Day'].unique())
            
            for day in days:
                st.subheader(f"📅 {day}")
                day_classes = section_df[section_df['Day'] == day].sort_values('StartTime')
                
                for _, class_info in day_classes.iterrows():
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        
                        with col1:
                            st.write(f"**{class_info['CourseID']} - {class_info['CourseName']}**")
                            st.write(f"*{class_info['SessionType']}*")
                        
                        with col2:
                            st.write(f"🕒 {class_info['StartTime']} - {class_info['EndTime']}")
                        
                        with col3:
                            st.write(f"🏫 {class_info['Room']}")
                        
                        with col4:
                            st.write(f"👨‍🏫 {class_info['Instructor']}")
                        
                        st.divider()
            
            # Also show as grid
            st.subheader("📊 Weekly View")
            grid_df = create_weekly_grid(df, selected_section)
            if grid_df is not None:
                display_colorful_grid(grid_df)
        
        else:
            st.warning(f"No classes found for section {selected_section}")

def show_instructor_view():  # ADDED BACK - DEDICATED INSTRUCTOR PAGE
    st.header("👨‍🏫 Instructor Timetable View")
    
    if st.session_state.timetable_df is None or st.session_state.timetable_df.empty:
        st.warning("⚠️ No timetable generated yet. Please generate a timetable first.")
        return
    
    df = st.session_state.timetable_df
    
    # Instructor selection
    st.subheader("Select Instructor")
    instructors = sorted(df['Instructor'].unique().tolist())
    selected_instructor = st.selectbox("Instructor Name", instructors)
    
    if selected_instructor:
        # Get instructor timetable
        instructor_df = df[df['Instructor'] == selected_instructor].copy()
        
        if not instructor_df.empty:
            st.success(f"📅 Teaching Schedule for {selected_instructor}")
            
            # Sort by day and time
            day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
            instructor_df['DayOrder'] = instructor_df['Day'].map(lambda x: day_order.index(x) if x in day_order else 999)
            
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
            
            instructor_df['TimeOrder'] = instructor_df['StartTime'].apply(time_to_minutes)
            instructor_df = instructor_df.sort_values(['DayOrder', 'TimeOrder']).drop(['DayOrder', 'TimeOrder'], axis=1)
            
            # Display summary stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Classes", len(instructor_df))
            with col2:
                st.metric("Different Courses", instructor_df['CourseID'].nunique())
            with col3:
                st.metric("Different Sections", instructor_df['SectionID'].nunique())
            with col4:
                st.metric("Busiest Day", instructor_df['Day'].mode().iloc[0] if not instructor_df.empty else "N/A")
            
            # Display as beautiful cards for each day
            days = sorted(instructor_df['Day'].unique())
            
            for day in days:
                st.subheader(f"📅 {day}")
                day_classes = instructor_df[instructor_df['Day'] == day].sort_values('StartTime')
                
                for _, class_info in day_classes.iterrows():
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        
                        with col1:
                            st.write(f"**{class_info['CourseID']} - {class_info['CourseName']}**")
                            st.write(f"*{class_info['SessionType']}* • Section {class_info['SectionID']}")
                        
                        with col2:
                            st.write(f"🕒 {class_info['StartTime']} - {class_info['EndTime']}")
                        
                        with col3:
                            st.write(f"🏫 {class_info['Room']}")
                        
                        with col4:
                            # Color code by session type
                            session_type = class_info['SessionType']
                            if session_type == 'Lecture':
                                st.success("📚 Lecture")
                            elif session_type == 'Lab':
                                st.info("🔬 Lab")
                            else:
                                st.warning("💻 TUT")
                        
                        st.divider()
            
            # Also show as data table
            st.subheader("📋 Detailed Schedule Table")
            st.dataframe(
                instructor_df[['CourseID', 'CourseName', 'SectionID', 'SessionType',
                              'Day', 'StartTime', 'EndTime', 'Room']],
                use_container_width=True,
                height=400
            )
            
            # Export functionality for this instructor
            st.subheader("💾 Export Instructor Schedule")
            csv_data = instructor_df.to_csv(index=False)
            st.download_button(
                label=f"📥 Download {selected_instructor}'s Schedule (CSV)",
                data=csv_data,
                file_name=f"{selected_instructor.replace(' ', '_')}_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        else:
            st.warning(f"No classes found for instructor {selected_instructor}")

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
        gen_time = stats['generation_time']
        st.metric("Generation Time", f"{gen_time:.2f}s")
        if gen_time <= 30:
            st.success("🚀 Fast")
        elif gen_time <= 60:
            st.warning("⚡ Moderate")
        else:
            st.error("🐢 Needs optimization")
    with col4:
        st.metric("Classes/Second", f"{stats['total_assignments']/stats['generation_time']:.1f}")
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Session Type Distribution")
        session_counts = df['SessionType'].value_counts()
        fig = px.pie(values=session_counts.values, names=session_counts.index, 
                    title="Session Types")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📅 Classes per Day")
        day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
        day_counts = df['Day'].value_counts().reindex(day_order, fill_value=0)
        fig = px.bar(x=day_counts.index, y=day_counts.values, 
                    title="Classes per Day", color=day_counts.values,
                    color_continuous_scale='viridis')
        st.plotly_chart(fig, use_container_width=True)
    
    # Room and Instructor utilization
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏫 Room Utilization (Top 10)")
        room_counts = df['Room'].value_counts().head(10)
        fig = px.bar(x=room_counts.index, y=room_counts.values,
                    title="Most Used Rooms")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("👨‍🏫 Instructor Workload (Top 10)")
        instructor_counts = df['Instructor'].value_counts().head(10)
        fig = px.bar(x=instructor_counts.index, y=instructor_counts.values,
                    title="Busiest Instructors")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()