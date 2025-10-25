# [file name]: utils.py (UPDATED FOR NEW VARIABLE FORMAT)
import pandas as pd
from typing import Dict, List, Tuple
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def format_timetable_for_display(solution: Dict, data_loader, csp=None) -> pd.DataFrame:
    """
    Convert NEW CSP solution to DataFrame for display
    Handles friend's "Course::G0::Lecture" variable format
    """
    rows = []
    
    for variable_id, assignment in solution.items():
        # Parse NEW variable format: "COURSE::G0::SessionType"
        parts = variable_id.split('::')
        if len(parts) != 3:
            continue
            
        course_id = parts[0]
        group_info = parts[1]  # e.g., "G0"
        session_type = parts[2]  # e.g., "Lecture", "Lab", "TUT"
        
        # Get timeslot info
        timeslot = assignment['timeslot']
        day, start_time, end_time = timeslot
        
        # Get course info
        course_info = data_loader.courses_df[
            data_loader.courses_df['CourseID'] == course_id
        ]
        course_name = course_info['CourseName'].iloc[0] if not course_info.empty else course_id
        
        # Get instructor info
        instructor_id = assignment['instructor']
        instructor_info = data_loader.instructors_df[
            data_loader.instructors_df['InstructorID'] == instructor_id
        ]
        instructor_name = instructor_info['Name'].iloc[0] if not instructor_info.empty else instructor_id
        
        # Get room info
        room_id = assignment['room']
        room_info = data_loader.rooms_df[
            data_loader.rooms_df['RoomID'] == room_id
        ]
        room_type = room_info['Type'].iloc[0] if not room_info.empty else 'Unknown'
        room_capacity = room_info['Capacity'].iloc[0] if not room_info.empty else 0
        
        # Get sections from CSP meta data if available
        sections = []
        if csp and variable_id in csp.meta:
            sections = csp.meta[variable_id].get('sections', [])
        else:
            # Fallback: try to extract from group info
            try:
                group_idx = int(group_info[1:])  # Extract number from "G0"
                if csp and course_id in csp.course_to_section_groups:
                    session_groups = csp.course_to_section_groups[course_id].get(session_type, [])
                    if group_idx < len(session_groups):
                        sections = session_groups[group_idx]
            except (ValueError, IndexError):
                sections = [f"Group{group_info}"]
        
        # Create a row for EACH section in the group
        for section_id in sections:
            rows.append({
                'CourseID': course_id,
                'CourseName': course_name,
                'SectionID': section_id,
                'Session': session_type,
                'Day': day,
                'StartTime': start_time,
                'EndTime': end_time,
                'Room': room_id,
                'RoomType': room_type,
                'RoomCapacity': room_capacity,
                'Instructor': instructor_name,
                'InstructorID': instructor_id,
                'VariableID': variable_id
            })
    
    # Create DataFrame and sort
    df = pd.DataFrame(rows)
    if not df.empty:
        # Sort by day and time
        day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        df['DayOrder'] = df['Day'].map(lambda x: day_order.index(x) if x in day_order else 999)
        
        def time_to_minutes(time_str):
            """Convert time string like '9:00 AM' to minutes since midnight for sorting"""
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
        
        df['TimeOrder'] = df['StartTime'].apply(time_to_minutes)
        df = df.sort_values(['DayOrder', 'TimeOrder', 'CourseID']).drop(['DayOrder', 'TimeOrder'], axis=1)
    
    return df

def calculate_solution_metrics(solution: Dict, data_loader, csp=None) -> Dict:
    """
    Calculate comprehensive metrics for the solution
    """
    if not solution:
        return {}
    
    timetable_df = format_timetable_for_display(solution, data_loader, csp)
    
    # Basic metrics
    metrics = {
        'total_assignments': len(solution),
        'lectures_count': len(timetable_df[timetable_df['Session'] == 'Lecture']),
        'labs_count': len(timetable_df[timetable_df['Session'] == 'Lab']),
        'tutorials_count': len(timetable_df[timetable_df['Session'] == 'TUT']),
        'days_used': len(timetable_df['Day'].unique()),
        'rooms_used': len(timetable_df['Room'].unique()),
        'instructors_used': len(timetable_df['InstructorID'].unique()),
        'courses_scheduled': len(timetable_df['CourseID'].unique()),
    }
    
    # Calculate distribution metrics
    day_distribution = timetable_df['Day'].value_counts().to_dict()
    metrics['day_distribution'] = day_distribution
    
    # Calculate instructor workload
    instructor_workload = timetable_df['InstructorID'].value_counts().to_dict()
    metrics['instructor_workload'] = instructor_workload
    
    # Calculate room utilization
    room_utilization = {}
    for room in timetable_df['Room'].unique():
        room_classes = timetable_df[timetable_df['Room'] == room]
        room_utilization[room] = {
            'classes_count': len(room_classes),
            'utilization_percentage': (len(room_classes) / len(timetable_df) * 100) if len(timetable_df) > 0 else 0
        }
    metrics['room_utilization'] = room_utilization
    
    return metrics

def create_timetable_visualization(timetable_df: pd.DataFrame):
    """
    Create interactive timetable visualization
    """
    if timetable_df.empty:
        return None
    
    # Create a structured timetable grid
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    time_slots = sorted(timetable_df['StartTime'].unique())
    
    # Create empty grid
    grid_data = []
    
    for day in days:
        for time_slot in time_slots:
            day_classes = timetable_df[
                (timetable_df['Day'] == day) & 
                (timetable_df['StartTime'] == time_slot)
            ]
            
            if not day_classes.empty:
                # Combine multiple classes in same timeslot
                class_info = []
                for _, class_row in day_classes.iterrows():
                    info = f"{class_row['CourseID']} - {class_row['Session']}<br>"
                    info += f"Room: {class_row['Room']}<br>"
                    info += f"Instructor: {class_row['Instructor']}"
                    class_info.append(info)
                
                grid_data.append({
                    'Day': day,
                    'TimeSlot': time_slot,
                    'Classes': '<br>---<br>'.join(class_info),
                    'ClassCount': len(day_classes)
                })
            else:
                grid_data.append({
                    'Day': day,
                    'TimeSlot': time_slot,
                    'Classes': 'Free',
                    'ClassCount': 0
                })
    
    grid_df = pd.DataFrame(grid_data)
    
    # Create heatmap-like visualization
    if not grid_df.empty:
        fig = px.density_heatmap(
            grid_df, 
            x='Day', 
            y='TimeSlot',
            z='ClassCount',
            color_continuous_scale='Blues',
            title='Timetable Density Heatmap'
        )
        return fig
    return None

def create_instructor_workload_chart(metrics: Dict):
    """
    Create chart showing instructor workload distribution
    """
    if 'instructor_workload' not in metrics:
        return None
    
    workload_data = metrics['instructor_workload']
    
    instructor_names = list(workload_data.keys())
    workload_counts = list(workload_data.values())
    
    fig = px.bar(
        x=instructor_names,
        y=workload_counts,
        title='Instructor Workload Distribution',
        labels={'x': 'Instructor ID', 'y': 'Number of Classes'}
    )
    
    fig.update_layout(xaxis_tickangle=-45)
    
    return fig

def export_timetable_to_csv(timetable_df: pd.DataFrame, filename: str = "csit_timetable.csv"):
    """
    Export timetable to CSV
    """
    # Reorganize data for better CSV export
    export_df = timetable_df[[
        'CourseID', 'CourseName', 'SectionID', 'Session',
        'Day', 'StartTime', 'EndTime', 'Room', 'Instructor', 'RoomType'
    ]].copy()
    
    export_df = export_df.sort_values(['Day', 'StartTime', 'Room'])
    
    return export_df.to_csv(index=False)

def validate_solution_completeness(solution: Dict, csp) -> Dict:
    """
    Validate if solution is complete and identify missing assignments
    """
    validation_result = {
        'is_complete': False,
        'total_variables': len(csp.variables),
        'assigned_variables': len(solution) if solution else 0,
        'missing_assignments': [],
        'completion_percentage': 0
    }
    
    if solution:
        validation_result['is_complete'] = len(solution) == len(csp.variables)
        validation_result['completion_percentage'] = (len(solution) / len(csp.variables)) * 100
        
        # Find missing assignments
        for variable in csp.variables:
            if variable.variable_id not in solution:
                validation_result['missing_assignments'].append({
                    'variable_id': variable.variable_id,
                    'course_id': variable.course_id,
                    'activity_type': variable.activity_type,
                    'sections': variable.sections
                })
    
    return validation_result

def generate_solution_report(solution: Dict, data_loader, solver_metrics: Dict, csp=None) -> str:
    """
    Generate a comprehensive text report of the solution
    """
    if not solution:
        return "No solution generated."
    
    timetable_df = format_timetable_for_display(solution, data_loader, csp)
    metrics = calculate_solution_metrics(solution, data_loader, csp)
    
    report = []
    report.append("🎓 CSIT TIMETABLE GENERATION REPORT")
    report.append("=" * 50)
    report.append(f"📊 Solution Overview:")
    report.append(f"   • Total Assignments: {metrics['total_assignments']}")
    report.append(f"   • Lectures: {metrics['lectures_count']}")
    report.append(f"   • Labs: {metrics['labs_count']}")
    report.append(f"   • Tutorials: {metrics['tutorials_count']}")
    report.append(f"   • Days Used: {metrics['days_used']}")
    report.append(f"   • Rooms Used: {metrics['rooms_used']}")
    report.append(f"   • Instructors Used: {metrics['instructors_used']}")
    report.append(f"   • Courses Scheduled: {metrics['courses_scheduled']}")
    report.append("")
    
    report.append("🕒 Day Distribution:")
    for day, count in metrics['day_distribution'].items():
        report.append(f"   • {day}: {count} classes")
    report.append("")
    
    report.append("⚙️ Solver Performance:")
    report.append(f"   • Backtracks: {solver_metrics.get('backtrack_count', 'N/A')}")
    report.append(f"   • Constraint Checks: {solver_metrics.get('constraint_checks', 'N/A')}")
    report.append(f"   • Search Time: {solver_metrics.get('search_time', 'N/A'):.2f}s")
    report.append(f"   • Completion: {solver_metrics.get('completion_percentage', 'N/A'):.1f}%")
    
    return "\n".join(report)