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
            VancomycinModule._initial_dose(calculator, target_auc, targets, regimen, patient_data)
        elif method == "Adjust Using Trough":
            VancomycinModule._adjust_with_trough(calculator, target_auc, targets, regimen, patient_data)
        else:
            VancomycinModule._adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data)
    
    @staticmethod
    def _initial_dose(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Initial Dose Calculation")
        
        interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48], index=1)
        infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)
        
        # Population PK estimates
        pk_params = calculator.calculate_initial_parameters()
        
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
        predicted_levels['auc'] = predicted_auc
        
        # Display results
        UIComponents.display_results(
            pk_params,
            predicted_levels,
            f"Recommended dose: {practical_dose} mg every {interval} hours"
        )
        
        # Display concentration-time curve
        PKVisualizer.display_pk_chart(
            pk_params,
            predicted_levels,
            {'tau': interval, 'infusion_duration': infusion_duration}
        )
        
        # Clinical interpretation
        if st.button("Generate Clinical Interpretation"):
            interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
            assessment, status = interpreter.assess_levels(predicted_levels)
            recommendations = interpreter.generate_recommendations(status, patient_data['crcl'])
            
            st.markdown("### Clinical Interpretation")
            interpretation = interpreter.format_recommendations(assessment, status, recommendations, patient_data)
            st.markdown(interpretation)
            
            # Generate and display print button
            report = UIComponents.generate_report(
                "Vancomycin",
                f"{regimen} therapy",
                patient_data,
                pk_params,
                predicted_levels,
                f"Recommended dose: {practical_dose} mg every {interval} hours",
                interpretation
            )
            UIComponents.create_print_button(report)
    
    @staticmethod
    def _adjust_with_trough(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Trough")
        
        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0)
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12)
        with col2:
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0)
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)
        
        # Optional timing information for better context
        st.markdown("##### Timing Information (optional)")
        include_timing = st.checkbox("Include specific dose and trough times?")
        
        if include_timing:
            col1, col2 = st.columns(2)
            with col1:
                dose_hour, dose_minute, dose_display = UIComponents.create_time_input("Dose Start Time", 9, 0, key="dose")
                st.info(f"Dose given at: {dose_display}")
            with col2:
                trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key="trough")
                st.info(f"Trough drawn at: {trough_display}")
            
            # Calculate time difference
            t_trough = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)
            st.info(f"Time from dose to trough: {t_trough:.1f} hours")
        
        if st.button("Calculate PK Parameters"):
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
            
            adjusted_params = {
                'ke': ke_adjusted,
                't_half': t_half_adjusted,
                'vd': vd,
                'cl': cl_adjusted
            }
            
            # Calculate current AUC with measured values
            predicted_levels = calculator.predict_levels(current_dose, current_interval, infusion_duration)
            current_auc = calculator.calculate_vancomycin_auc(
                predicted_levels['peak'],
                measured_trough,
                ke_adjusted,
                current_interval,
                infusion_duration
            )
            
            measured_levels = {
                'peak': predicted_levels['peak'],  # Estimated peak
                'trough': measured_trough,
                'auc': current_auc
            }
            
            # Display results using consistent format
            UIComponents.display_results(
                adjusted_params,
                measured_levels,
                ""
            )
            
            # Calculate new dose
            st.markdown("### Dose Adjustment")
            desired_interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48], 
                                          index=[8, 12, 24, 36, 48].index(current_interval) if current_interval in [8, 12, 24, 36, 48] else 1)
            
            new_daily_dose = target_auc * cl_adjusted
            new_dose_interval = new_daily_dose / (24 / desired_interval)
            practical_new_dose = calculator._round_dose(new_dose_interval)
            
            recommendation = f"Suggested new dose: {practical_new_dose} mg every {desired_interval} hours"
            st.success(recommendation)
            
            # Clinical interpretation
            interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
            assessment, status = interpreter.assess_levels(measured_levels)
            recommendations = interpreter.generate_recommendations(status, patient_data['crcl'])
            
            st.markdown("### Clinical Interpretation")
            interpretation = interpreter.format_recommendations(assessment, status, recommendations, patient_data)
            st.markdown(interpretation)
            
            # Generate and display print button
            report = UIComponents.generate_report(
                "Vancomycin",
                f"{regimen} therapy - Trough adjustment",
                patient_data,
                adjusted_params,
                measured_levels,
                recommendation,
                interpretation
            )
            UIComponents.create_print_button(report)
    
    @staticmethod
    def _adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Peak & Trough")
        
        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0)
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12)
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)
        
        # Dose administration time
        st.subheader("Dose Administration Time")
        dose_hour, dose_minute, dose_display = UIComponents.create_time_input("Dose Start Time", 9, 0, key="dose")
        st.info(f"Dose given at: {dose_display}")
        
        # Sampling times
        st.subheader("Sampling Times")
        col1, col2 = st.columns(2)
        with col1:
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0)
            trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key="trough")
            st.info(f"Trough drawn at: {trough_display}")
        with col2:
            measured_peak = st.number_input("Measured Peak (mg/L)", 0.1, 100.0, 30.0)
            peak_hour, peak_minute, peak_display = UIComponents.create_time_input("Peak Sample Time", 11, 0, key="peak")
            st.info(f"Peak drawn at: {peak_display}")
        
        # Calculate time differences
        t_trough = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)
        t_peak = UIComponents.calculate_time_difference(dose_hour, dose_minute, peak_hour, peak_minute)
        
        # Handle next day scenario
        if t_peak < 0:
            t_peak += 24  # Add 24 hours if peak is on next day
        if t_trough < 0:
            t_trough += 24  # Add 24 hours if trough is on next day
        
        if st.button("Calculate PK Parameters"):
            # For conventional 2-level kinetics, we expect trough before next dose and peak after infusion
            # But we'll handle both "trough before peak" (within same dose) and "trough before next dose" scenarios
            
            try:
                if t_trough < t_peak:
                    # Trough and peak are within same dose interval
                    delta_t = t_peak - t_trough
                else:
                    # Trough is before next dose, peak is from previous dose
                    delta_t = (current_interval - t_trough) + (t_peak)
                
                if delta_t <= 0:
                    st.error("Unable to calculate. Please check your sampling times.")
                    return
                
                # Calculate individual PK parameters
                ke_ind = (math.log(measured_trough) - math.log(measured_peak)) / delta_t
                ke_ind = max(1e-6, abs(ke_ind))  # Ensure positive ke
                t_half_ind = 0.693 / ke_ind
                
                # Calculate Vd and extrapolate to find true Cmax and Cmin
                if t_peak > infusion_duration:
                    # Peak is post-infusion - back extrapolate to find Cmax
                    cmax_ind = measured_peak * math.exp(ke_ind * (t_peak - infusion_duration))
                else:
                    # Peak is during infusion - estimate Cmax
                    cmax_ind = measured_peak / (t_peak / infusion_duration)
                
                # Calculate Cmin at end of interval
                cmin_ind = cmax_ind * math.exp(-ke_ind * (current_interval - infusion_duration))
                
                # Calculate Vd using the dose/concentration relationship
                term_inf = 1 - math.exp(-ke_ind * infusion_duration)
                term_tau = 1 - math.exp(-ke_ind * current_interval)
                denom = cmax_ind * ke_ind * infusion_duration * term_tau
                vd_ind = (current_dose * term_inf) / denom if denom > 1e-9 else 0
                cl_ind = ke_ind * vd_ind if vd_ind > 0 else 0
                
                individual_params = {
                    'ke': ke_ind,
                    't_half': t_half_ind,
                    'vd': vd_ind,
                    'cl': cl_ind
                }
                
                # Calculate current AUC
                current_auc = calculator.calculate_vancomycin_auc(
                    cmax_ind,
                    cmin_ind,
                    ke_ind,
                    current_interval,
                    infusion_duration
                )
                
                measured_levels = {
                    'peak': cmax_ind,
                    'trough': cmin_ind,
                    'auc': current_auc
                }
                
                # Display results using consistent format
                UIComponents.display_results(
                    individual_params,
                    measured_levels,
                    ""
                )
                
                # Calculate new dose
                st.markdown("### Dose Adjustment")
                desired_interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48], 
                                              index=[8, 12, 24, 36, 48].index(current_interval) if current_interval in [8, 12, 24, 36, 48] else 1)
                
                if cl_ind > 0:
                    new_daily_dose = target_auc * cl_ind
                    new_dose_interval = new_daily_dose / (24 / desired_interval)
                    practical_new_dose = calculator._round_dose(new_dose_interval)
                    
                    recommendation = f"Suggested new dose: {practical_new_dose} mg every {desired_interval} hours"
                    st.success(recommendation)
                    
                    # Clinical interpretation
                    interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
                    assessment, status = interpreter.assess_levels(measured_levels)
                    recommendations = interpreter.generate_recommendations(status, patient_data['crcl'])
                    
                    st.markdown("### Clinical Interpretation")
                    interpretation = interpreter.format_recommendations(assessment, status, recommendations, patient_data)
                    st.markdown(interpretation)
                    
                    # Generate and display print button
                    report = UIComponents.generate_report(
                        "Vancomycin",
                        f"{regimen} therapy - Peak and Trough adjustment",
                        patient_data,
                        individual_params,
                        measured_levels,
                        recommendation,
                        interpretation
                    )
                    UIComponents.create_print_button(report)
                else:
                    st.error("Unable to calculate new dose due to invalid clearance calculation")
                
            except Exception as e:
                st.error(f"Calculation error: {e}")
                st.info("Please verify that sampling times and concentration values are correct.")
