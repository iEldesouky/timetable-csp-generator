import pandas as pd
from typing import Dict, List

def format_timetable_for_display(solution: Dict, data_loader) -> pd.DataFrame:
    """
    Convert CSP solution to a nice DataFrame for display
    """
    rows = []
    
    for variable_id, assignment in solution.items():
        timeslot, room, instructor = assignment
        
        # Extract components
        day = timeslot.split()[0]
        time_range = ' '.join(timeslot.split()[1:])
        
        # Get course info
        course_id = variable_id.split('_')[0]
        course_info = data_loader.courses_df[
            data_loader.courses_df['CourseID'] == course_id
        ].iloc[0]
        
        # Get instructor info
        instructor_info = data_loader.instructors_df[
            data_loader.instructors_df['InstructorID'] == instructor
        ].iloc[0]
        
        rows.append({
            'Course Section': variable_id,
            'Course Name': course_info['CourseName'],
            'Course Type': course_info['Type'],
            'Day': day,
            'Time': time_range,
            'Room': room,
            'Instructor': instructor_info['Name'],
            'Instructor ID': instructor
        })
    
    return pd.DataFrame(rows)

def calculate_solution_metrics(solution: Dict, data_loader) -> Dict:
    """
    Calculate various metrics for the solution
    """
    if not solution:
        return {}
    
    timetable_df = format_timetable_for_display(solution, data_loader)
    
    metrics = {
        'total_classes': len(solution),
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
    
    return metrics