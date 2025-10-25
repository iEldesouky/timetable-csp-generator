# [file name]: performance_analysis.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, List

class PerformanceAnalyzer:
    """
    Comprehensive performance analysis for timetable generation
    """
    
    @staticmethod
    def analyze_solution_performance(solution: Dict, csp, solver_metrics: Dict, data_loader) -> Dict:
        """Comprehensive performance analysis"""
        analysis = {}
        
        # Basic metrics
        analysis['basic'] = PerformanceAnalyzer._basic_metrics(solution, csp, solver_metrics)
        
        # Constraint analysis
        analysis['constraints'] = PerformanceAnalyzer._constraint_analysis(solution, csp, data_loader)
        
        # Resource utilization
        analysis['utilization'] = PerformanceAnalyzer._resource_utilization(solution, data_loader)
        
        # Search performance
        analysis['search'] = PerformanceAnalyzer._search_performance(solver_metrics)
        
        return analysis
    
    @staticmethod
    def _basic_metrics(solution: Dict, csp, solver_metrics: Dict) -> Dict:
        """Calculate basic performance metrics"""
        total_variables = len(csp.variables)
        assigned_variables = len(solution) if solution else 0
        
        return {
            'completion_rate': (assigned_variables / total_variables * 100) if total_variables > 0 else 0,
            'total_variables': total_variables,
            'assigned_variables': assigned_variables,
            'search_time_seconds': solver_metrics.get('search_time', 0),
            'backtracks_per_variable': solver_metrics.get('backtrack_count', 0) / total_variables if total_variables > 0 else 0,
            'constraint_checks_per_second': solver_metrics.get('constraint_checks', 0) / solver_metrics.get('search_time', 1) if solver_metrics.get('search_time', 0) > 0 else 0
        }
    
    @staticmethod
    def _constraint_analysis(solution: Dict, csp, data_loader) -> Dict:
        """Analyze constraint satisfaction"""
        if not solution:
            return {}
        
        # Count session types
        session_counts = {'Lecture': 0, 'Lab': 0, 'TUT': 0}
        room_type_matches = 0
        instructor_qualifications = 0
        
        for var_id, assignment in solution.items():
            # Parse variable
            parts = var_id.split('::')
            if len(parts) == 3:
                session_type = parts[2]
                session_counts[session_type] = session_counts.get(session_type, 0) + 1
            
            # Check room type matching
            room_id = assignment['room']
            room_data = data_loader.rooms_df[data_loader.rooms_df['RoomID'] == room_id]
            if not room_data.empty:
                room_type = room_data.iloc[0]['Type']
                if (session_type == 'Lecture' and room_type == 'Lecture') or \
                   (session_type == 'Lab' and room_type == 'Lab') or \
                   (session_type == 'TUT' and room_type == 'TUT'):
                    room_type_matches += 1
        
        return {
            'session_distribution': session_counts,
            'room_type_match_rate': (room_type_matches / len(solution) * 100) if solution else 0,
            'total_constraints_checked': len(solution) * 3  # instructor, room, sections
        }
    
    @staticmethod
    def _resource_utilization(solution: Dict, data_loader) -> Dict:
        """Analyze resource utilization"""
        if not solution:
            return {}
        
        # Instructor workload
        instructor_workload = {}
        room_usage = {}
        timeslot_usage = {}
        
        for assignment in solution.values():
            # Instructor workload
            instructor = assignment['instructor']
            instructor_workload[instructor] = instructor_workload.get(instructor, 0) + 1
            
            # Room usage
            room = assignment['room']
            room_usage[room] = room_usage.get(room, 0) + 1
            
            # Timeslot usage
            timeslot = assignment['timeslot']
            timeslot_usage[timeslot] = timeslot_usage.get(timeslot, 0) + 1
        
        return {
            'instructor_workload': instructor_workload,
            'room_utilization': room_usage,
            'timeslot_distribution': timeslot_usage,
            'avg_instructor_load': sum(instructor_workload.values()) / len(instructor_workload) if instructor_workload else 0,
            'avg_room_utilization': sum(room_usage.values()) / len(room_usage) if room_usage else 0
        }
    
    @staticmethod
    def _search_performance(solver_metrics: Dict) -> Dict:
        """Analyze search algorithm performance"""
        return {
            'backtrack_efficiency': solver_metrics.get('backtrack_count', 0) / solver_metrics.get('constraint_checks', 1),
            'search_depth_efficiency': solver_metrics.get('max_depth', 0) / solver_metrics.get('backtrack_calls', 1),
            'variables_per_second': solver_metrics.get('variables_assigned', 0) / solver_metrics.get('search_time', 1) if solver_metrics.get('search_time', 0) > 0 else 0,
            'constraint_checks_per_variable': solver_metrics.get('constraint_checks', 0) / solver_metrics.get('variables_assigned', 1) if solver_metrics.get('variables_assigned', 0) > 0 else 0
        }
    
    @staticmethod
    def create_performance_dashboard(analysis: Dict):
        """Create comprehensive performance dashboard"""
        st.header("📊 Performance Analysis Dashboard")
        
        # Basic Metrics
        st.subheader("🎯 Basic Performance")
        basic = analysis.get('basic', {})
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Completion Rate", f"{basic.get('completion_rate', 0):.1f}%")
        with col2:
            st.metric("Search Time", f"{basic.get('search_time_seconds', 0):.2f}s")
        with col3:
            st.metric("Backtracks/Variable", f"{basic.get('backtracks_per_variable', 0):.1f}")
        with col4:
            st.metric("Constraint Checks/s", f"{basic.get('constraint_checks_per_second', 0):.0f}")
        
        # Constraint Analysis
        st.subheader("🔗 Constraint Satisfaction")
        constraints = analysis.get('constraints', {})
        col1, col2 = st.columns(2)
        
        with col1:
            session_dist = constraints.get('session_distribution', {})
            if session_dist:
                fig = px.pie(values=list(session_dist.values()), names=list(session_dist.keys()),
                           title="Session Type Distribution")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            metrics = [
                ("Room Type Match", f"{constraints.get('room_type_match_rate', 0):.1f}%"),
                ("Total Constraints", constraints.get('total_constraints_checked', 0))
            ]
            for name, value in metrics:
                st.metric(name, value)
        
        # Resource Utilization
        st.subheader("📈 Resource Utilization")
        utilization = analysis.get('utilization', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Instructor workload distribution
            instructor_load = utilization.get('instructor_workload', {})
            if instructor_load:
                fig = px.histogram(x=list(instructor_load.values()), 
                                 title="Instructor Workload Distribution",
                                 labels={'x': 'Number of Classes', 'y': 'Count'})
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Room utilization
            room_util = utilization.get('room_utilization', {})
            if room_util:
                fig = px.bar(x=list(room_util.keys())[:10], y=list(room_util.values())[:10],
                           title="Top 10 Room Utilization",
                           labels={'x': 'Room', 'y': 'Classes'})
                st.plotly_chart(fig, use_container_width=True)
        
        # Search Performance
        st.subheader("⚡ Search Algorithm Performance")
        search = analysis.get('search', {})
        
        metrics_data = {
            'Backtrack Efficiency': search.get('backtrack_efficiency', 0),
            'Search Depth Efficiency': search.get('search_depth_efficiency', 0),
            'Variables per Second': search.get('variables_per_second', 0),
            'Constraints per Variable': search.get('constraint_checks_per_variable', 0)
        }
        
        fig = px.bar(x=list(metrics_data.keys()), y=list(metrics_data.values()),
                   title="Search Performance Metrics")
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed metrics table
        st.subheader("📋 Detailed Metrics")
        detailed_data = []
        for category, metrics in analysis.items():
            for metric, value in metrics.items():
                if isinstance(value, dict):
                    for sub_metric, sub_value in value.items():
                        detailed_data.append({
                            'Category': category,
                            'Metric': f"{metric}.{sub_metric}",
                            'Value': sub_value
                        })
                else:
                    detailed_data.append({
                        'Category': category,
                        'Metric': metric,
                        'Value': value
                    })
        
        if detailed_data:
            st.dataframe(pd.DataFrame(detailed_data), use_container_width=True)