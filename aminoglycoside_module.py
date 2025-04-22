# aminoglycoside_module.py
import streamlit as st
import math
from pk_calculations import PKCalculator
from clinical_logic import ClinicalInterpreter
from visualization import PKVisualizer
from ui_components import UIComponents
from config import DRUG_CONFIGS

class AminoglycosideModule:
    @staticmethod
    def initial_dose(patient_data):
        st.title("🧮 Aminoglycoside Initial Dose Calculator")
        
        # Drug and regimen selection
        drug = st.selectbox("Select Drug", ["Gentamicin", "Amikacin"])
        regimen_options = DRUG_CONFIGS[drug]["regimens"]
        regimen_names = {k: v["display_name"] for k, v in regimen_options.items()}
        
        selected_display_name = st.selectbox("Dosing Strategy", list(regimen_names.values()))
        regimen = next(k for k, v in regimen_names.items() if v == selected_display_name)
        
        # Display target ranges
        targets = DRUG_CONFIGS[drug]["regimens"][regimen]["targets"]
        st.info(f"Target Peak: {targets['peak']['info']} | Target Trough: {targets['trough']['info']}")
        
        # MIC input for SDD regimens
        if regimen == "SDD":
            mic = st.number_input("MIC (mg/L)", min_value=0.1, value=1.0, step=0.1)
            recommended_peak = mic * 10
            st.info(f"Based on MIC, recommended peak: ≥{recommended_peak:.1f} mg/L")
            
            # Adjust target if needed
            if recommended_peak > targets['peak']['min']:
                targets['peak']['min'] = recommended_peak
        
        # Interval and infusion duration
        default_interval = DRUG_CONFIGS[drug]["regimens"][regimen]["default_interval"]
        tau = st.number_input("Dosing Interval (hr)", min_value=4, max_value=72, value=default_interval)
        infusion_duration = st.number_input("Infusion Duration (hr)", min_value=0.5, max_value=4.0, value=1.0)
        
        # Calculate dose
        calculator = PKCalculator(drug, patient_data['weight'], patient_data['crcl'])
        dose, pk_params = calculator.calculate_dose(
            targets['peak']['min'],
            targets['trough']['max'],
            tau,
            infusion_duration
        )
        
        # Predict levels
        predicted_levels = calculator.predict_levels(dose, tau, infusion_duration)
        
        # Display results
        UIComponents.display_results(
            pk_params,
            predicted_levels,
            f"Recommended dose: {dose} mg every {tau} hours (infused over {infusion_duration} hr)"
        )
        
        # Display concentration-time curve
        PKVisualizer.display_pk_chart(
            pk_params,
            predicted_levels,
            {'tau': tau, 'infusion_duration': infusion_duration}
        )
        
        # Clinical interpretation
        if st.button("Generate Clinical Interpretation"):
            interpreter = ClinicalInterpreter(drug, regimen, targets)
            assessment, status = interpreter.assess_levels(predicted_levels)
            recommendations = interpreter.generate_recommendations(status, patient_data['crcl'])
            
            st.markdown("### Clinical Interpretation")
            st.markdown(interpreter.format_recommendations(assessment, status, recommendations))
    
    @staticmethod
    def conventional_dosing(patient_data):
        st.title("📊 Aminoglycoside Dose Adjustment")
        
        # Drug and regimen selection
        drug = st.selectbox("Select Drug", ["Gentamicin", "Amikacin"])
        regimen_options = DRUG_CONFIGS[drug]["regimens"]
        regimen_names = {k: v["display_name"] for k, v in regimen_options.items()}
        
        selected_display_name = st.selectbox("Dosing Strategy", list(regimen_names.values()))
        regimen = next(k for k, v in regimen_names.items() if v == selected_display_name)
        
        # Display target ranges
        targets = DRUG_CONFIGS[drug]["regimens"][regimen]["targets"]
        st.info(f"Target Peak: {targets['peak']['info']} | Target Trough: {targets['trough']['info']}")
        
        # Current dosing information
        col1, col2, col3 = st.columns(3)
        with col1:
            dose = st.number_input("Current Dose (mg)", min_value=10.0, value=120.0)
        with col2:
            tau = st.number_input("Current Interval (hr)", min_value=4, max_value=72, value=8)
        with col3:
            infusion_duration = st.number_input("Infusion Duration (hr)", value=1.0)
        
        # Dose timing
        dose_time = UIComponents.create_datetime_input("Dose Start Time", 12, 0)
        
        # Measured levels
        col1, col2 = st.columns(2)
        with col1:
            trough_level = st.number_input("Trough Level (mg/L)", min_value=0.0, value=1.0)
            trough_time = UIComponents.create_datetime_input("Trough Sample Time", 11, 30)
        with col2:
            peak_level = st.number_input("Peak Level (mg/L)", min_value=0.0, value=8.0)
            peak_time = UIComponents.create_datetime_input("Peak Sample Time", 13, 30)
        
        # Calculate times relative to dose
        t_trough = (trough_time - dose_time).total_seconds() / 3600
        t_peak = (peak_time - dose_time).total_seconds() / 3600
        
        if t_trough >= t_peak:
            st.error("Trough must be drawn before peak.")
            return
        
        # Calculate individualized PK parameters
        if st.button("Calculate PK Parameters"):
            try:
                # Calculate Ke from two levels
                delta_t = t_peak - t_trough
                ke = (math.log(trough_level) - math.log(peak_level)) / delta_t
                ke = max(1e-6, ke)
                t_half = 0.693 / ke
                
                # Extrapolate to find Cmax and Cmin
                cmax = peak_level * math.exp(ke * (t_peak - infusion_duration))
                cmin = cmax * math.exp(-ke * (tau - infusion_duration))
                
                # Calculate Vd
                term_inf = 1 - math.exp(-ke * infusion_duration)
                term_tau = 1 - math.exp(-ke * tau)
                denom = cmax * ke * infusion_duration * term_tau
                vd = (dose * term_inf) / denom if denom > 1e-9 else 0
                cl = ke * vd if vd > 0 else 0
                
                # Display results
                st.markdown("### Individualized PK Parameters")
                results = {
                    "ke": ke,
                    "t_half": t_half,
                    "vd": vd,
                    "cl": cl
                }
                levels = {
                    "peak": cmax,
                    "trough": cmin
                }
                
                UIComponents.display_results(results, levels, "")
                
                # Generate new dose recommendation
                desired_peak = st.number_input("Desired Peak (mg/L)", value=targets['peak']['min'])
                desired_interval = st.number_input("Desired Interval (hr)", value=tau)
                
                calculator = PKCalculator(drug, patient_data['weight'], patient_data['crcl'])
                new_dose = desired_peak * vd * (1 - math.exp(-ke * desired_interval))
                new_dose = calculator._round_dose(new_dose)
                
                st.success(f"Suggested new dose: {new_dose} mg every {desired_interval} hours")
                
            except Exception as e:
                st.error(f"Calculation error: {e}")
