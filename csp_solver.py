# csp_solver.py - OPTIMIZED VERSION
"""
OPTIMIZED CSP-based Timetable Generator
With performance improvements and faster solving
"""

import pandas as pd
import random
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set
import time

def parse_qualified_courses(val):
    """Parse instructor's qualified courses from CSV"""
    if pd.isna(val):
        return []
    if isinstance(val, str):
        return [s.strip() for s in val.split(',') if s.strip()]
    if isinstance(val, (list, tuple)):
        return list(val)
    return []

def can_assign_course_to_section(course_id: str, section_id: str, course_year: int, is_shared: bool = False) -> bool:
    """Optimized section assignment check"""
    if not section_id or '/' not in str(section_id):
        return True
    
    parts = str(section_id).split('/')
    if len(parts) < 2:
        return True
    
    try:
        section_year = int(parts[0].strip())
    except ValueError:
        return True
    
    # Check if course year matches section year
    if course_year != section_year:
        return False
    
    # For years 1-2, only year matching is required
    if course_year in [1, 2]:
        return True
    
    # For year 3 shared courses
    if course_year == 3 and is_shared:
        section_dept = parts[1].strip().upper() if len(parts) > 1 else ""
        return section_dept in ['AID', 'BIF', 'CSC', 'CNC']
    
    # For years 3-4, check department matching
    if course_year in [3, 4]:
        course_dept = course_id[:3].upper() if len(course_id) >= 3 else ""
        section_dept = parts[1].strip().upper() if len(parts) > 1 else ""
        return course_dept == section_dept
    
    return True

def create_section_groups(sections: List[str], session_type: str = 'Lecture') -> List[List[str]]:
    """Optimized section grouping"""
    if session_type == 'TUT':
        return [[s] for s in sections]  # Individual groups
    elif session_type == 'Lab':
        # Pair sections
        return [sections[i:i+2] for i in range(0, len(sections), 2)]
    else:
        # Lecture: 3-4 per group
        group_size = 3 if len(sections) % 3 == 0 else 4
        return [sections[i:i+group_size] for i in range(0, len(sections), group_size)]

def build_domains(courses_df, instructors_df, rooms_df, timeslots_df, sections_df, force_permissive=False, fast_mode=True):
    """
    OPTIMIZED domain building with performance improvements
    """
    
    # Cache instructor qualifications
    instructors_df = instructors_df.copy()
    instructors_df['_quals'] = instructors_df['QualifiedCourses'].apply(parse_qualified_courses)
    instructor_dict = instructors_df.to_dict('records')
    
    # Precompute course properties
    course_types = dict(zip(courses_df['CourseID'], courses_df['Type']))
    course_years = dict(zip(courses_df['CourseID'], courses_df['Year']))
    course_shared = dict(zip(courses_df['CourseID'], courses_df.get('Shared', pd.Series())))
    
    # Build course to section groups mapping
    course_to_section_groups = defaultdict(dict)
    
    # Pre-filter sections by year for faster matching
    sections_by_year = defaultdict(list)
    for _, sec in sections_df.iterrows():
        section_id = str(sec['SectionID'])
        if '/' in section_id:
            try:
                year = int(section_id.split('/')[0])
                sections_by_year[year].append(section_id)
            except ValueError:
                pass
    
    for _, course in courses_df.iterrows():
        course_id = course['CourseID']
        course_year = course_years.get(course_id)
        
        if course_year is None:
            continue
        
        is_shared = False
        if course_year == 3 and 'Shared' in course:
            shared_val = str(course.get('Shared', '')).strip().lower()
            is_shared = shared_val == 'yes'
        
        # Use pre-filtered sections by year
        candidate_sections = sections_by_year.get(course_year, [])
        matching_sections = []
        
        for section_id in candidate_sections:
            if can_assign_course_to_section(course_id, section_id, course_year, is_shared):
                matching_sections.append(section_id)
        
        # Create groups
        if matching_sections:
            ctype = course_types.get(course_id, 'Lecture')
            ctype_lower = ctype.lower() if isinstance(ctype, str) else 'lecture'
            
            if 'lecture' in ctype_lower:
                course_to_section_groups[course_id]['Lecture'] = create_section_groups(matching_sections, 'Lecture')
            if 'lab' in ctype_lower:
                course_to_section_groups[course_id]['Lab'] = create_section_groups(matching_sections, 'Lab')
            if 'tut' in ctype_lower:
                course_to_section_groups[course_id]['TUT'] = create_section_groups(matching_sections, 'TUT')
            
            if not course_to_section_groups[course_id]:
                course_to_section_groups[course_id]['Lecture'] = create_section_groups(matching_sections, 'Lecture')
    
    # Optimized timeslot processing
    timeslots_45 = []
    timeslots_90 = []
    
    for _, r in timeslots_df.iterrows():
        slot = (r['Day'], r['StartTime'], r['EndTime'])
        
        if 'Duration' in timeslots_df.columns:
            duration = r.get('Duration', 90)
            if duration == 45:
                timeslots_45.append(slot)
            else:
                timeslots_90.append(slot)
        else:
            timeslots_90.append(slot)
    
    rooms = list(rooms_df.to_dict('records'))
    
    # Create variables and domains
    variables = []
    domains = {}
    meta = {}
    
    # Pre-compute valid instructors and rooms by type
    valid_instructors_by_role = {
        'lecture': [i for i in instructor_dict if 'professor' in str(i.get('Role', '')).lower() and 'assistant' not in str(i.get('Role', '')).lower()],
        'lab_tut': [i for i in instructor_dict if 'assistant' in str(i.get('Role', '')).lower()]
    }
    
    valid_rooms_by_type = {
        'lecture': [r for r in rooms if not str(r.get('Type', '')).lower().startswith(('lab', 'tut'))],
        'lab': [r for r in rooms if str(r.get('Type', '')).lower().startswith('lab')],
        'tut': [r for r in rooms if str(r.get('Type', '')).lower() == 'tut']
    }
    
    for _, course in courses_df.iterrows():
        course_id = course['CourseID']
        
        if course_id not in course_to_section_groups:
            continue
        
        ctype = course_types.get(course_id, 'Lecture')
        
        for session_type, section_groups in course_to_section_groups[course_id].items():
            for group_idx, section_group in enumerate(section_groups):
                var = f"{course_id}::G{group_idx}::{session_type}"
                variables.append(var)
                
                # FAST MODE: Reduced domain generation
                if fast_mode:
                    vals = generate_domain_fast(
                        course_id, session_type, ctype,
                        valid_instructors_by_role, valid_rooms_by_type,
                        timeslots_45, timeslots_90, force_permissive
                    )
                else:
                    vals = generate_domain_comprehensive(
                        course_id, session_type, ctype, instructor_dict, rooms,
                        timeslots_45, timeslots_90, force_permissive
                    )
                
                domains[var] = vals
                meta[var] = {
                    'course': course_id,
                    'group_index': group_idx,
                    'sections': section_group,
                    'type': ctype
                }
    
    print(f'[CSP OPTIMIZED] Created {len(variables)} variables')
    return variables, domains, meta, course_to_section_groups

def generate_domain_fast(course_id, session_type, course_type, valid_instructors_by_role, valid_rooms_by_type, 
                        timeslots_45, timeslots_90, force_permissive):
    """Fast domain generation with pre-filtering"""
    domain_vals = []
    
    # Select appropriate timeslots
    session_lower = session_type.lower()
    if session_lower == 'tut':
        valid_timeslots = timeslots_45 if timeslots_45 else timeslots_90
    else:
        valid_timeslots = timeslots_90
    
    # Select appropriate instructors
    if session_lower in ['lab', 'tut']:
        valid_instructors = valid_instructors_by_role['lab_tut']
    else:
        valid_instructors = valid_instructors_by_role['lecture']
    
    # Select appropriate rooms
    if session_lower == 'lab':
        valid_rooms = valid_rooms_by_type['lab']
    elif session_lower == 'tut':
        valid_rooms = valid_rooms_by_type['tut']
    else:
        valid_rooms = valid_rooms_by_type['lecture']
    
    # Limit combinations for performance
    max_instructors = min(5, len(valid_instructors))
    max_rooms = min(5, len(valid_rooms))
    max_timeslots = min(10, len(valid_timeslots))
    
    sampled_instructors = random.sample(valid_instructors, max_instructors) if valid_instructors else []
    sampled_rooms = random.sample(valid_rooms, max_rooms) if valid_rooms else []
    sampled_timeslots = random.sample(valid_timeslots, max_timeslots) if valid_timeslots else []
    
    for t in sampled_timeslots:
        for instr in sampled_instructors:
            instr_id = instr['InstructorID'] if 'InstructorID' in instr else instr.get('Name')
            for room in sampled_rooms:
                domain_vals.append({
                    'timeslot': t,
                    'room': room['RoomID'],
                    'instructor': instr_id
                })
    
    return domain_vals

def generate_domain_comprehensive(course_id, session_type, course_type, instructors, rooms, 
                                timeslots_45, timeslots_90, force_permissive):
    """Comprehensive domain generation (fallback)"""
    domain_vals = []
    
    # Select timeslots based on session type
    if session_type.lower() == 'tut':
        valid_timeslots = timeslots_45 if timeslots_45 else timeslots_90
    else:
        valid_timeslots = timeslots_90
    
    for t in valid_timeslots:
        day = t[0]
        for instr in instructors:
            # Check instructor qualifications and role
            quals = instr.get('_quals', [])
            if not force_permissive and quals and course_id not in quals:
                continue
            
            # Role-based assignment
            instr_role = str(instr.get('Role', '')).lower()
            is_lab_or_tut = session_type.lower() in ['lab', 'tut']
            
            if 'assistant' in instr_role and not is_lab_or_tut:
                continue
            elif 'professor' in instr_role and 'assistant' not in instr_role and is_lab_or_tut:
                continue
            
            # Check availability
            pref_slots = instr.get('PreferredSlots', '')
            if pref_slots and isinstance(pref_slots, str):
                if 'Not on' in pref_slots and day in pref_slots:
                    if not force_permissive:
                        continue
            
            instr_id = instr['InstructorID'] if 'InstructorID' in instr else instr.get('Name')
            
            for room in rooms:
                # Room type matching
                rtype = room.get('Type', 'Lecture').lower()
                session_lower = session_type.lower()
                
                if session_lower == 'lab' and not rtype.startswith('lab'):
                    if not force_permissive:
                        continue
                elif session_lower == 'lecture' and (rtype.startswith('lab') or rtype == 'tut'):
                    if not force_permissive:
                        continue
                elif session_lower == 'tut' and rtype != 'tut':
                    if not force_permissive:
                        continue
                
                domain_vals.append({
                    'timeslot': t,
                    'room': room['RoomID'],
                    'instructor': instr_id
                })
    
    return domain_vals

def is_consistent(assignment: Dict, var: str, val: Dict, meta: Dict, fast_mode=True) -> bool:
    """
    OPTIMIZED consistency checking
    """
    # Extract components
    day, start_time, end_time = val['timeslot']
    room = val['room']
    instructor = val['instructor']
    
    current_course = meta[var]['course']
    current_sections = set(meta[var]['sections'])
    
    # Fast conflict detection
    for assigned_var, assigned_val in assignment.items():
        # Same timeslot conflicts
        if assigned_val['timeslot'] == val['timeslot']:
            # Room conflict
            if assigned_val['room'] == room:
                return False
            
            # Instructor conflict
            if assigned_val['instructor'] == instructor:
                return False
            
            # Section overlap conflict
            assigned_meta = meta[assigned_var]
            assigned_sections = set(assigned_meta['sections'])
            if current_sections & assigned_sections:
                return False
    
    return True

def select_unassigned_variable(variables: List[str], domains: Dict, assignment: Dict, meta: Dict, fast_mode=True) -> str:
    """
    OPTIMIZED variable selection using MRV (Minimum Remaining Values)
    """
    unassigned = [v for v in variables if v not in assignment]
    
    if not unassigned:
        return None
    
    if fast_mode:
        # Fast mode: simple ordering
        return unassigned[0]
    else:
        # MRV heuristic
        return min(unassigned, key=lambda v: len(domains[v]))

def order_domain_values(var: str, domains: Dict, assignment: Dict, meta: Dict, fast_mode=True) -> List:
    """
    OPTIMIZED value ordering
    """
    values = domains[var]
    
    if fast_mode:
        # Random shuffle for diversity
        random.shuffle(values)
    else:
        # Least constraining value heuristic
        values.sort(key=lambda v: count_conflicts(var, v, assignment, meta))
    
    return values

def count_conflicts(var: str, val: Dict, assignment: Dict, meta: Dict) -> int:
    """Count potential conflicts for a value"""
    conflicts = 0
    day, start_time, end_time = val['timeslot']
    room = val['room']
    instructor = val['instructor']
    
    current_sections = set(meta[var]['sections'])
    
    for assigned_var, assigned_val in assignment.items():
        if assigned_val['timeslot'] == val['timeslot']:
            if assigned_val['room'] == room:
                conflicts += 1
            if assigned_val['instructor'] == instructor:
                conflicts += 1
            if set(meta[assigned_var]['sections']) & current_sections:
                conflicts += 1
    
    return conflicts

def backtracking_search(variables: List[str], domains: Dict, meta: Dict, timeout: int = 30, fast_mode=True) -> Optional[Dict]:
    """
    OPTIMIZED backtracking search with timeout and performance improvements
    """
    start_time = time.time()
    
    def backtrack(assignment: Dict, depth: int = 0) -> Optional[Dict]:
        # Timeout check
        if time.time() - start_time > timeout:
            return None
        
        if len(assignment) == len(variables):
            return assignment
        
        var = select_unassigned_variable(variables, domains, assignment, meta, fast_mode)
        if var is None:
            return assignment
        
        for val in order_domain_values(var, domains, assignment, meta, fast_mode):
            if is_consistent(assignment, var, val, meta, fast_mode):
                assignment[var] = val
                result = backtrack(assignment, depth + 1)
                if result is not None:
                    return result
                del assignment[var]
        
        return None
    
    return backtrack({})

def generate_timetable(courses_df, instructors_df, rooms_df, timeslots_df, sections_df, 
                      force_permissive=False, timeout=30, fast_mode=True):
    """
    Main timetable generation function with optimizations
    """
    print(f"[OPTIMIZED] Starting timetable generation (timeout: {timeout}s, fast_mode: {fast_mode})")
    
    # Build domains with optimizations
    variables, domains, meta, course_to_section_groups = build_domains(
        courses_df, instructors_df, rooms_df, timeslots_df, sections_df, 
        force_permissive, fast_mode
    )
    
    if not variables:
        print("[ERROR] No variables generated - check your data")
        return None
    
    print(f"[OPTIMIZED] Starting search with {len(variables)} variables")
    
    # Run backtracking search
    solution = backtracking_search(variables, domains, meta, timeout, fast_mode)
    
    if solution:
        print(f"[SUCCESS] Found solution with {len(solution)} assignments")
        return {
            'solution': solution,
            'meta': meta,
            'total_variables': len(variables),
            'course_to_section_groups': course_to_section_groups
        }
    else:
        print(f"[FAILED] No solution found within {timeout} seconds")
        return None

def format_timetable_for_display(solution: Dict, meta: Dict, courses_df: pd.DataFrame, 
                                instructors_df: pd.DataFrame, course_to_section_groups: Dict) -> pd.DataFrame:
    """
    Format the solution for display
    """
    if not solution:
        return pd.DataFrame()
    
    rows = []
    
    # Create course info mapping
    course_info = {}
    for _, course in courses_df.iterrows():
        course_info[course['CourseID']] = {
            'name': course['CourseName'],
            'year': course['Year']
        }
    
    # Create instructor name mapping
    instructor_names = {}
    for _, instr in instructors_df.iterrows():
        instr_id = instr['InstructorID'] if 'InstructorID' in instr else instr.get('Name')
        instructor_names[instr_id] = instr.get('Name', 'Unknown')
    
    for var, val in solution.items():
        if var not in meta:
            continue
        
        info = meta[var]
        course_id = info['course']
        sections = info['sections']
        
        day, start_time, end_time = val['timeslot']
        room = val['room']
        instructor_id = val['instructor']
        instructor_name = instructor_names.get(instructor_id, instructor_id)
        
        course_data = course_info.get(course_id, {'name': 'Unknown', 'year': 1})
        
        for section in sections:
            rows.append({
                'CourseID': course_id,
                'CourseName': course_data['name'],
                'CourseYear': course_data['year'],
                'SectionID': section,
                'SessionType': info.get('type', 'Lecture'),
                'Day': day,
                'StartTime': start_time,
                'EndTime': end_time,
                'Room': room,
                'Instructor': instructor_name
            })
    
    df = pd.DataFrame(rows)
    
    if not df.empty:
        # Sort by day and time
        day_order = {'Sunday': 0, 'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4}
        df['DayOrder'] = df['Day'].map(day_order)
        
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
        
        df['TimeOrder'] = df['StartTime'].apply(time_to_minutes)
        df = df.sort_values(['DayOrder', 'TimeOrder']).drop(['DayOrder', 'TimeOrder'], axis=1)
    
    return df