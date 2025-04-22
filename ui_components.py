# ui_components.py
import streamlit as st
from datetime import datetime, timedelta
import math

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
        
        # Return the time difference allowing for negative values (indicating next day)
        minutes_diff = sample_time - dose_time
        return minutes_diff / 60.0
    
    @staticmethod
    def display_results(pk_results, level_results, dose_recommendation):
        """Display results in a standardized format."""
        st.markdown("### 📊 Calculated PK Parameters")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.markdown(f"""
        **Ke (hr⁻¹)**  
        # {pk_results['ke']:.4f}
        """)
        
        col2.markdown(f"""
        **t½ (hr)**  
        # {pk_results['t_half']:.2f}
        """)
        
        col3.markdown(f"""
        **Vd (L)**  
        # {pk_results['vd']:.2f}
        """)
        
        col4.markdown(f"""
        **CL (L/hr)**  
        # {pk_results['cl']:.2f}
        """)
        
        st.markdown("### 🎯 Predicted Levels")
        if 'auc' in level_results:
            col1, col2, col3 = st.columns(3)
            
            col1.markdown(f"""
            **Peak (mg/L)**  
            # {level_results['peak']:.1f}
            """)
            
            col2.markdown(f"""
            **Trough (mg/L)**  
            # {level_results['trough']:.1f}
            """)
            
            col3.markdown(f"""
            **AUC₂₄ (mg·hr/L)**  
            # {level_results['auc']:.0f}
            """)
        else:
            col1, col2 = st.columns(2)
            
            col1.markdown(f"""
            **Peak (mg/L)**  
            # {level_results['peak']:.1f}
            """)
            
            col2.markdown(f"""
            **Trough (mg/L)**  
            # {level_results['trough']:.1f}
            """)
        
        if dose_recommendation:
            st.markdown("### 💡 Recommendation")
            st.success(dose_recommendation)
    
    @staticmethod
    def generate_report(drug, regimen, patient_data, pk_params, predicted_levels, recommendation, interpretation=None):
        """Generate a printable report with all calculation details"""
        report = f"""
# {drug} TDM Report

## Patient Information
- Patient ID: {patient_data['patient_id']}
- Ward: {patient_data['ward']}
- Age: {patient_data['age']} years
- Gender: {patient_data['gender']}
- Weight: {patient_data['weight']} kg
- Height: {patient_data['height']} cm
- Serum Creatinine: {patient_data['serum_cr']} µmol/L
- CrCl: {patient_data['crcl']:.1f} mL/min
- Renal Function: {patient_data['renal_function']}
- Diagnosis: {patient_data.get('diagnosis', 'N/A')}
- Current Regimen: {patient_data.get('current_regimen', 'N/A')}

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
        
        report += f"\n## Clinical Notes\n{patient_data.get('notes', 'N/A')}\n"
        
        report += f"\n---\nReport generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
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
