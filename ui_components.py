# ui_components.py
import streamlit as st
from datetime import datetime, timedelta
import math

class UIComponents:
    @staticmethod
    def create_time_input(label, default_hour=12, default_minute=0, key=None):
        """Create a clock time input (just hour and minute)"""
        col1, col2 = st.columns(2)
        with col1:
            hour = st.number_input(f"{label} - Hour (0-23)", min_value=0, max_value=23, value=default_hour, key=f"{key}_hour" if key else None)
        with col2:
            minute = st.number_input(f"{label} - Minute (0-59)", min_value=0, max_value=59, value=default_minute, key=f"{key}_minute" if key else None)
        
        # Return time string for display
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        am_pm = "AM" if hour < 12 else "PM"
        display_time = f"{display_hour}:{minute:02d} {am_pm}"
        
        return hour, minute, display_time
    
    @staticmethod
    def calculate_time_difference(dose_hour, dose_minute, sample_hour, sample_minute):
        """Calculate time difference in hours between dose and sample times"""
        dose_time = dose_hour * 60 + dose_minute
        sample_time = sample_hour * 60 + sample_minute
        
        # Handle case where sample crosses midnight
        if sample_time < dose_time:
            # Sample is on the next day
            minutes_diff = (24 * 60 - dose_time) + sample_time
        else:
            minutes_diff = sample_time - dose_time
        
        return minutes_diff / 60.0
    
    @staticmethod
    def display_results(pk_params, predicted_levels, recommendation):
        """Display PK parameters and predicted levels in a consistent format"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Calculated Parameters")
            st.write(f"**Elimination Rate Constant (ke):** {pk_params['ke']:.4f} /hr")
            st.write(f"**Half-life:** {pk_params['t_half']:.1f} hr")
            st.write(f"**Volume of Distribution (Vd):** {pk_params['vd']:.2f} L")
            st.write(f"**Clearance:** {pk_params['cl']:.2f} L/hr")
        
        with col2:
            st.markdown("### Predicted Levels")
            st.write(f"**Predicted Peak:** {predicted_levels['peak']:.1f} mg/L")
            st.write(f"**Predicted Trough:** {predicted_levels['trough']:.1f} mg/L")
            if 'auc' in predicted_levels:
                st.write(f"**Predicted AUC₂₄:** {predicted_levels['auc']:.0f} mg·hr/L")
        
        if recommendation:
            st.success(recommendation)
    
    @staticmethod
    def generate_report(drug, regimen, patient_data, pk_params, predicted_levels, recommendation, interpretation=None):
        """Generate a printable report with all calculation details"""
        report = f"""
# {drug} TDM Report

## Patient Information
- Weight: {patient_data['weight']} kg
- CrCl: {patient_data['crcl']} mL/min

## Dosing Information
- Drug: {drug}
- Regimen: {regimen}

## Calculated Parameters
- Elimination Rate Constant (ke): {pk_params['ke']:.4f} /hr
- Half-life: {pk_params['t_half']:.1f} hr
- Volume of Distribution (Vd): {pk_params['vd']:.2f} L
- Clearance: {pk_params['cl']:.2f} L/hr

## Predicted Levels
- Predicted Peak: {predicted_levels['peak']:.1f} mg/L
- Predicted Trough: {predicted_levels['trough']:.1f} mg/L
"""
        
        if 'auc' in predicted_levels:
            report += f"- Predicted AUC₂₄: {predicted_levels['auc']:.0f} mg·hr/L\n"
        
        report += f"\n## Recommendation\n{recommendation}\n"
        
        if interpretation:
            report += f"\n## Clinical Interpretation\n{interpretation}\n"
        
        return report
    
    @staticmethod
    def create_print_button(report_content):
        """Create a button to download the report as a text file"""
        st.download_button(
            label="📄 Download Report",
            data=report_content,
            file_name=f"tdm_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )
    
    @staticmethod
    def create_patient_sidebar():
        """Create sidebar with patient information inputs"""
        st.sidebar.header("Patient Information")
        
        weight = st.sidebar.number_input("Weight (kg)", min_value=10.0, max_value=300.0, value=70.0)
        crcl = st.sidebar.number_input("Creatinine Clearance (mL/min)", min_value=5.0, max_value=200.0, value=80.0)
        
        st.sidebar.markdown("---")
        
        # Navigation
        pages = [
            "Aminoglycoside: Initial Dose",
            "Aminoglycoside: Conventional Dosing (C1/C2)",
            "Vancomycin AUC-based Dosing"
        ]
        page = st.sidebar.radio("Select Calculator", pages)
        
        return page, {"weight": weight, "crcl": crcl}
