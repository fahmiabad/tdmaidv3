# vancomycin_module.py
import streamlit as st
import math
from pk_calculations import PKCalculator
from clinical_logic import ClinicalInterpreter
from visualization import PKVisualizer
from ui_components import UIComponents
from config import DRUG_CONFIGS

class VancomycinModule:
    @staticmethod
    def auc_dosing(patient_data):
        st.title("🧪 Vancomycin AUC-Based Dosing")
        st.info("AUC24 is calculated using the Linear-Log Trapezoidal method")
        
        method = st.radio(
            "Select Method",
            ["Calculate Initial Dose", "Adjust Using Trough", "Adjust Using Peak & Trough"],
            horizontal=True
        )
        
        # Target selection
        st.markdown("### Target Selection")
        col1, col2 = st.columns(2)
        
        with col1:
            target_auc = st.slider("Target AUC24 (mg·hr/L)", 300, 700, 500, 10)
            st.info("Typical Target: 400-600 mg·hr/L")
        
        with col2:
            therapy_type = st.selectbox(
                "Therapy Type",
                ["Empiric (Trough 10-15)", "Definitive (Trough 15-20)"]
            )
            regimen = "empiric" if "Empiric" in therapy_type else "definitive"
            targets = DRUG_CONFIGS["Vancomycin"]["regimens"][regimen]["targets"]
        
        calculator = PKCalculator("Vancomycin", patient_data['weight'], patient_data['crcl'])
        
        if method == "Calculate Initial Dose":
            VancomycinModule._initial_dose(calculator, target_auc, targets, regimen)
        elif method == "Adjust Using Trough":
            VancomycinModule._adjust_with_trough(calculator, target_auc, targets, regimen)
        else:
            VancomycinModule._adjust_with_peak_trough(calculator, target_auc, targets, regimen)
    
    @staticmethod
    def _initial_dose(calculator, target_auc, targets, regimen):
        st.markdown("### Initial Dose Calculation")
        
        interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48], index=1)
        infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)
        
        # Population PK estimates
        pk_params = calculator.calculate_initial_parameters()
        st.markdown("#### Population PK Estimates")
        st.write(f"Vd: {pk_params['vd']:.2f} L | CL: {pk_params['cl']:.2f} L/hr | Ke: {pk_params['ke']:.4f} hr⁻¹")
        
        # Calculate dose for target AUC
        target_daily_dose = target_auc * pk_params['cl']
        dose_per_interval = target_daily_dose / (24 / interval)
        practical_dose = calculator._round_dose(dose_per_interval)
        
        # Predict levels
        predicted_levels = calculator.predict_levels(practical_dose, interval, infusion_duration)
        predicted_auc = calculator.calculate_vancomycin_auc(
            predicted_levels['peak'],
            predicted_levels['trough'],
            pk_params['ke'],
            interval,
            infusion_duration
        )
        
        st.success(f"Recommended dose: {practical_dose} mg every {interval} hours")
        st.info(f"Predicted AUC24: {predicted_auc:.0f} mg·hr/L")
        st.info(f"Predicted Peak: {predicted_levels['peak']:.1f} mg/L | Trough: {predicted_levels['trough']:.1f} mg/L")
        
        # Display concentration-time curve
        PKVisualizer.display_pk_chart(
            pk_params,
            predicted_levels,
            {'tau': interval, 'infusion_duration': infusion_duration}
        )
        
        # Check targets
        interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
        assessment, status = interpreter.assess_levels(predicted_levels)
        
        if st.button("Generate Clinical Interpretation"):
            recommendations = interpreter.generate_recommendations(status, calculator.crcl)
            st.markdown("### Clinical Interpretation")
            st.markdown(interpreter.format_recommendations(assessment, status, recommendations))
    
    @staticmethod
    def _adjust_with_trough(calculator, target_auc, targets, regimen):
        st.markdown("### Dose Adjustment Using Trough")
        
        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0)
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12)
        with col2:
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0)
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)
        
        # Estimate parameters using population Vd and measured trough
        pk_params = calculator.calculate_initial_parameters()
        vd = pk_params['vd']
        
        # Estimate CL based on trough
        predicted_trough_pop = calculator.predict_levels(current_dose, current_interval, infusion_duration)['trough']
        
        if predicted_trough_pop > 0.5 and measured_trough > 0.1:
            cl_adjusted = pk_params['cl'] * (predicted_trough_pop / measured_trough)
            cl_adjusted = max(0.05, min(cl_adjusted, pk_params['cl'] * 5))
        else:
            cl_adjusted = pk_params['cl']
        
        ke_adjusted = cl_adjusted / vd
        t_half_adjusted = 0.693 / ke_adjusted
        
        st.markdown("#### Adjusted PK Parameters")
        st.write(f"CL: {cl_adjusted:.2f} L/hr | Ke: {ke_adjusted:.4f} hr⁻¹ | t½: {t_half_adjusted:.2f} hr")
        
        # Calculate current AUC
        pk_params_adj = {'vd': vd, 'ke': ke_adjusted}
        predicted_levels = calculator.predict_levels(current_dose, current_interval, infusion_duration)
        current_auc = calculator.calculate_vancomycin_auc(
            predicted_levels['peak'],
            measured_trough,
            ke_adjusted,
            current_interval,
            infusion_duration
        )
        
        st.markdown("#### Current Regimen Assessment")
        st.write(f"Estimated AUC24: {current_auc:.0f} mg·hr/L")
        st.write(f"Measured Trough: {measured_trough:.1f} mg/L")
        
        # Calculate new dose
        desired_interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48], 
                                      index=[8, 12, 24, 36, 48].index(current_interval) if current_interval in [8, 12, 24, 36, 48] else 1)
        
        new_daily_dose = target_auc * cl_adjusted
        new_dose_interval = new_daily_dose / (24 / desired_interval)
        practical_new_dose = calculator._round_dose(new_dose_interval)
        
        st.success(f"Suggested new dose: {practical_new_dose} mg every {desired_interval} hours")
        
        if st.button("Generate Clinical Interpretation"):
            predicted_levels_new = calculator.predict_levels(practical_new_dose, desired_interval, infusion_duration)
            predicted_auc_new = calculator.calculate_vancomycin_auc(
                predicted_levels_new['peak'],
                predicted_levels_new['trough'],
                ke_adjusted,
                desired_interval,
                infusion_duration
            )
            
            st.info(f"Predicted AUC24 with new dose: {predicted_auc_new:.0f} mg·hr/L")
            st.info(f"Predicted Trough with new dose: {predicted_levels_new['trough']:.1f} mg/L")
    
    @staticmethod
    def _adjust_with_peak_trough(calculator, target_auc, targets, regimen):
        st.markdown("### Dose Adjustment Using Peak & Trough")
        
        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0)
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12)
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)
        
        with col2:
            dose_time = UIComponents.create_datetime_input("Dose Start Time", 9, 0)
            trough_time = UIComponents.create_datetime_input("Trough Sample Time", 8, 30)
            peak_time = UIComponents.create_datetime_input("Peak Sample Time", 10, 30)
        
        measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0)
        measured_peak = st.number_input("Measured Peak (mg/L)", 0.1, 100.0, 30.0)
        
        # Calculate relative times
        t_trough = (trough_time - dose_time).total_seconds() / 3600
        t_peak = (peak_time - dose_time).total_seconds() / 3600
        
        if t_trough >= t_peak:
            st.error("Trough must be drawn before peak")
            return
        
        # Calculate individual PK parameters
        try:
            delta_t = t_peak - t_trough
            ke_ind = (math.log(measured_trough) - math.log(measured_peak)) / delta_t
            ke_ind = max(1e-6, ke_ind)
            t_half_ind = 0.693 / ke_ind
            
            # Extrapolate to find true Cmax and Cmin
            time_to_cmax = infusion_duration - (t_peak - infusion_duration)
            cmax_ind = measured_peak * math.exp(ke_ind * time_to_cmax)
            cmin_ind = cmax_ind * math.exp(-ke_ind * (current_interval - infusion_duration))
            
            # Calculate Vd
            term_inf = 1 - math.exp(-ke_ind * infusion_duration)
            term_tau = 1 - math.exp(-ke_ind * current_interval)
            denom = cmax_ind * ke_ind * infusion_duration * term_tau
            vd_ind = (current_dose * term_inf) / denom if denom > 1e-9 else 0
            cl_ind = ke_ind * vd_ind if vd_ind > 0 else 0
            
            st.markdown("#### Individualized PK Parameters")
            st.write(f"Ke: {ke_ind:.4f} hr⁻¹ | t½: {t_half_ind:.2f} hr | Vd: {vd_ind:.2f} L | CL: {cl_ind:.2f} L/hr")
            
            # Calculate current AUC
            current_auc = calculator.calculate_vancomycin_auc(
                cmax_ind,
                cmin_ind,
                ke_ind,
                current_interval,
                infusion_duration
            )
            
            st.markdown("#### Current Regimen Assessment")
            st.write(f"Estimated AUC24: {current_auc:.0f} mg·hr/L")
            
            # Calculate new dose
            desired_interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48], 
                                          index=[8, 12, 24, 36, 48].index(current_interval) if current_interval in [8, 12, 24, 36, 48] else 1)
            
            if cl_ind > 0:
                new_daily_dose = target_auc * cl_ind
                new_dose_interval = new_daily_dose / (24 / desired_interval)
                practical_new_dose = calculator._round_dose(new_dose_interval)
                
                st.success(f"Suggested new dose: {practical_new_dose} mg every {desired_interval} hours")
            else:
                st.error("Unable to calculate new dose due to invalid clearance calculation")
            
        except Exception as e:
            st.error(f"Calculation error: {e}")
