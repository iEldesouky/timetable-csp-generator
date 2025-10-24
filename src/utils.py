# utils.py - CORRECTED VERSION

import pandas as pd
from typing import Dict, List, Tuple
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def format_timetable_for_display(solution: Dict, data_loader) -> pd.DataFrame:
    """
    Convert CSP solution to a comprehensive DataFrame for display
    """
    rows = []
    
    for variable_id, assignment in solution.items():
        timeslot_id, room_id, instructor_id = assignment
        
        # Parse variable ID
        parts = variable_id.split('_')
        course_id = parts[0]
        activity_type = parts[1]  # LEC, LAB, TUT
        year = parts[2]
        group = parts[3]
        
        # Get additional info from data
        course_info = data_loader.courses_df[
            data_loader.courses_df['course_id'] == course_id
        ].iloc[0]
        
        instructor_info = data_loader.instructors_df[
            data_loader.instructors_df['instructor_id'] == instructor_id
        ].iloc[0]
        
        room_info = data_loader.rooms_df[
            data_loader.rooms_df['room_id'] == room_id
        ].iloc[0]
        
        timeslot_info = data_loader.timeslots_df[
            data_loader.timeslots_df['time_slot_id'] == timeslot_id
        ].iloc[0]
        
        # Map activity types
        activity_map = {
            'LEC': 'Lecture',
            'LAB': 'Lab', 
            'TUT': 'Tutorial'
        }
        
        rows.append({
            'Variable ID': variable_id,
            'Course ID': course_id,
            'Course Name': course_info['course_name'],
            'Activity Type': activity_map.get(activity_type, activity_type),
            'Year': year,
            'Group': group,
            'Day': timeslot_info['day'],
            'Start Time': timeslot_info['start_time'],
            'End Time': timeslot_info['end_time'],
            'TimeSlot': timeslot_id,
            'Room': room_id,
            'Room Type': room_info['type'],
            'Room Capacity': room_info['capacity'],
            'Instructor': instructor_info['name'],
            'Instructor ID': instructor_id,
            'Instructor Role': instructor_info['role']
        })
    
    return pd.DataFrame(rows)

def calculate_solution_metrics(solution: Dict, data_loader) -> Dict:
    """
    Calculate comprehensive metrics for the solution
    """
    if not solution:
        return {}
    
    timetable_df = format_timetable_for_display(solution, data_loader)
    
    # Basic metrics
    metrics = {
        'total_classes': len(solution),
        'lectures_count': len(timetable_df[timetable_df['Activity Type'] == 'Lecture']),
        'labs_count': len(timetable_df[timetable_df['Activity Type'] == 'Lab']),
        'tutorials_count': len(timetable_df[timetable_df['Activity Type'] == 'Tutorial']),
        'days_used': len(timetable_df['Day'].unique()),
        'rooms_used': len(timetable_df['Room'].unique()),
        'instructors_used': len(timetable_df['Instructor ID'].unique()),
    }
    
    # Calculate distribution metrics
    day_distribution = timetable_df['Day'].value_counts().to_dict()
    metrics['day_distribution'] = day_distribution
    
    # Calculate instructor workload
    instructor_workload = timetable_df['Instructor ID'].value_counts().to_dict()
    metrics['instructor_workload'] = instructor_workload
    
    # Calculate room utilization
    room_utilization = {}
    for room in timetable_df['Room'].unique():
        room_capacity = data_loader.get_room_capacity(room)
        room_classes = timetable_df[timetable_df['Room'] == room]
        # For simplicity, assume average utilization
        avg_utilization = len(room_classes) / len(data_loader.timeslots_df) if len(data_loader.timeslots_df) > 0 else 0
        room_utilization[room] = {
            'capacity': room_capacity,
            'classes_count': len(room_classes),
            'avg_utilization': avg_utilization
        }
    metrics['room_utilization'] = room_utilization
    
    return metrics

def create_timetable_visualization(timetable_df: pd.DataFrame):
    """
    Create interactive timetable visualization
    """
    # Create a structured timetable grid
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    time_slots = sorted(timetable_df['TimeSlot'].unique())
    
    # Create empty grid
    grid_data = []
    
    for day in days:
        for time_slot in time_slots:
            day_classes = timetable_df[
                (timetable_df['Day'] == day) & 
                (timetable_df['TimeSlot'] == time_slot)
            ]
            
            if not day_classes.empty:
                # Combine multiple classes in same timeslot
                class_info = []
                for _, class_row in day_classes.iterrows():
                    info = f"{class_row['Course ID']} - {class_row['Activity Type']}<br>"
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
        'Course ID', 'Course Name', 'Activity Type', 'Year', 'Group',
        'Day', 'Start Time', 'End Time', 'Room', 'Instructor', 'Room Type'
    ]].copy()
    
    export_df = export_df.sort_values(['Day', 'Start Time', 'Room'])
    
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
                    'year': variable.year,
                    'group': variable.group_number
                })
    
    return validation_result

def generate_solution_report(solution: Dict, data_loader, solver_metrics: Dict) -> str:
    """
    Generate a comprehensive text report of the solution
    """
    if not solution:
        return "No solution generated."
    
    timetable_df = format_timetable_for_display(solution, data_loader)
    metrics = calculate_solution_metrics(solution, data_loader)
    
    report = []
    report.append("🎓 CSIT TIMETABLE GENERATION REPORT")
    report.append("=" * 50)
    report.append(f"📊 Solution Overview:")
    report.append(f"   • Total Classes Scheduled: {metrics['total_classes']}")
    report.append(f"   • Lectures: {metrics['lectures_count']}")
    report.append(f"   • Labs: {metrics['labs_count']}")
    report.append(f"   • Tutorials: {metrics['tutorials_count']}")
    report.append(f"   • Days Used: {metrics['days_used']}")
    report.append(f"   • Rooms Used: {metrics['rooms_used']}")
    report.append(f"   • Instructors Used: {metrics['instructors_used']}")
    report.append("")
    
    report.append("🕒 Day Distribution:")
    for day, count in metrics['day_distribution'].items():
        report.append(f"   • {day}: {count} classes")
    report.append("")
    
    report.append("⚙️ Solver Performance:")
    report.append(f"   • Backtracks: {solver_metrics.get('backtrack_count', 'N/A')}")
    report.append(f"   • Constraint Checks: {solver_metrics.get('constraint_checks', 'N/A')}")
    report.append(f"   • Solution Quality Score: {solver_metrics.get('solution_quality', 'N/A')}")
    
    return "\n".join(report)