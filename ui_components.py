# ui_components.py
import streamlit as st
from datetime import datetime, timedelta
import math

class UIComponents:
    @staticmethod
    def create_patient_sidebar():
        """Create a standardized patient sidebar with improved layout and validation."""
        st.sidebar.title("📊 Navigation")
        page = st.sidebar.radio(
            "Select Module",
            ["Aminoglycoside: Initial Dose", 
             "Aminoglycoside: Conventional Dosing (C1/C2)", 
             "Vancomycin AUC-based Dosing"]
        )
        
        st.sidebar.title("🩺 Patient Demographics")
        patient_data = {}
        
        # Patient identification
        col1, col2 = st.sidebar.columns(2)
        with col1:
            patient_data['patient_id'] = st.text_input("Patient ID", value="N/A")
        with col2:
            patient_data['ward'] = st.text_input("Ward", value="N/A")
        
        # Basic demographics
        patient_data['gender'] = st.sidebar.selectbox("Gender", ["Male", "Female"])
        patient_data['age'] = st.sidebar.number_input("Age (years)", 0, 120, 65)
        
        # Anthropometrics
        col1, col2 = st.sidebar.columns(2)
        with col1:
            patient_data['height'] = st.number_input("Height (cm)", 50, 250, 165)
        with col2:
            patient_data['weight'] = st.number_input("Weight (kg)", 1.0, 300.0, 70.0, step=0.1)
        
        # Renal function
        patient_data['serum_cr'] = st.sidebar.number_input(
            "Serum Creatinine (µmol/L)", 
            10.0, 2000.0, 90.0,
            help="Typical range: 60-120 µmol/L for adults"
        )
        
        # Calculate CrCl
        crcl_result = UIComponents.calculate_crcl(patient_data)
        patient_data['crcl'] = crcl_result['value']
        patient_data['renal_function'] = crcl_result['status']
        
        with st.sidebar.expander("Creatinine Clearance", expanded=True):
            # Show appropriate color based on renal function
            if patient_data['crcl'] >= 60:
                st.success(f"CrCl: {crcl_result['value']:.1f} mL/min")
            elif patient_data['crcl'] >= 30:
                st.warning(f"CrCl: {crcl_result['value']:.1f} mL/min")
            else:
                st.error(f"CrCl: {crcl_result['value']:.1f} mL/min")
                
            st.info(f"Renal Function: {crcl_result['status']}")
        
        st.sidebar.title("🩺 Clinical Information")
        patient_data['diagnosis'] = st.sidebar.text_input(
            "Diagnosis/Indication", 
            placeholder="e.g., Pneumonia, Bacteremia",
            help="This will help refine clinical recommendations"
        )
        patient_data['notes'] = st.sidebar.text_area("Clinical Notes", value="No known allergies.")
        
        # Add current regimen for context
        patient_data['current_regimen'] = st.sidebar.text_input(
            "Current Antimicrobial Regimen",
            placeholder="e.g., Vancomycin 1g q12h",
            help="Current antimicrobial therapy (optional)"
        )
        
        return page, patient_data
    
    @staticmethod
    def calculate_crcl(patient_data):
        """Calculate creatinine clearance using Cockcroft-Gault with improved validation."""
        age = patient_data['age']
        weight = patient_data['weight']
        scr = patient_data['serum_cr']
        gender = patient_data['gender']
        
        if age > 0 and weight > 0 and scr > 0:
            factor = (140 - age) * weight
            multiplier = 1.23 if gender == "Male" else 1.04
            crcl = (factor * multiplier) / scr
            crcl = max(0, min(200, crcl))  # Cap at reasonable limits
            
            if crcl >= 90: status = "Normal (≥90 mL/min)"
            elif crcl >= 60: status = "Mild Impairment (60-89 mL/min)"
            elif crcl >= 30: status = "Moderate Impairment (30-59 mL/min)"
            elif crcl >= 15: status = "Severe Impairment (15-29 mL/min)"
            else: status = "Kidney Failure (<15 mL/min)"
            
            return {"value": crcl, "status": status}
        
        return {"value": 0, "status": "N/A"}
    
    @staticmethod
    def create_time_input(label, default_hour=12, default_minute=0, key=None, help_text=None):
        """Create a clock time input with improved formatting and help text."""
        col1, col2 = st.columns(2)
        with col1:
            hour = st.number_input(
                f"{label} - Hour (0-23)", 
                min_value=0, 
                max_value=23, 
                value=default_hour, 
                key=f"{key}_hour" if key else None,
                help=help_text
            )
        with col2:
            minute = st.number_input(
                f"{label} - Minute (0-59)", 
                min_value=0, 
                max_value=59, 
                value=default_minute, 
                key=f"{key}_minute" if key else None
            )
        
        # Return time string for display in 12-hour format
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        am_pm = "AM" if hour < 12 else "PM"
        display_time = f"{display_hour}:{minute:02d} {am_pm}"
        
        return hour, minute, display_time
    
    @staticmethod
    def calculate_time_difference(dose_hour, dose_minute, sample_hour, sample_minute):
        """
        Calculate time difference in hours between dose and sample times
        with improved handling of cross-day scenarios.
        """
        dose_time = dose_hour * 60 + dose_minute
        sample_time = sample_hour * 60 + sample_minute
        
        # Calculate minutes difference
        minutes_diff = sample_time - dose_time
        
        # Return the time difference in hours
        return minutes_diff / 60.0
    
    @staticmethod
    def display_results(pk_results, level_results, dose_recommendation):
        """Display results in a standardized format with improved visual indicators."""
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
        """Generate a printable report with all calculation details and improved formatting."""
        # Add timestamp and header
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Basic header formatting
        report = f"""
# {drug} TDM Report - {current_time}

## Patient Information
- **Patient ID**: {patient_data['patient_id']}
- **Ward**: {patient_data['ward']}
- **Age**: {patient_data['age']} years
- **Gender**: {patient_data['gender']}
- **Weight**: {patient_data['weight']} kg
- **Height**: {patient_data['height']} cm
- **Serum Creatinine**: {patient_data['serum_cr']} µmol/L
- **CrCl**: {patient_data['crcl']:.1f} mL/min
- **Renal Function**: {patient_data['renal_function']}
- **Diagnosis**: {patient_data.get('diagnosis', 'N/A')}
- **Current Regimen**: {patient_data.get('current_regimen', 'N/A')}

## Dosing Information
- **Drug**: {drug}
- **Regimen**: {regimen}

## Calculated Parameters
- **Elimination Rate Constant (ke)**: {pk_params['ke']:.4f} /hr
- **Half-life**: {pk_params['t_half']:.1f} hr
- **Volume of Distribution (Vd)**: {pk_params['vd']:.2f} L
- **Clearance**: {pk_params['cl']:.2f} L/hr

## Predicted Levels
- **Predicted Peak**: {predicted_levels['peak']:.1f} mg/L
- **Predicted Trough**: {predicted_levels['trough']:.1f} mg/L
"""
        
        if 'auc' in predicted_levels:
            report += f"- **Predicted AUC₂₄**: {predicted_levels['auc']:.0f} mg·hr/L\n"
        
        report += f"\n## Recommendation\n{recommendation}\n"
        
        if interpretation:
            # Clean up interpretation for plain text
            plain_interpretation = interpretation.replace('✅', '[OK]')
            plain_interpretation = plain_interpretation.replace('❌', '[BELOW]')
            plain_interpretation = plain_interpretation.replace('⚠️', '[ABOVE]')
            plain_interpretation = plain_interpretation.replace('🚨', '[CRITICAL]')
            plain_interpretation = plain_interpretation.replace('👁️', '[MONITOR]')
            plain_interpretation = plain_interpretation.replace('📈', '[INCREASE]')
            plain_interpretation = plain_interpretation.replace('📉', '[DECREASE]')
            plain_interpretation = plain_interpretation.replace('📅', '[SCHEDULE]')
            
            report += f"\n## Clinical Interpretation\n{plain_interpretation}\n"
        
        report += f"\n## Clinical Notes\n{patient_data.get('notes', 'N/A')}\n"
        
        report += f"\n---\nReport generated on: {current_time}\n"
        report += "This report is provided for clinical support purposes only. Always use clinical judgment when interpreting results."
        
        return report
    
    @staticmethod
    def create_print_button(report_content):
        """Create a button to download the report as a text file with improved naming."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        st.download_button(
            label="📄 Download Report",
            data=report_content,
            file_name=f"tdm_report_{timestamp}.txt",
            mime="text/plain",
            help="Download a printable version of this report"
        )
        
    @staticmethod
    def create_help_expander(title, content):
        """Create an expander with help information."""
        with st.expander(f"ℹ️ {title}"):
            st.markdown(content)
