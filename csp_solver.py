"""
CSP-based Timetable Generator
Adapted from proven implementation with section conflict prevention
"""

import pandas as pd
import random
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set


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
    """
    Check if a course can be assigned to a section based on year and department rules.
    
    Rules:
    - Years 1-2: section format is "year/number" (e.g., "1/5", "2/3")
    - Years 3-4: section format is "year/department/number" (e.g., "3/CNC/1", "4/AID/2")
    - Shared courses (Year 3): Assigned to all departments (AID, BIF, CSC, CNC)
    """
    if not section_id or '/' not in str(section_id):
        return True
    
    parts = str(section_id).split('/')
    if len(parts) < 2:
        return True
    
    section_year_str = parts[0].strip()
    section_right = parts[1].strip() if len(parts) >= 2 else ""
    
    try:
        section_year = int(section_year_str)
    except ValueError:
        return True
    
    # Check if course year matches section year
    if course_year != section_year:
        return False
    
    # For years 1-2, only year matching is required
    if course_year in [1, 2]:
        return True
    
    # For year 3, check if course is shared
    if course_year == 3 and is_shared:
        section_dept = section_right.upper()
        return section_dept in ['AID', 'BIF', 'CSC', 'CNC']
    
    # For years 3-4 (non-shared or year 4), check department matching
    if course_year in [3, 4]:
        course_dept = course_id[:3].upper() if len(course_id) >= 3 else ""
        section_dept = section_right.upper()
        return course_dept == section_dept
    
    return True


def create_section_groups(sections: List[str], session_type: str = 'Lecture') -> List[List[str]]:
    """
    Group sections based on session type:
    - TUT: Individual sections (1 per group)
    - Lab: Pairs (2 per group)
    - Lecture: 3-4 per group based on total count
    """
    if session_type == 'TUT':
        group_size = 1
    elif session_type == 'Lab':
        group_size = 2
    else:
        group_size = 4 if len(sections) % 2 == 0 else 3
    
    groups = []
    for i in range(0, len(sections), group_size):
        group = sections[i:i+group_size]
        groups.append(group)
    
    return groups


def build_domains(courses_df, instructors_df, rooms_df, timeslots_df, sections_df, force_permissive=False):
    """
    Build CSP domains with proper constraint checking.
    Returns: (variables, domains, meta, course_to_section_groups)
    """
    
    # Parse instructor qualifications
    instructors_df = instructors_df.copy()
    instructors_df['_quals'] = instructors_df['QualifiedCourses'].apply(parse_qualified_courses)
    
    course_types = dict(zip(courses_df['CourseID'], courses_df['Type']))
    course_years = dict(zip(courses_df['CourseID'], courses_df['Year']))
    course_shared = dict(zip(courses_df['CourseID'], courses_df.get('Shared', pd.Series())))
    
    # Build course to section groups mapping
    course_to_section_groups = defaultdict(dict)
    
    for _, course in courses_df.iterrows():
        course_id = course['CourseID']
        course_year = course_years.get(course_id)
        
        if course_year is None:
            continue
        
        # Check if course is shared
        is_shared = False
        if course_year == 3 and 'Shared' in course:
            shared_val = str(course.get('Shared', '')).strip().lower()
            is_shared = shared_val == 'yes'
        
        # Find matching sections
        matching_sections = []
        for _, sec in sections_df.iterrows():
            section_id = str(sec['SectionID'])
            if can_assign_course_to_section(course_id, section_id, course_year, is_shared):
                matching_sections.append(section_id)
        
        # Create groups for each session type
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
    
    # Separate timeslots by duration
    timeslots_45 = []
    timeslots_90 = []
    
    for idx, r in timeslots_df.iterrows():
        slot = (r['Day'], r['StartTime'], r['EndTime'])
        
        if 'Duration' in timeslots_df.columns:
            duration = r.get('Duration', 90)
            if duration == 45:
                timeslots_45.append(slot)
            elif duration == 90:
                timeslots_90.append(slot)
        else:
            timeslots_90.append(slot)
    
    rooms = list(rooms_df.to_dict('records'))
    instructors = list(instructors_df.to_dict('records'))
    
    # Create variables for course-group pairs
    variables = []
    domains = {}
    meta = {}
    rejection_reasons = defaultdict(lambda: defaultdict(int))
    fallbacks_used = defaultdict(list)
    
    for _, course in courses_df.iterrows():
        course_id = course['CourseID']
        course_year = course_years.get(course_id, None)
        
        if course_id not in course_to_section_groups or not course_to_section_groups[course_id]:
            continue
        
        ctype = course_types.get(course_id, 'Lecture')
        
        for session_type, section_groups in course_to_section_groups[course_id].items():
            for group_idx, section_group in enumerate(section_groups):
                var = f"{course_id}::G{group_idx}::{session_type}"
                variables.append(var)
                
                def generate_vals(allow_unqualified=False, allow_room_mismatch=False, allow_role_mismatch=False):
                    vals_local = []
                    
                    # Pre-filter instructors
                    valid_instructors = []
                    for instr in instructors:
                        quals = instr.get('_quals', [])
                        if not allow_unqualified and quals and course_id not in quals:
                            rejection_reasons[var]['unqualified_instructor'] += 1
                            continue
                        
                        # STRICT role-based assignment
                        instr_role = str(instr.get('Role', '')).lower()
                        is_lab_or_tut = ('lab' in session_type.lower() or 'tut' in session_type.lower())
                        
                        if not allow_role_mismatch and instr_role:
                            if 'assistant' in instr_role and not is_lab_or_tut:
                                rejection_reasons[var]['role_mismatch_assistant_to_lecture'] += 1
                                continue
                            elif 'professor' in instr_role and 'assistant' not in instr_role and is_lab_or_tut:
                                rejection_reasons[var]['role_mismatch_professor_to_lab_or_tut'] += 1
                                continue
                        
                        valid_instructors.append(instr)
                    
                    # Pre-filter rooms
                    valid_rooms = []
                    for room in rooms:
                        rtype = room.get('Type', 'Lecture')
                        
                        if session_type.lower() == 'lab' and not rtype.lower().startswith('lab'):
                            if not allow_room_mismatch:
                                rejection_reasons[var]['room_type_mismatch'] += 1
                                continue
                        elif session_type.lower() == 'lecture' and (rtype.lower().startswith('lab') or rtype.lower() == 'tut'):
                            if not allow_room_mismatch:
                                rejection_reasons[var]['room_type_mismatch'] += 1
                                continue
                        elif session_type.lower() == 'tut' and rtype.lower() != 'tut':
                            if not allow_room_mismatch:
                                rejection_reasons[var]['room_type_mismatch'] += 1
                                continue
                        
                        valid_rooms.append(room)
                    
                    # Filter timeslots based on duration
                    ctype_lower = ctype.lower() if isinstance(ctype, str) else 'lecture'
                    
                    if session_type.lower() == 'tut':
                        has_lab = 'lab' in ctype_lower
                        has_lecture = 'lecture' in ctype_lower
                        
                        if has_lab and has_lecture:
                            valid_timeslots = timeslots_45 if timeslots_45 else timeslots_90
                        else:
                            valid_timeslots = timeslots_90 if timeslots_90 else timeslots_45
                    else:
                        valid_timeslots = timeslots_90 if timeslots_90 else timeslots_45
                    
                    # Create combinations
                    for t in valid_timeslots:
                        day = t[0]
                        for instr in valid_instructors:
                            pref_slots = instr.get('PreferredSlots', '')
                            if pref_slots and isinstance(pref_slots, str):
                                if 'Not on' in pref_slots and day in pref_slots:
                                    if not allow_unqualified:
                                        rejection_reasons[var]['instructor_unavailable'] += 1
                                        continue
                            
                            instr_id = instr['InstructorID'] if 'InstructorID' in instr else instr.get('Name')
                            
                            for room in valid_rooms:
                                vals_local.append({
                                    'timeslot': t,
                                    'room': room['RoomID'],
                                    'instructor': instr_id
                                })
                    
                    return vals_local
                
                # Progressive fallback system (NEVER allow role mismatch)
                if force_permissive:
                    vals = generate_vals(allow_unqualified=True, allow_room_mismatch=True, allow_role_mismatch=False)
                    if vals:
                        fallbacks_used[var].append('force_permissive_initial')
                else:
                    vals = generate_vals(allow_unqualified=False, allow_room_mismatch=False, allow_role_mismatch=False)
                
                if not vals:
                    vals = generate_vals(allow_unqualified=True, allow_room_mismatch=False, allow_role_mismatch=False)
                    if vals:
                        fallbacks_used[var].append('allow_unqualified_instructor')
                
                if not vals:
                    vals = generate_vals(allow_unqualified=False, allow_room_mismatch=True, allow_role_mismatch=False)
                    if vals:
                        fallbacks_used[var].append('allow_room_type_mismatch')
                
                if not vals:
                    vals = generate_vals(allow_unqualified=True, allow_room_mismatch=True, allow_role_mismatch=False)
                    if vals:
                        fallbacks_used[var].append('allow_unqualified_and_room_mismatch')
                
                domains[var] = vals
                meta[var] = {
                    'course': course_id,
                    'group_index': group_idx,
                    'sections': section_group,
                    'type': ctype,
                    'rejection_reasons': dict(rejection_reasons.get(var, {})),
                    'fallbacks': fallbacks_used.get(var, [])
                }
    
    print(f'[CSP] Created {len(variables)} variables (course-group based)')
    return variables, domains, meta, course_to_section_groups


def forward_checking_search(variables, domains, meta):
    """
    Enhanced forward checking search with section conflict prevention
    """
    assignment = {}
    
    # Pre-compute constraint neighbors
    var_timeslots = {}
    for v in variables:
        ts_set = set()
        for val in domains[v]:
            ts_set.add(val['timeslot'])
        var_timeslots[v] = ts_set
    
    constraint_neighbors = {}
    for v in variables:
        neighbors = []
        v_ts = var_timeslots[v]
        for other in variables:
            if other != v and v_ts & var_timeslots[other]:
                neighbors.append(other)
        constraint_neighbors[v] = neighbors
    
    # Cache for timeslot assignments - INCLUDES SECTIONS
    assigned_by_timeslot = {}
    local_domains = {v: list(domains[v]) for v in variables}
    
    print(f"[CSP] Constraint graph built - avg neighbors: {sum(len(n) for n in constraint_neighbors.values())/len(constraint_neighbors):.1f}")
    
    def consistent(var, val):
        """Fast consistency check with SECTION conflict prevention"""
        ts = val['timeslot']
        if ts not in assigned_by_timeslot:
            return True
        
        ts_data = assigned_by_timeslot[ts]
        var_sections = set(meta[var]['sections'])
        
        # Check instructor conflict
        if val['instructor'] in ts_data['instructor']:
            return False
        
        # Check room conflict
        if val['room'] in ts_data['room']:
            return False
        
        # CHECK SECTION CONFLICT - CRITICAL
        if var_sections & ts_data['sections']:
            return False
        
        return True
    
    def select_unassigned_var():
        """MRV heuristic with dynamic degree"""
        unassigned = [v for v in variables if v not in assignment]
        if not unassigned:
            return None
        
        def heuristic(x):
            domain_size = len(local_domains.get(x, []))
            if domain_size == 0:
                return (0, 0)
            unassigned_neighbors = sum(1 for n in constraint_neighbors.get(x, []) 
                                      if n not in assignment)
            return (domain_size, -unassigned_neighbors)
        
        return min(unassigned, key=heuristic)
    
    def order_domain_values(var):
        """Order domain values for efficiency"""
        domain_vals = local_domains.get(var, [])
        
        if len(domain_vals) <= 10:
            return domain_vals
        
        def timeslot_score(val):
            ts = val['timeslot']
            ts_data = assigned_by_timeslot.get(ts, {})
            used_count = len(ts_data.get('instructor', set())) + len(ts_data.get('room', set()))
            return used_count
        
        return sorted(domain_vals, key=timeslot_score)
    
    backtrack_calls = [0]
    max_depth = [0]
    
    def backtrack(depth=0):
        backtrack_calls[0] += 1
        max_depth[0] = max(max_depth[0], depth)
        
        if len(assignment) == len(variables):
            return True
        
        var = select_unassigned_var()
        if var is None:
            return True
        
        domain_vals = order_domain_values(var)
        if not domain_vals:
            return False
        
        for val in domain_vals:
            if not consistent(var, val):
                continue
            
            assignment[var] = val
            ts = val['timeslot']
            
            # Update timeslot tracking - ADD SECTIONS
            if ts not in assigned_by_timeslot:
                assigned_by_timeslot[ts] = {'instructor': set(), 'room': set(), 'sections': set()}
            
            assigned_by_timeslot[ts]['instructor'].add(val['instructor'])
            assigned_by_timeslot[ts]['room'].add(val['room'])
            
            # Add ALL sections from this variable's group
            for section in meta[var]['sections']:
                assigned_by_timeslot[ts]['sections'].add(section)
            
            removed = {}
            failure = False
            
            # Forward checking
            for neighbor in constraint_neighbors.get(var, []):
                if neighbor in assignment:
                    continue
                
                neighbor_sections = set(meta[neighbor]['sections'])
                
                newdom = []
                for nval in local_domains.get(neighbor, []):
                    if nval['timeslot'] != ts:
                        newdom.append(nval)
                    elif (nval['instructor'] != val['instructor'] and 
                          nval['room'] != val['room'] and 
                          not (neighbor_sections & assigned_by_timeslot[ts]['sections'])):
                        newdom.append(nval)
                
                if len(newdom) == 0:
                    failure = True
                    break
                
                if len(newdom) < len(local_domains[neighbor]):
                    removed[neighbor] = local_domains[neighbor]
                    local_domains[neighbor] = newdom
            
            if not failure:
                result = backtrack(depth + 1)
                if result:
                    return True
            
            # Restore domains
            for k, v in removed.items():
                local_domains[k] = v
            
            # Restore timeslot tracking
            assigned_by_timeslot[ts]['instructor'].discard(val['instructor'])
            assigned_by_timeslot[ts]['room'].discard(val['room'])
            for section in meta[var]['sections']:
                assigned_by_timeslot[ts]['sections'].discard(section)
            
            if not assigned_by_timeslot[ts]['instructor'] and not assigned_by_timeslot[ts]['room'] and not assigned_by_timeslot[ts]['sections']:
                del assigned_by_timeslot[ts]
            
            del assignment[var]
        
        return False
    
    print("[CSP] Starting backtracking search...")
    success = backtrack()
    print(f"[CSP] Search complete: backtrack_calls={backtrack_calls[0]}, max_depth={max_depth[0]}")
    
    if not success:
        return None
    return assignment


def format_timetable_for_display(assign, meta, courses_df, instructors_df, course_to_section_groups):
    """
    Convert solution to DataFrame with proper section expansion
    """
    course_name_map = {}
    if courses_df is not None and 'CourseID' in courses_df.columns and 'CourseName' in courses_df.columns:
        course_name_map = dict(zip(courses_df['CourseID'].astype(str), courses_df['CourseName']))
    
    instructor_name_map = {}
    if instructors_df is not None:
        if 'InstructorID' in instructors_df.columns and 'Name' in instructors_df.columns:
            instructor_name_map = dict(zip(instructors_df['InstructorID'].astype(str), instructors_df['Name']))
    
    rows = []
    for var, val in assign.items():
        parts = var.split('::')
        if len(parts) == 3 and parts[1].startswith('G'):
            course = parts[0]
            group_index = parts[1]
            session_type = parts[2]
            
            # Get sections from meta
            sections = meta.get(var, {}).get('sections', [])
            
            if not sections and course_to_section_groups:
                try:
                    group_idx = int(group_index[1:])
                    if course in course_to_section_groups:
                        session_groups = course_to_section_groups[course].get(session_type, [])
                        if group_idx < len(session_groups):
                            sections = session_groups[group_idx]
                except (ValueError, IndexError):
                    pass
            
            if not sections:
                sections = ['Unknown']
            
            day, start, end = val['timeslot']
            course_name = course_name_map.get(course, course)
            instructor_id = val['instructor']
            instructor_name = instructor_name_map.get(str(instructor_id), instructor_id)
            
            # Get course year
            course_year = 1
            if courses_df is not None:
                course_row = courses_df[courses_df['CourseID'] == course]
                if not course_row.empty:
                    course_year = course_row['Year'].iloc[0]
            
            # Create row for EACH section
            for section in sections:
                rows.append({
                    'CourseID': course,
                    'CourseName': course_name,
                    'CourseYear': course_year,
                    'SectionID': section,
                    'SessionType': session_type,
                    'Day': day,
                    'StartTime': start,
                    'EndTime': end,
                    'Room': val['room'],
                    'Instructor': instructor_name
                })
    
    df = pd.DataFrame(rows)
    
    if df.empty:
        return df
    
    # Sort by day and time
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    df['DayOrder'] = df['Day'].map(lambda x: day_order.index(x) if x in day_order else 999)
    
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
    df = df.sort_values(['DayOrder', 'TimeOrder', 'CourseID']).drop(['DayOrder', 'TimeOrder'], axis=1).reset_index(drop=True)
    
    return df


def generate_timetable(courses_df, instructors_df, rooms_df, timeslots_df, sections_df, 
                      force_permissive=False, timeout=120):
    """
    Main entry point for timetable generation
    
    Returns:
        Dictionary with:
        - solution: assignment dictionary
        - meta: variable metadata
        - course_to_section_groups: mapping dictionary
        - total_variables: number of variables
    """
    try:
        print("[CSP] Building domains...")
        variables, domains, meta, course_to_section_groups = build_domains(
            courses_df, instructors_df, rooms_df, timeslots_df, sections_df, force_permissive
        )
        
        if not variables:
            print("[CSP] ERROR: No variables created!")
            return None
        
        print(f"[CSP] Created {len(variables)} variables")
        
        # Check for empty domains
        empty_domains = [v for v in variables if not domains.get(v)]
        if empty_domains:
            print(f"[CSP] WARNING: {len(empty_domains)} variables have empty domains")
            for v in empty_domains[:5]:
                print(f"  - {v}")
                reasons = meta.get(v, {}).get('rejection_reasons', {})
                if reasons:
                    print(f"    Reasons: {reasons}")
        
        print("[CSP] Running forward checking search...")
        assign = forward_checking_search(variables, domains, meta)
        
        if assign is None:
            print("[CSP] No solution found in strict mode")
            
            if not force_permissive:
                print("[CSP] Retrying with permissive mode...")
                variables2, domains2, meta2, course_to_section_groups2 = build_domains(
                    courses_df, instructors_df, rooms_df, timeslots_df, sections_df, 
                    force_permissive=True
                )
                assign2 = forward_checking_search(variables2, domains2, meta2)
                
                if assign2 is not None:
                    print('[CSP] Permissive mode succeeded')
                    return {
                        'solution': assign2,
                        'meta': meta2,
                        'course_to_section_groups': course_to_section_groups2,
                        'total_variables': len(variables2)
                    }
            
            return None
        
        print(f"[CSP] Success! Assigned {len(assign)}/{len(variables)} variables")
        
        return {
            'solution': assign,
            'meta': meta,
            'course_to_section_groups': course_to_section_groups,
            'total_variables': len(variables)
        }
        
    except Exception as e:
        print(f"[CSP] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None