# ui_components.py
import streamlit as st
from datetime import datetime, time, timedelta

class UIComponents:
    @staticmethod
    def create_patient_sidebar():
        """Create a standardized patient sidebar."""
        st.sidebar.title("📊 Navigation")
        page = st.sidebar.radio(
            "Select Module",
            ["Aminoglycoside: Initial Dose", 
             "Aminoglycoside: Conventional Dosing (C1/C2)", 
             "Vancomycin AUC-based Dosing"]
        )
        
        st.sidebar.title("🩺 Patient Demographics")
        patient_data = {}
        patient_data['patient_id'] = st.sidebar.text_input("Patient ID", value="N/A")
        patient_data['ward'] = st.sidebar.text_input("Ward", value="N/A")
        patient_data['gender'] = st.sidebar.selectbox("Gender", ["Male", "Female"])
        patient_data['age'] = st.sidebar.number_input("Age (years)", 0, 120, 65)
        patient_data['height'] = st.sidebar.number_input("Height (cm)", 50, 250, 165)
        patient_data['weight'] = st.sidebar.number_input("Weight (kg)", 1.0, 300.0, 70.0, step=0.1)
        patient_data['serum_cr'] = st.sidebar.number_input("Serum Creatinine (µmol/L)", 10.0, 2000.0, 90.0)
        
        # Calculate CrCl
        crcl_result = UIComponents.calculate_crcl(patient_data)
        patient_data['crcl'] = crcl_result['value']
        patient_data['renal_function'] = crcl_result['status']
        
        with st.sidebar.expander("Creatinine Clearance", expanded=True):
            st.success(f"CrCl: {crcl_result['value']:.1f} mL/min")
            st.info(f"Renal Function: {crcl_result['status']}")
        
        st.sidebar.title("🩺 Clinical Information")
        patient_data['diagnosis'] = st.sidebar.text_input("Diagnosis/Indication", placeholder="e.g., Pneumonia")
        patient_data['current_regimen'] = st.sidebar.text_area("Current Dosing Regimen", value="1g IV q12h")
        patient_data['notes'] = st.sidebar.text_area("Clinical Notes", value="No known allergies.")
        
        return page, patient_data
    
    @staticmethod
    def calculate_crcl(patient_data):
        """Calculate creatinine clearance using Cockcroft-Gault."""
        age = patient_data['age']
        weight = patient_data['weight']
        scr = patient_data['serum_cr']
        gender = patient_data['gender']
        
        if age > 0 and weight > 0 and scr > 0:
            factor = (140 - age) * weight
            multiplier = 1.23 if gender == "Male" else 1.04
            crcl = (factor * multiplier) / scr
            crcl = max(0, crcl)
            
            if crcl >= 90: status = "Normal (≥90)"
            elif crcl >= 60: status = "Mild Impairment (60-89)"
            elif crcl >= 30: status = "Moderate Impairment (30-59)"
            elif crcl >= 15: status = "Severe Impairment (15-29)"
            else: status = "Kidney Failure (<15)"
            
            return {"value": crcl, "status": status}
        
        return {"value": 0, "status": "N/A"}
    
    @staticmethod
    def create_datetime_input(label, default_hour=12, default_minute=0):
        """Create a standardized datetime input."""
        default_date = datetime.now().date()
        default_time = time(default_hour, default_minute)
        return st.datetime_input(
            label, 
            value=datetime.combine(default_date, default_time),
            step=timedelta(minutes=15)
        )
    
    @staticmethod
    def display_results(pk_results, level_results, dose_recommendation):
        """Display results in a standardized format."""
        st.markdown("### Calculated Parameters")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ke (hr⁻¹)", f"{pk_results['ke']:.4f}")
        col2.metric("t½ (hr)", f"{pk_results['t_half']:.2f}")
        col3.metric("Vd (L)", f"{pk_results['vd']:.2f}")
        col4.metric("CL (L/hr)", f"{pk_results['cl']:.2f}")
        
        st.markdown("### Predicted Levels")
        col1, col2 = st.columns(2)
        col1.metric("Peak", f"{level_results['peak']:.1f} mg/L")
        col2.metric("Trough", f"{level_results['trough']:.1f} mg/L")
        
        st.markdown("### Recommendation")
        st.success(dose_recommendation)
