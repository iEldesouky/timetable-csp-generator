# 🎓 Automated Timetable Generator using Constraint Satisfaction Problems

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

An Intelligent Systems project that formulates university timetable generation as a **Constraint Satisfaction Problem (CSP)** and solves it using advanced backtracking algorithms with optimization techniques.

## 📊 Project Overview

This system automatically generates optimal university timetables by modeling the scheduling problem as a CSP, where:
- **Variables** represent course sections needing scheduling
- **Domains** consist of all possible (time, room, instructor) combinations  
- **Constraints** enforce scheduling rules and preferences

The solver employs **AI search strategies** including Minimum Remaining Values (MRV), Least Constraining Value (LCV), and forward checking to efficiently find feasible schedules.

## 🚀 Features

### Core CSP Implementation
- **Complete CSP Formulation** with variables, domains, and constraints
- **Backtracking Search** with intelligent pruning
- **Optimization Heuristics**: MRV, LCV, Degree Heuristic
- **Constraint Propagation**: Forward checking and arc consistency
- **Hard & Soft Constraints** handling

### User Interface
- **Streamlit Web Application** for easy interaction
- **Real-time Data Upload** and validation
- **Visual Timetable Display** in multiple views
- **Performance Analytics** and metrics
- **Export Capabilities** to CSV format

### Data Management
- **Dynamic Dataset Support** (CSV files)
- **Data Validation** and consistency checks
- **Expandable Architecture** for new constraints

