# CSIT Timetable Generator - Streamlit Edition

An intelligent automatic timetable generator using Constraint Satisfaction Problem (CSP) algorithms. Built with Streamlit for an intuitive web interface.

## 🌟 Features

- **Advanced CSP Algorithm**: Forward checking with backtracking and MRV heuristic
- **Section Conflict Prevention**: No student double-booking at same timeslot
- **Strict Role-Based Assignment**: Professors teach Lectures, Assistant Professors teach Labs/TUTs
- **Duration-Aware Scheduling**: 90-min for Lectures/Labs, 45/90-min for TUTs
- **Smart Section Grouping**: Lectures (3-4 sections), Labs (2 sections), TUTs (individual)
- **Interactive Streamlit UI**: Real-time filtering, statistics, and CSV export

## 🚀 Quick Start

### Installation

```bash
pip install streamlit pandas plotly
```

### Run Application

```bash
streamlit run app.py
```

Opens automatically at `http://localhost:8501`

## 📁 Project Structure

```
timetable-csp-project/
├── app.py           # Streamlit UI (400 lines)
├── csp_solver.py    # CSP algorithm (300 lines)
└── requirements.txt # Dependencies
```

**Simple**: Just 2 files, ~700 lines total

## 📊 Required CSV Files

### 1. courses.csv
```csv
CourseID,CourseName,Credits,Type,Year,Shared
CSC111,Programming,3,Lecture and Lab,1,No
MTH111,Mathematics,3,Lecture and TUT,1,No
PHY113,Physics,3,Lecture and Lab and TUT,1,No
```

**Type options:**
- `Lecture` - 90 min
- `Lecture and Lab` - Both 90 min
- `Lecture and TUT` - Both 90 min
- `Lecture and Lab and TUT` - Lecture 90min, Lab 90min, TUT 45min

### 2. instructors.csv
```csv
InstructorID,Name,Role,PreferredSlots,QualifiedCourses
PROF01,Dr. Smith,Professor,Not on Tuesday,"CSC111,MTH111"
AP01,Eng. Ahmed,Assistant Professor,Not on Sunday,"CSC111,PHY113"
```

**⚠️ Critical:**
- `Role` must be "Professor" or "Assistant Professor"
- Professors → Lectures ONLY
- Assistant Professors → Labs/TUTs ONLY

### 3. rooms.csv
```csv
RoomID,Type,Capacity
R101,Lecture,150
L11,Lab,35
T1,TUT,35
```

**Types:** `Lecture`, `Lab`, `TUT` (must match exactly)

### 4. timeslots.csv
```csv
Day,StartTime,EndTime,Duration
Sunday,9:00 AM,10:30 AM,90
Sunday,9:00 AM,9:45 AM,45
```

**⚠️ Duration required:** 45 or 90 minutes

### 5. sections.csv
```csv
SectionID,Capacity
1/1,30
1/2,30
3/CNC/1,30
4/AID/1,30
```

**Format:**
- Years 1-2: `year/number` (e.g., "1/5")
- Years 3-4: `year/department/number` (e.g., "3/CNC/1")

## 🎯 How It Works

1. **Load Data** → Upload 5 CSV files
2. **Assign Courses to Sections** → Based on year/department matching
3. **Group Sections** → TUT (1), Lab (2), Lecture (3-4)
4. **Build Domains** → Pre-filter valid (timeslot, room, instructor) combinations
5. **Solve CSP** → Forward checking with MRV heuristic
6. **Format Results** → Export to CSV with filtering options

## 🔧 Algorithm Details

### Constraints (Priority Order)

**Hard (Never Violated):**
- No instructor double-booking
- No room double-booking
- **No section double-booking** ✅
- Role-based assignment (Professor→Lecture, Assistant→Lab/TUT)
- Duration matching (45/90 min)

**Medium (Fallback in Permissive Mode):**
- Instructor qualifications
- Room type matching (Lecture→R, Lab→L, TUT→T)

**Soft (Preferences):**
- Instructor day preferences

### Performance

| Courses | Time | Backtracks |
|---------|------|------------|
| 50 | 10-20s | 500-2000 |
| 100 | 30-60s | 2000-8000 |
| 150 | 60-120s | 5000-15000 |

## 🌐 Using the Interface

### Page 1: Upload & Generate
1. Upload 5 CSV files
2. Set timeout (default: 120s)
3. Enable permissive mode if needed
4. Click "Generate"

### Page 2: View Timetable
- Filter by: Year, Day, Session Type, Room
- View by: Day, Room, Instructor, Year
- Export to CSV

### Page 3: Statistics
- Generation metrics
- Session distribution
- Room utilization
- Instructor workload

## 🔍 Troubleshooting

### "No valid timetable found"

**Check:**
1. ✅ Enough Professors for Lectures
2. ✅ Enough Assistant Professors for Labs/TUTs
3. ✅ Enough rooms of each type (R, L, T)
4. ✅ Duration column exists (45 and 90)
5. ✅ Section IDs match year/department format

**Solutions:**
- Enable permissive mode
- Increase timeout
- Add more instructors/rooms
- Check role assignments

### "Empty domains"

**Causes:**
- No instructors with correct role
- No rooms with correct type
- No timeslots with correct duration
- Section format mismatch

### Generation too slow (>120s)

**Solutions:**
- Increase timeout to 180-300s
- Add more resources (instructors/rooms)
- Reduce sections per course

## 📈 Output Format

| Column | Description |
|--------|-------------|
| CourseID | Course code |
| CourseName | Full name |
| CourseYear | 1, 2, 3, or 4 |
| SectionID | Section identifier |
| SessionType | Lecture, Lab, or TUT |
| Day | Day of week |
| StartTime | Start time |
| EndTime | End time |
| Room | Room ID |
| Instructor | Instructor name |

## 👨‍💻 Development

### Key Functions

**csp_solver.py:**
```python
generate_timetable(...)          # Main entry point
build_domains(...)               # Create variables & domains
forward_checking_search(...)     # Solve CSP
format_timetable_for_display(...) # Convert to DataFrame
```

### Adding Constraints

Modify `generate_vals()` in `build_domains()`:

```python
# Example: Max 4 classes per day
if instructor_day_count[instr_id][day] >= 4:
    rejection_reasons[var]['max_classes_per_day'] += 1
    continue
```

## 📝 Key Differences from Original

### Simplified Architecture
- **Before**: 6 files, ~2500 lines, complex imports
- **After**: 2 files, ~700 lines, simple structure

### Critical Fixes
1. ✅ **Section conflict prevention** - Added triple tracking (instructor, room, section)
2. ✅ **Proper duration handling** - Separate 45/90-min timeslots
3. ✅ **Pre-filtered domains** - 100-300x smaller search space
4. ✅ **Strict role enforcement** - Never allows role mismatches

### Performance
- **Old**: Domains ~160,000 values, slow generation
- **New**: Domains ~50-500 values, 10-60s generation

## 🎉 Success Indicators

When working correctly:
- ✅ Generation < 120 seconds
- ✅ Completion rate > 95%
- ✅ No section conflicts
- ✅ Correct role assignments
- ✅ Proper duration matching

---

**Built with proven CSP algorithms • Streamlit UI • Section conflict prevention included**