import os
import itertools
import pandas as pd
from collections import defaultdict
import random


def load_csvs(upload_dir):
    # Expect files in upload_dir: courses.csv, instructors.csv, rooms.csv, timeslots.csv, sections.csv
    paths = {
        'courses': f"{upload_dir}/courses.csv",
        'instructors': f"{upload_dir}/instructors.csv",
        'rooms': f"{upload_dir}/rooms.csv",
        'timeslots': f"{upload_dir}/timeslots.csv",
        'sections': f"{upload_dir}/sections.csv",
    }
    dfs = {}
    for k, p in paths.items():
        # First try upload_dir/<k>/<k>.csv (how uploads are stored), then upload_dir/<k>.csv
        alt = os.path.join(upload_dir, k, f"{k}.csv")
        p1 = p
        p2 = alt
        found = None
        for candidate in (p2, p1):
            try:
                dfs[k] = pd.read_csv(candidate)
                found = candidate
                break
            except FileNotFoundError:
                continue
        if found is None:
            raise FileNotFoundError(f"Missing required upload: {k} (tried {p2} and {p1})")
    return dfs['courses'], dfs['instructors'], dfs['rooms'], dfs['timeslots'], dfs['sections']



def parse_qualified_courses(val):
    # instructors.QualifiedCourses may be comma separated
    if pd.isna(val):
        return []
    if isinstance(val, str):
        return [s.strip() for s in val.split(',') if s.strip()]
    if isinstance(val, (list, tuple)):
        return list(val)
    return []


def can_assign_course_to_section(course_id, section_id, course_year, is_shared=False):
    """
    Check if a course can be assigned to a section based on year and department rules.
    
    Rules:
    - For years 1-2: section format is "year/number" (e.g., "1/5", "2/3")
        Course is assigned if section year matches course year
    - For years 3-4: section format is "year/department/number" (e.g., "3/CNC/1", "4/AID/2")
    Course is assigned if:
        1. Section year matches course year AND
        2. If is_shared=True (3rd year only): assign to all departments (AID, BIF, CSC, CNC)
        3. If is_shared=False: Course department (first 3 letters) matches section department
    
    Args:
        course_id: Course identifier (e.g., "CSC111", "AID321")
        section_id: Section identifier (e.g., "1/5", "3/CNC/1", "4/AID/2")
        course_year: Year level of the course (1, 2, 3, or 4)
        is_shared: Whether the course is shared across departments (year 3 only)
    
    Returns:
        bool: True if course can be assigned to this section
    """
    if not section_id or '/' not in str(section_id):
        return True  # If no proper section format, allow assignment
    
    parts = str(section_id).split('/')
    if len(parts) < 2:
        return True
    
    section_year_str = parts[0].strip()
    # For years 3-4: extract department from 2nd part (e.g., "3/CNC/1" -> "CNC")
    # For years 1-2: use 2nd part directly (e.g., "1/5" -> "5")
    section_right = parts[1].strip() if len(parts) >= 2 else ""
    
    try:
        section_year = int(section_year_str)
    except ValueError:
        return True  # If section year is not a number, allow assignment
    
    # Check if course year matches section year
    if course_year != section_year:
        return False
    
    # For years 1-2, only year matching is required
    if course_year in [1, 2]:
        return True
    
    # For year 3, check if course is shared
    if course_year == 3 and is_shared:
        # Shared courses in year 3 should be assigned to all departments
        section_dept = section_right.upper()
        # Check if section belongs to one of the main departments
        return section_dept in ['AID', 'BIF', 'CSC', 'CNC']
    
    # For years 3-4 (non-shared or year 4), also check department matching
    if course_year in [3, 4]:
        # Extract department from course ID (first 3 letters)
        course_dept = course_id[:3].upper() if len(course_id) >= 3 else ""
        section_dept = section_right.upper()
        
        # Course department must match section department
        return course_dept == section_dept
    
    return True



def create_section_groups(sections, session_type='Lecture'):
    """
    Group sections based on session type:
    - TUT: Individual sections (1 per group)
    - Lab: Pairs (2 per group)
    - Lecture: 3-4 per group based on total count
    """
    if session_type == 'TUT':
        # TUT sessions are individual - each section gets its own timeslot
        group_size = 1
    elif session_type == 'Lab':
        # Labs are in pairs
        group_size = 2
    else:
        # Lectures: use 4 if even number of sections, 3 if odd
        group_size = 4 if len(sections) % 2 == 0 else 3
    
    # Create groups of the specified size
    groups = []
    for i in range(0, len(sections), group_size):
        group = sections[i:i+group_size]
        groups.append(group)
    
    return groups


def build_domains(courses_df, instructors_df, rooms_df, timeslots_df, sections_df, force_permissive=False):
    # Required columns checks
    if 'CourseID' not in courses_df.columns:
        raise ValueError('courses.csv must contain CourseID')
    if 'Type' not in courses_df.columns:
        raise ValueError('courses.csv must contain Type')
    if 'InstructorID' not in instructors_df.columns and 'QualifiedCourses' not in instructors_df.columns:
        pass
    if 'RoomID' not in rooms_df.columns:
        raise ValueError('rooms.csv must contain RoomID')
    if 'Type' not in rooms_df.columns:
        raise ValueError('rooms.csv must contain Type (Lab/Lecture)')
    if 'Day' not in timeslots_df.columns or 'StartTime' not in timeslots_df.columns or 'EndTime' not in timeslots_df.columns:
        raise ValueError('timeslots.csv must contain Day, StartTime, EndTime')

    instructors_df = instructors_df.copy()
    if 'QualifiedCourses' in instructors_df.columns:
        instructors_df['_quals'] = instructors_df['QualifiedCourses'].apply(parse_qualified_courses)
    else:
        instructors_df['_quals'] = [[] for _ in range(len(instructors_df))]

    course_types = dict(zip(courses_df['CourseID'], courses_df['Type']))
    
    # Create a mapping for course years
    course_years = {}
    if 'Year' in courses_df.columns:
        course_years = dict(zip(courses_df['CourseID'], courses_df['Year']))
    
    # Create a mapping for shared courses
    course_shared = {}
    if 'Shared' in courses_df.columns:
        course_shared = dict(zip(courses_df['CourseID'], courses_df['Shared']))

    if 'SectionID' not in sections_df.columns:
        raise ValueError('sections.csv must include SectionID')

    # Build mapping: course -> {session_type: [groups]} for different grouping per session type
    course_to_section_groups = defaultdict(dict)
    
    if 'CourseID' not in sections_df.columns:
        # Smart assignment of courses to sections based on year and department rules
        print('[csp] CourseID not found in sections - building course-to-sections mapping with grouping')
        
        for _, course in courses_df.iterrows():
            course_id = course['CourseID']
            course_year = course_years.get(course_id)
            
            if course_year is None:
                continue
            
            # Check if course is shared (only for year 3)
            is_shared = False
            if course_year == 3 and 'Shared' in course:
                shared_val = str(course.get('Shared', '')).strip().lower()
                is_shared = shared_val == 'yes'
            
            # Find ALL matching sections for this course
            matching_sections = []
            for _, sec in sections_df.iterrows():
                section_id = str(sec['SectionID'])
                
                # Check if this course can be assigned to this section
                if can_assign_course_to_section(course_id, section_id, course_year, is_shared):
                    matching_sections.append(section_id)
            
            # Group the sections differently for each session type
            if matching_sections:
                # Parse course type
                ctype = course_types.get(course_id, 'Lecture')
                ctype_lower = ctype.lower() if isinstance(ctype, str) else 'lecture'
                
                # Create groups for each session type the course needs
                if 'lecture' in ctype_lower:
                    course_to_section_groups[course_id]['Lecture'] = create_section_groups(matching_sections, 'Lecture')
                if 'lab' in ctype_lower:
                    course_to_section_groups[course_id]['Lab'] = create_section_groups(matching_sections, 'Lab')
                if 'tut' in ctype_lower:
                    course_to_section_groups[course_id]['TUT'] = create_section_groups(matching_sections, 'TUT')
                
                # If no session type found, default to Lecture
                if not course_to_section_groups[course_id]:
                    course_to_section_groups[course_id]['Lecture'] = create_section_groups(matching_sections, 'Lecture')
        
        print(f'[csp] Mapped {len(course_to_section_groups)} courses to section groups')
        for year in sorted(set(course_years.values())):
            year_courses = [c for c, y in course_years.items() if y == year and c in course_to_section_groups]
            if year_courses:
                total_lecture_groups = sum([len(course_to_section_groups[c].get('Lecture', [])) for c in year_courses])
                total_lab_groups = sum([len(course_to_section_groups[c].get('Lab', [])) for c in year_courses])
                total_tut_groups = sum([len(course_to_section_groups[c].get('TUT', [])) for c in year_courses])
                print(f'[csp]   Year {int(year)}: {len(year_courses)} courses → Lectures: {total_lecture_groups} groups, Labs: {total_lab_groups} groups, TUTs: {total_tut_groups} groups')

    timeslots = []
    timeslots_45 = []  # Store 45-minute timeslots separately
    timeslots_90 = []  # Store 90-minute timeslots separately
    
    for idx, r in timeslots_df.iterrows():
        slot = (r['Day'], r['StartTime'], r['EndTime'])
        timeslots.append(slot)
        
        # Categorize by duration if Duration column exists
        if 'Duration' in timeslots_df.columns:
            duration = r.get('Duration', 90)
            if duration == 45:
                timeslots_45.append(slot)
            elif duration == 90:
                timeslots_90.append(slot)
        else:
            # If no Duration column, assume all are 90 minutes
            timeslots_90.append(slot)

    rooms = list(rooms_df.to_dict('records'))
    instructors = list(instructors_df.to_dict('records'))

    if len(timeslots) == 0:
        raise ValueError('timeslots.csv contains no rows')
    if len(rooms) == 0:
        raise ValueError('rooms.csv contains no rows')
    if len(instructors) == 0:
        raise ValueError('instructors.csv contains no rows')

    # NEW APPROACH: Create variables for COURSE-GROUP pairs
    # Each group of sections shares the same timeslot
    variables = []
    domains = {}
    meta = {}
    rejection_reasons = defaultdict(lambda: defaultdict(int))
    fallbacks_used = defaultdict(list)
    
    # Process each course and its section groups
    for _, course in courses_df.iterrows():
        course_id = course['CourseID']
        course_year = course_years.get(course_id, None)
        
        # Skip courses without matching section groups
        if course_id not in course_to_section_groups or not course_to_section_groups[course_id]:
            continue
        
        ctype = course_types.get(course_id, 'Lecture')
        
        # For each session type this course has, create variables for its groups
        for session_type, section_groups in course_to_section_groups[course_id].items():
            # Create a variable for each group in this session type
            for group_idx, section_group in enumerate(section_groups):
                # Variable name: CourseID::GroupIndex::SessionType (e.g., "CSC111::G0::Lecture", "CSC111::G0::Lab")
                var = f"{course_id}::G{group_idx}::{session_type}"
                variables.append(var)

                def generate_vals(allow_unqualified=False, allow_room_mismatch=False, allow_role_mismatch=False):
                    vals_local = []
                    
                    # Pre-filter instructors to avoid repeated checks
                    valid_instructors = []
                    for instr in instructors:
                        # Check qualifications
                        quals = instr.get('_quals', [])
                        if not allow_unqualified and quals and course_id not in quals:
                            rejection_reasons[var]['unqualified_instructor'] += 1
                            continue
                        
                        # Check role-based assignment
                        instr_role = str(instr.get('Role', '')).lower()
                        is_lab_or_tut = ('lab' in session_type.lower() or 'tut' in session_type.lower())
                        
                        if not allow_role_mismatch and instr_role:
                            # Assistant Professor should only teach labs and tutorials
                            if 'assistant' in instr_role and not is_lab_or_tut:
                                rejection_reasons[var]['role_mismatch_assistant_to_lecture'] += 1
                                continue
                            # Professor should only teach lectures
                            elif 'professor' in instr_role and 'assistant' not in instr_role and is_lab_or_tut:
                                rejection_reasons[var]['role_mismatch_professor_to_lab_or_tut'] += 1
                                continue
                        
                        valid_instructors.append(instr)
                    
                    # Pre-filter rooms
                    valid_rooms = []
                    for room in rooms:
                        rtype = room.get('Type', 'Lecture')
                        
                        # Match room type to session type
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
                    
                    # Filter timeslots based on session type and course type
                    # Rule: If course has "Lecture and Lab and TUT" → TUT uses 45-min slots
                    #       If course has "Lecture and TUT" (no Lab) → TUT uses 90-min slots
                    ctype_lower = ctype.lower() if isinstance(ctype, str) else 'lecture'
                    
                    if session_type.lower() == 'tut':
                        # Check if course has both Lab and TUT
                        has_lab = 'lab' in ctype_lower
                        has_lecture = 'lecture' in ctype_lower
                        
                        if has_lab and has_lecture:
                            # "Lecture and Lab and TUT" → use 45-minute slots
                            valid_timeslots = timeslots_45 if timeslots_45 else timeslots
                        else:
                            # "Lecture and TUT" (no Lab) → use 90-minute slots
                            valid_timeslots = timeslots_90 if timeslots_90 else timeslots
                    else:
                        # Lecture and Lab always use 90-minute slots
                        valid_timeslots = timeslots_90 if timeslots_90 else timeslots
                    
                    # Now generate combinations with pre-filtered lists
                    for t in valid_timeslots:
                        day = t[0]
                        for instr in valid_instructors:
                            # Check instructor day preferences
                            pref_slots = instr.get('PreferredSlots', '')
                            if pref_slots and isinstance(pref_slots, str):
                                if 'Not on' in pref_slots and day in pref_slots:
                                    if not allow_unqualified:  # treat as similar constraint level
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

                if force_permissive:
                    # Even in permissive mode, NEVER allow role mismatch (hard constraint)
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
                    'sections': section_group,  # Store sections in this group
                    'type': ctype
                }

    for v in variables:
        meta[v]['rejection_reasons'] = dict(rejection_reasons.get(v, {}))
        meta[v]['fallbacks'] = fallbacks_used.get(v, [])

    print(f'[csp] Created {len(variables)} variables (course-group based)')
    return variables, domains, meta, course_to_section_groups



def forward_checking_search(variables, domains, meta):
    assignment = {}
    
    # Pre-compute constraint neighbors - variables that share any timeslot
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
    
    # Cache for faster lookups
    assigned_by_timeslot = {}  # timeslot -> {instructor: set(), room: set(), sections: set()}
    local_domains = {v: list(domains[v]) for v in variables}
    
    print(f"[csp] Constraint graph built - avg neighbors: {sum(len(n) for n in constraint_neighbors.values())/len(constraint_neighbors):.1f}")

    def consistent(var, val):
        """Fast consistency check using cached timeslot assignments"""
        ts = val['timeslot']
        if ts not in assigned_by_timeslot:
            return True
        
        ts_data = assigned_by_timeslot[ts]
        # Check for instructor, room, AND section conflicts
        var_sections = set(meta[var]['sections'])
        if val['instructor'] in ts_data['instructor']:
            return False
        if val['room'] in ts_data['room']:
            return False
        # Check if any section in this variable's group is already assigned at this timeslot
        if var_sections & ts_data['sections']:
            return False
        return True

    def select_unassigned_var():
        """Select variable using MRV with dynamic degree heuristic"""
        unassigned = [v for v in variables if v not in assignment]
        if not unassigned:
            return None
        
        # MRV: choose variable with smallest domain
        # Degree: break ties with most constraints on remaining variables
        def heuristic(x):
            domain_size = len(local_domains.get(x, []))
            if domain_size == 0:
                return (0, 0)  # Dead end - prioritize to fail fast
            # Count unassigned neighbors
            unassigned_neighbors = sum(1 for n in constraint_neighbors.get(x, []) 
                                    if n not in assignment)
            return (domain_size, -unassigned_neighbors)
        
        return min(unassigned, key=heuristic)
    
    def order_domain_values(var):
        """Order domain values - simplified for speed"""
        domain_vals = local_domains.get(var, [])
        
        # For small domains, return as-is
        if len(domain_vals) <= 10:
            return domain_vals
        
        # For larger domains, prioritize timeslots with fewer assignments
        # This is a fast approximation of least-constraining-value
        def timeslot_score(val):
            ts = val['timeslot']
            ts_data = assigned_by_timeslot.get(ts, {})
            # Count resources already used in this timeslot
            used_count = len(ts_data.get('instructor', set())) + len(ts_data.get('room', set()))
            return used_count
        
        # Sort by timeslot usage
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
        
        # Check if domain is empty (dead end)
        domain_vals = order_domain_values(var)
        if not domain_vals:
            return False
        
        for val in domain_vals:
            if not consistent(var, val):
                continue
            
            assignment[var] = val
            ts = val['timeslot']
            
            # Update timeslot tracking - add instructor, room, AND sections
            if ts not in assigned_by_timeslot:
                assigned_by_timeslot[ts] = {'instructor': set(), 'room': set(), 'sections': set()}
            assigned_by_timeslot[ts]['instructor'].add(val['instructor'])
            assigned_by_timeslot[ts]['room'].add(val['room'])
            # Add all sections from this variable's group to the timeslot
            for section in meta[var]['sections']:
                assigned_by_timeslot[ts]['sections'].add(section)
            
            removed = {}
            failure = False
            
            # Forward checking - prune inconsistent values from neighbor domains
            for neighbor in constraint_neighbors.get(var, []):
                if neighbor in assignment:
                    continue
                
                # Get sections for the neighbor variable
                neighbor_sections = set(meta[neighbor]['sections'])
                
                newdom = []
                for nval in local_domains.get(neighbor, []):
                    # Keep if different timeslot or no conflicts (instructor, room, or sections)
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
            
            # Restore timeslot tracking - remove instructor, room, AND sections
            assigned_by_timeslot[ts]['instructor'].discard(val['instructor'])
            assigned_by_timeslot[ts]['room'].discard(val['room'])
            for section in meta[var]['sections']:
                assigned_by_timeslot[ts]['sections'].discard(section)
            if not assigned_by_timeslot[ts]['instructor'] and not assigned_by_timeslot[ts]['room'] and not assigned_by_timeslot[ts]['sections']:
                del assigned_by_timeslot[ts]
            
            del assignment[var]
        
        return False

    print("[csp] Starting backtracking search...")
    success = backtrack()
    print(f"[csp] Search complete: backtrack_calls={backtrack_calls[0]}, max_depth={max_depth[0]}")
    
    if not success:
        return None
    return assignment



# ✅ Updated Function - handles course-group assignments and replicates to sections in each group
def assignments_to_dataframe(assign, meta=None, courses_df=None, instructors_df=None, course_to_section_groups=None):
    # Map CourseID -> CourseName if available
    course_name_map = {}
    if courses_df is not None and 'CourseID' in courses_df.columns and 'CourseName' in courses_df.columns:
        course_name_map = dict(zip(courses_df['CourseID'].astype(str), courses_df['CourseName']))

    # Map CourseID -> Year if available
    course_year_map = {}
    if courses_df is not None and 'CourseID' in courses_df.columns and 'Year' in courses_df.columns:
        course_year_map = dict(zip(courses_df['CourseID'].astype(str), courses_df['Year']))

    # Map InstructorID -> Name if available
    instructor_name_map = {}
    if instructors_df is not None:
        if 'InstructorID' in instructors_df.columns and 'Name' in instructors_df.columns:
            instructor_name_map = dict(zip(instructors_df['InstructorID'].astype(str), instructors_df['Name']))
        elif 'Name' in instructors_df.columns:
            # If no InstructorID column, use Name as both key and value
            instructor_name_map = dict(zip(instructors_df['Name'].astype(str), instructors_df['Name']))

    rows = []
    for var, val in assign.items():
        # Parse variable: "CourseID::GroupIndex::SessionType" (e.g., "CSC111::G0::Lecture")
        parts = var.split('::')
        if len(parts) == 3 and parts[1].startswith('G'):
            course = parts[0]
            group_index = parts[1]  # e.g., "G0", "G1"
            session_type = parts[2]
            
            # Get sections for this group from meta
            sections = meta.get(var, {}).get('sections', []) if meta else []
            
            # If no sections in meta, try to get from course_to_section_groups
            if not sections and course_to_section_groups:
                try:
                    group_idx = int(group_index[1:])  # Extract number from "G0"
                    # Access the session-specific groups
                    if course in course_to_section_groups:
                        session_groups = course_to_section_groups[course].get(session_type, [])
                        if group_idx < len(session_groups):
                            sections = session_groups[group_idx]
                except (ValueError, IndexError):
                    pass
            
            # If still no sections, use a placeholder
            if not sections:
                sections = ['Unknown']
            
            # Create a row for EACH section in this group
            day, start, end = val['timeslot']
            course_name = course_name_map.get(course, course)
            course_year = course_year_map.get(course, None)
            instructor_id = val['instructor']
            instructor_name = instructor_name_map.get(str(instructor_id), instructor_id)
            
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
        else:
            # Old format or unexpected format - try to handle gracefully
            print(f"Warning: Unexpected variable format: {var}")
    
    return pd.DataFrame(rows)



def generate_timetable_from_uploads(upload_dir):
    courses_df, instructors_df, rooms_df, timeslots_df, sections_df = load_csvs(upload_dir)
    variables, domains, meta, course_to_section_groups = build_domains(courses_df, instructors_df, rooms_df, timeslots_df, sections_df)
    assign = forward_checking_search(variables, domains, meta)
    if assign is None:
        total_vars = len(variables)
        zero_domain = [v for v in variables if not domains.get(v)]
        domain_sizes = sorted([(v, len(domains.get(v, []))) for v in variables], key=lambda x: x[1])
        sample = {}
        for v, sz in domain_sizes[:10]:
            sample[v] = domains.get(v, [])[:5]
        diag_lines = []
        diag_lines.append(f"No valid timetable found. variables={total_vars}, zero_domain_count={len(zero_domain)}")
        if zero_domain:
            diag_lines.append("Variables with empty domain (first 20): " + ", ".join(zero_domain[:20]))
            for v in zero_domain[:10]:
                reasons = meta.get(v, {}).get('rejection_reasons', {})
                if reasons:
                    diag_lines.append(f"  {v} rejection_reasons: " + ", ".join([f"{k}={c}" for k, c in reasons.items()]))
                fb = meta.get(v, {}).get('fallbacks', [])
                if fb:
                    diag_lines.append(f"  {v} fallbacks_used: " + ", ".join(fb))
        diag_lines.append("Smallest domain sizes (var:size): " + ", ".join([f"{v}:{s}" for v, s in domain_sizes[:20]]))
        diag_lines.append("Sample domains (up to 5 values each) for smallest-domain vars:")
        for v, vals in sample.items():
            diag_lines.append(f"  {v} -> {vals}")
        diag_lines.append("Fallbacks used (smallest-domain vars):")
        for v, s in domain_sizes[:10]:
            fb = meta.get(v, {}).get('fallbacks', [])
            if fb:
                diag_lines.append(f"  {v}: " + ", ".join(fb))
        try:
            variables2, domains2, meta2, course_to_section_groups2 = build_domains(courses_df, instructors_df, rooms_df, timeslots_df, sections_df, force_permissive=True)
            assign2 = forward_checking_search(variables2, domains2, meta2)
            if assign2 is not None:
                print('[csp] Notice: strict generation failed; permissive generation succeeded')
                return assignments_to_dataframe(assign2, meta=meta2, courses_df=courses_df, instructors_df=instructors_df, course_to_section_groups=course_to_section_groups2)
            else:
                diag_lines.append('\nAttempted permissive generation (ignore qualifications and room-type) but it also failed.')
        except Exception as e:
            diag_lines.append(f"\nAttempted permissive generation and it raised an error: {e}")

        diag = "\n".join(diag_lines)
        raise RuntimeError(diag)

    df = assignments_to_dataframe(assign, meta=meta, courses_df=courses_df, instructors_df=instructors_df, course_to_section_groups=course_to_section_groups)
    return df
