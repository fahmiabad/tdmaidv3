# vancomycin_module.py
import streamlit as st
import math
from datetime import datetime, timedelta
from pk_calculations import PKCalculator
from clinical_logic import ClinicalInterpreter
from visualization import PKVisualizer
from ui_components import UIComponents
from config import DRUG_CONFIGS

class VancomycinModule:
    @staticmethod
    def auc_dosing(patient_data):
        st.title("🧪 Vancomycin Dosing")
        st.info("AUC24 is calculated using the Linear-Log Trapezoidal method")

        method = st.radio(
            "Select Method",
            ["Calculate Initial Dose", "Adjust Using Single Level", "Adjust Using Peak & Trough"],
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
        elif method == "Adjust Using Single Level":
            VancomycinModule._adjust_with_single_level(calculator, target_auc, targets, regimen, patient_data)
        else:
            VancomycinModule._adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data)

    @staticmethod
    def _initial_dose(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Initial Dose Calculation")

        # Recommend interval based on CrCl
        crcl = patient_data['crcl']
        
        # More practical interval recommendations based on renal function
        if crcl < 20:
            recommended_interval = 48
        elif crcl < 30:
            recommended_interval = 36
        elif crcl < 40:
            recommended_interval = 24
        elif crcl < 60:
            recommended_interval = 12
        else:
            recommended_interval = 8

        # More practical interval options
        interval_options = [6, 8, 12, 24, 36, 48, 72]
        recommended_index = interval_options.index(min(interval_options, key=lambda x: abs(x - recommended_interval)))

        col1, col2 = st.columns(2)
        with col1:
            interval = st.selectbox(
                "Dosing Interval (hr)",
                interval_options,
                index=recommended_index,
                help=f"Interval of {recommended_interval}h suggested based on CrCl of {crcl:.1f} mL/min"
            )
        with col2:
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0, 0.5)

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

        # Validate results and provide clinical warnings
        warnings = VancomycinModule._validate_regimen(practical_dose, interval, predicted_levels, patient_data)
        
        if warnings:
            st.warning("Please review the following warnings:")
            for warning in warnings:
                st.warning(f"• {warning}")

        # Display results
        UIComponents.display_results(
            pk_params,
            predicted_levels,
            f"Recommended dose: {practical_dose} mg every {interval} hours (infused over {infusion_duration} hr)"
        )

        # Display concentration-time curve
        PKVisualizer.display_pk_chart(
            pk_params,
            predicted_levels,
            {'tau': interval, 'infusion_duration': infusion_duration},
            key_suffix="initial_dose"
        )

        # Clinical interpretation
        if st.button("Generate Clinical Interpretation"):
            interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
            assessment, status = interpreter.assess_levels(predicted_levels)
            recommendations = interpreter.generate_recommendations(status, patient_data['crcl'])
            
            # Add resampling recommendation
            resampling_rec = interpreter.recommend_resampling_date(interval, status, patient_data['crcl'])
            recommendations.append(resampling_rec)

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
    def _adjust_with_single_level(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Single Level")

        # Basic dosing information
        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input(
                "Current Dose (mg)", 
                min_value=250.0, 
                max_value=3000.0, 
                value=1000.0, 
                step=50.0,
                help="Typical adult doses range from 500-2000mg"
            )
            
            # Use practical interval options
            interval_options = [6, 8, 12, 24, 36, 48, 72]
            interval_index = 2  # Default to 12 hours
            
            current_interval = st.selectbox(
                "Current Interval (hr)", 
                options=interval_options,
                index=interval_index,
                help="Standard intervals based on renal function"
            )
        
        with col2:
            infusion_duration = st.number_input(
                "Infusion Duration (hr)", 
                min_value=0.5, 
                max_value=4.0, 
                value=1.0, 
                step=0.5,
                help="Standard infusion time is 1-2 hours"
            )
            
            # Level type selection (trough or random)
            level_type = st.radio(
                "Level Measurement Type",
                ["Trough Level", "Random Level"],
                help="Select 'Trough Level' if drawn just before next dose, or 'Random Level' if drawn at any other time"
            )

        # Display target ranges based on therapy type
        if "Empiric" in regimen:
            trough_min, trough_max = 10, 15
            st.info(f"Empiric therapy target trough range: {trough_min}-{trough_max} mg/L")
        else:  # Definitive
            trough_min, trough_max = 15, 20
            st.info(f"Definitive therapy target trough range: {trough_min}-{trough_max} mg/L")

        # Level measurement information
        st.subheader("Level Measurement Information")
        col1, col2 = st.columns(2)
        
        with col1:
            measured_level = st.number_input(
                "Measured Level (mg/L)", 
                min_value=0.1, 
                max_value=100.0, 
                value=12.0, 
                step=0.1,
                help="Typical therapeutic levels range from 5-40 mg/L"
            )
        
        # Timing information
        st.subheader("Timing Information")
        include_timing = True
        
        if include_timing:
            col1, col2 = st.columns(2)
            with col1:
                dose_hour, dose_minute, dose_display = UIComponents.create_time_input(
                    "Last Dose Start Time", 
                    9, 0, 
                    key="dose_single"
                )
                st.info(f"Dose given at: {dose_display}")
            
            with col2:
                level_hour, level_minute, level_display = UIComponents.create_time_input(
                    "Level Sample Time", 
                    8, 30, 
                    key="level_single"
                )
                st.info(f"Level drawn at: {level_display}")

            # Calculate time difference
            time_diff = UIComponents.calculate_time_difference(dose_hour, dose_minute, level_hour, level_minute)
            
            # Handle next day scenario
            if time_diff < 0 and level_type == "Trough":
                time_diff += 24  # Add 24 hours if trough is on next day before next dose
                st.info(f"Time from dose to level: {time_diff:.1f} hours (next day)")
            else:
                st.info(f"Time from dose to level: {time_diff:.1f} hours")

        if st.button("Calculate PK Parameters"):
            try:
                # Validate inputs before proceeding
                errors = []
                warnings = []
                
                # Basic validation
                if time_diff < 0 and level_type == "Random Level":
                    errors.append("Invalid timing: Sample time is before dose time. Please check your inputs.")
                
                if time_diff > current_interval and level_type == "Random Level":
                    warnings.append(f"Time since dose ({time_diff:.1f}h) exceeds the dosing interval ({current_interval}h). Are you sure about the timing?")
                
                if level_type == "Trough" and abs(time_diff) > 3 and abs(time_diff) < (current_interval - 3):
                    warnings.append(f"Sample time ({time_diff:.1f}h after dose) is not close to the next dose time ({current_interval}h). This may not be a true trough.")
                
                # Display errors and stop if necessary
                if errors:
                    for error in errors:
                        st.error(error)
                    return
                
                # Display warnings but continue
                if warnings:
                    for warning in warnings:
                        st.warning(warning)
                
                # Estimate parameters using population Vd and measured level
                pk_params = calculator.calculate_initial_parameters()
                vd = pk_params['vd']
                ke_pop = pk_params['ke']
                
                # Different processing based on level type
                if level_type == "Trough":
                    # For trough level, adjust clearance based on measured trough
                    predicted_trough_pop = calculator.predict_levels(current_dose, current_interval, infusion_duration)['trough']
                    
                    if predicted_trough_pop > 0.5 and measured_level > 0.1:
                        # Adjust clearance based on ratio of predicted to measured trough
                        cl_adjusted = pk_params['cl'] * (predicted_trough_pop / measured_level)
                        cl_adjusted = max(0.05, min(cl_adjusted, pk_params['cl'] * 5))  # Limit adjustment range
                    else:
                        cl_adjusted = pk_params['cl']
                    
                    ke_adjusted = cl_adjusted / vd
                    t_half_adjusted = 0.693 / ke_adjusted if ke_adjusted > 0 else float('inf')
                    
                    # Use adjusted parameters
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
                        measured_level,  # Use measured trough
                        ke_adjusted,
                        current_interval,
                        infusion_duration
                    )
                    
                    measured_levels = {
                        'peak': predicted_levels['peak'],  # Estimated peak
                        'trough': measured_level,          # Measured trough
                        'auc': current_auc
                    }
                
                else:  # Random level
                    # For random level, we need to back-calculate using the time since dose
                    if time_diff <= infusion_duration:
                        # Level drawn during infusion - complex scenario, use approximation
                        st.warning("Level drawn during infusion. Calculations are approximate.")
                        
                        # Estimate ke using population parameter initially
                        ke_adjusted = ke_pop
                        t_half_adjusted = 0.693 / ke_adjusted if ke_adjusted > 0 else float('inf')
                        
                        # Rough approximation of peak based on infusion ratio
                        est_cmax = measured_level * (infusion_duration / time_diff) if time_diff > 0 else measured_level
                        
                        # Estimate trough using population ke
                        est_cmin = est_cmax * math.exp(-ke_adjusted * (current_interval - infusion_duration))
                        
                    else:
                        # Level drawn after infusion
                        # Back-calculate ke using the measured level and time
                        # Start with population estimate
                        predicted_levels = calculator.predict_levels(current_dose, current_interval, infusion_duration)
                        est_cmax_pop = predicted_levels['peak']
                        
                        # Calculate what level should be at the measured time point using population ke
                        expected_level_at_timepoint = est_cmax_pop * math.exp(-ke_pop * (time_diff - infusion_duration))
                        
                        # Adjust ke based on ratio of expected to measured
                        adjustment_factor = min(max(expected_level_at_timepoint / measured_level, 0.2), 5.0)
                        
                        ke_adjusted = ke_pop * adjustment_factor
                        ke_adjusted = max(0.01, min(ke_adjusted, 0.3))  # Reasonable ke range
                        
                        t_half_adjusted = 0.693 / ke_adjusted if ke_adjusted > 0 else float('inf')
                        
                        # Back-calculate peak and trough with adjusted ke
                        est_cmax = measured_level / math.exp(-ke_adjusted * (time_diff - infusion_duration))
                        est_cmin = est_cmax * math.exp(-ke_adjusted * (current_interval - infusion_duration))
                    
                    # Adjust clearance and volume based on the estimated ke
                    cl_adjusted = ke_adjusted * vd
                    
                    # Use adjusted parameters
                    adjusted_params = {
                        'ke': ke_adjusted,
                        't_half': t_half_adjusted,
                        'vd': vd,
                        'cl': cl_adjusted
                    }
                    
                    # Calculate current AUC with estimated values
                    current_auc = calculator.calculate_vancomycin_auc(
                        est_cmax,
                        est_cmin,
                        ke_adjusted,
                        current_interval,
                        infusion_duration
                    )
                    
                    measured_levels = {
                        'peak': est_cmax,      # Estimated peak
                        'trough': est_cmin,    # Estimated trough
                        'auc': current_auc
                    }
                
                # Display results using consistent format
                st.markdown("### Current PK Parameters and Levels")
                UIComponents.display_results(
                    adjusted_params,
                    measured_levels,
                    f"Current regimen: {current_dose} mg every {current_interval} hours (infused over {infusion_duration} hr)"
                )
                
                # Calculate new dose - find the best interval and dose
                st.markdown("### Dose Adjustment Recommendation")
                
                # Start with interval recommendation based on renal function
                crcl = patient_data['crcl']
                practical_interval_options = [6, 8, 12, 24, 36, 48, 72]
                
                # Find optimal regimen
                best_regimen = VancomycinModule._find_optimal_regimen(
                    calculator, 
                    adjusted_params, 
                    target_auc, 
                    targets, 
                    practical_interval_options, 
                    crcl, 
                    infusion_duration
                )
                
                if best_regimen:
                    # Display the single best recommendation
                    old_regimen = f"{current_dose} mg every {current_interval} hours"
                    new_regimen = f"{best_regimen['dose']} mg every {best_regimen['interval']} hours"
                    
                    st.subheader("Recommended Dosing Regimen")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Current Regimen:**")
                        st.info(old_regimen)
                        
                        # Display current levels with appropriate indicators
                        for parameter, value in measured_levels.items():
                            if parameter == 'auc':
                                auc_min = targets['AUC']['min']
                                auc_max = targets['AUC']['max']
                                if value < auc_min:
                                    st.markdown(f"❌ AUC₂₄: {value:.1f} mg·hr/L (BELOW target)")
                                elif value > auc_max:
                                    st.markdown(f"⚠️ AUC₂₄: {value:.1f} mg·hr/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ AUC₂₄: {value:.1f} mg·hr/L (within target)")
                            
                            elif parameter == 'trough':
                                trough_min = targets['trough']['min']
                                trough_max = targets['trough']['max']
                                if value < trough_min:
                                    st.markdown(f"❌ Trough: {value:.1f} mg/L (BELOW target)")
                                elif value > trough_max:
                                    st.markdown(f"⚠️ Trough: {value:.1f} mg/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ Trough: {value:.1f} mg/L (within target)")
                                    
                            elif parameter == 'peak':
                                st.markdown(f"Peak: {value:.1f} mg/L")
                    
                    with col2:
                        st.markdown("**Recommended Regimen:**")
                        st.success(new_regimen)
                        
                        # Display predicted levels with appropriate indicators
                        predicted_new_levels = best_regimen['predicted_levels']
                        for parameter, value in predicted_new_levels.items():
                            if parameter == 'auc':
                                auc_min = targets['AUC']['min']
                                auc_max = targets['AUC']['max']
                                if value < auc_min:
                                    st.markdown(f"❌ AUC₂₄: {value:.1f} mg·hr/L (BELOW target)")
                                elif value > auc_max:
                                    st.markdown(f"⚠️ AUC₂₄: {value:.1f} mg·hr/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ AUC₂₄: {value:.1f} mg·hr/L (within target)")
                            
                            elif parameter == 'trough':
                                trough_min = targets['trough']['min']
                                trough_max = targets['trough']['max']
                                if value < trough_min:
                                    st.markdown(f"❌ Trough: {value:.1f} mg/L (BELOW target)")
                                elif value > trough_max:
                                    st.markdown(f"⚠️ Trough: {value:.1f} mg/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ Trough: {value:.1f} mg/L (within target)")
                                    
                            elif parameter == 'peak':
                                st.markdown(f"Peak: {value:.1f} mg/L")
                    
                    # Display clinical reasoning
                    st.markdown("### Clinical Reasoning")
                    st.markdown(best_regimen['reasoning'])
                    
                    # Clinical interpretation
                    interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)

                    # First assess current levels
                    current_assessment, current_status = interpreter.assess_levels(measured_levels)

                    # Then assess predicted new levels
                    new_assessment, new_status = interpreter.assess_levels(predicted_new_levels)

                    # Generate recommendations based on the NEW predicted levels
                    recommendations = interpreter.generate_recommendations(new_status, patient_data['crcl'])
                    
                    # Add resampling recommendation
                    resampling_rec = interpreter.recommend_resampling_date(
                        best_regimen['interval'], 
                        new_status, 
                        patient_data['crcl']
                    )
                    recommendations.append(resampling_rec)

                    st.markdown("### Clinical Interpretation")
                    interpretation = interpreter.format_recommendations_for_regimen_change(
                        old_regimen,
                        measured_levels,
                        new_regimen,
                        predicted_new_levels, 
                        patient_data
                    )
                    st.markdown(interpretation)

                    # Generate and display print button
                    report = UIComponents.generate_report(
                        "Vancomycin",
                        f"{regimen} therapy - Level adjustment",
                        patient_data,
                        adjusted_params,
                        measured_levels,
                        f"Changed from {old_regimen} to {new_regimen}",
                        interpretation
                    )
                    UIComponents.create_print_button(report)

                    # Visualize the predicted concentration-time curves
                    st.markdown("### Predicted Concentration-Time Profiles")
                    tab1, tab2 = st.tabs(["Current Regimen", "New Regimen"])

                    with tab1:
                        PKVisualizer.display_pk_chart(
                            adjusted_params,
                            measured_levels,
                            {'tau': current_interval, 'infusion_duration': infusion_duration},
                            key_suffix="current_single"
                        )

                    with tab2:
                        PKVisualizer.display_pk_chart(
                            adjusted_params,
                            predicted_new_levels,
                            {'tau': best_regimen['interval'], 'infusion_duration': infusion_duration},
                            key_suffix="new_single"
                        )
                
                else:
                    st.error("Could not determine optimal dosing regimen. Please check input values.")
            
            except Exception as e:
                st.error(f"An error occurred during calculations: {str(e)}")
                st.info("Please verify that all input values are clinically reasonable.")

    @staticmethod
    def _adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Peak & Trough")

        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0, 50.0,
                                         help="Typical adult doses range from 500-2000mg")
            
            # Use practical interval options
            interval_options = [6, 8, 12, 24, 36, 48, 72]
            interval_index = 2  # Default to 12 hours
            
            current_interval = st.selectbox(
                "Current Interval (hr)", 
                options=interval_options,
                index=interval_index,
                help="Standard intervals based on renal function"
            )
        
        with col2:
            infusion_duration = st.number_input(
                "Infusion Duration (hr)", 
                0.5, 4.0, 1.0, 0.5,
                help="Standard infusion time is 1-2 hours"
            )

        # Display target ranges based on therapy type
        if "Empiric" in regimen:
            trough_min, trough_max = 10, 15
            st.info(f"Empiric therapy target trough range: {trough_min}-{trough_max} mg/L")
        else:  # Definitive
            trough_min, trough_max = 15, 20
            st.info(f"Definitive therapy target trough range: {trough_min}-{trough_max} mg/L")

        # Dose administration time
        st.subheader("Dose Administration Time")
        dose_hour, dose_minute, dose_display = UIComponents.create_time_input("Dose Start Time", 9, 0, key="dose_pt")
        st.info(f"Dose given at: {dose_display}")

        # Sampling times
        st.subheader("Sampling Times")
        col1, col2 = st.columns(2)
        with col1:
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0, 0.1,
                                            help="Typical therapeutic trough levels range from 5-20 mg/L")
            trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key="trough_pt")
            st.info(f"Trough drawn at: {trough_display}")
        with col2:
            measured_peak = st.number_input("Measured Peak (mg/L)", 0.1, 100.0, 30.0, 0.1,
                                          help="Typical therapeutic peak levels range from 20-40 mg/L")
            peak_hour, peak_minute, peak_display = UIComponents.create_time_input("Peak Sample Time", 11, 0, key="peak_pt")
            st.info(f"Peak drawn at: {peak_display}")


        if st.button("Calculate PK Parameters"):
            try:
                # Calculate time differences
                t_trough = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)
                t_peak = UIComponents.calculate_time_difference(dose_hour, dose_minute, peak_hour, peak_minute)
                
                # Handle cross-day scenarios
                if t_peak < 0: t_peak += 24  # Add 24 hours if peak is on next day
                if t_trough < 0: t_trough += 24  # Add 24 hours if trough is on next day
                
                # Basic validation
                errors = []
                warnings = []
                
                if t_peak <= 0 or t_trough <= 0:
                    errors.append("Invalid sampling times. Please check that samples are taken after dose administration.")
                
                if t_peak > current_interval or t_trough > current_interval:
                    warnings.append(f"Sampling time exceeds dosing interval ({current_interval}h). Check if timing is correct.")
                
                if abs(t_peak - t_trough) < 1:
                    errors.append("Peak and trough samples are too close together for accurate calculations.")
                
                # Display errors and stop if necessary
                if errors:
                    for error in errors:
                        st.error(error)
                    return
                
                # Display warnings but continue
                if warnings:
                    for warning in warnings:
                        st.warning(warning)
                
                # Determine which sample is first
                if t_peak < t_trough:
                    t1, c1 = t_peak, measured_peak
                    t2, c2 = t_trough, measured_trough
                else:
                    t1, c1 = t_trough, measured_trough
                    t2, c2 = t_peak, measured_peak
                
                # Calculate ke using the two points
                delta_t = t2 - t1
                
                if c1 > 0 and c2 > 0:
                    ke_ind = (math.log(c1) - math.log(c2)) / delta_t
                    ke_ind = max(0.01, min(0.3, abs(ke_ind)))  # Reasonable ke range
                    t_half_ind = 0.693 / ke_ind
                else:
                    st.error("Invalid concentration values. Both peak and trough must be positive.")
                    return
                
                # Use population Vd initially
                pk_params = calculator.calculate_initial_parameters()
                vd_ind = pk_params['vd']
                
                # Calculate Cmax at end of infusion by back-extrapolating
                if t_peak > infusion_duration:
                    cmax_ind = measured_peak * math.exp(ke_ind * (t_peak - infusion_duration))
                else:
                    # If peak measured during infusion, use a simple approximation
                    cmax_ind = measured_peak * (infusion_duration / t_peak) if t_peak > 0 else measured_peak
                
                # Calculate Cmin just before the next dose
                cmin_ind = cmax_ind * math.exp(-ke_ind * (current_interval - infusion_duration))
                
                # Calculate clearance
                cl_ind = ke_ind * vd_ind
                
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
                    'peak': cmax_ind,      # Calculated steady-state peak
                    'trough': cmin_ind,    # Calculated steady-state trough
                    'auc': current_auc
                }
                
                # Display results using consistent format
                st.markdown("### Current PK Parameters and Levels")
                UIComponents.display_results(
                    individual_params,
                    measured_levels,
                    f"Current regimen: {current_dose} mg every {current_interval} hours (infused over {infusion_duration} hr)"
                )
                
                # Calculate new dose - find the best interval and dose
                st.markdown("### Dose Adjustment Recommendation")
                
                # Available interval options
                practical_interval_options = [6, 8, 12, 24, 36, 48, 72]
                
                # Find optimal regimen
                best_regimen = VancomycinModule._find_optimal_regimen(
                    calculator, 
                    individual_params, 
                    target_auc, 
                    targets, 
                    practical_interval_options, 
                    patient_data['crcl'], 
                    infusion_duration
                )
                
                if best_regimen:
                    # Display the single best recommendation
                    old_regimen = f"{current_dose} mg every {current_interval} hours"
                    new_regimen = f"{best_regimen['dose']} mg every {best_regimen['interval']} hours"
                    
                    st.subheader("Recommended Dosing Regimen")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Current Regimen:**")
                        st.info(old_regimen)
                        
                        # Display current levels with appropriate indicators
                        for parameter, value in measured_levels.items():
                            if parameter == 'auc':
                                auc_min = targets['AUC']['min']
                                auc_max = targets['AUC']['max']
                                if value < auc_min:
                                    st.markdown(f"❌ AUC₂₄: {value:.1f} mg·hr/L (BELOW target)")
                                elif value > auc_max:
                                    st.markdown(f"⚠️ AUC₂₄: {value:.1f} mg·hr/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ AUC₂₄: {value:.1f} mg·hr/L (within target)")
                            
                            elif parameter == 'trough':
                                trough_min = targets['trough']['min']
                                trough_max = targets['trough']['max']
                                if value < trough_min:
                                    st.markdown(f"❌ Trough: {value:.1f} mg/L (BELOW target)")
                                elif value > trough_max:
                                    st.markdown(f"⚠️ Trough: {value:.1f} mg/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ Trough: {value:.1f} mg/L (within target)")
                                    
                            elif parameter == 'peak':
                                st.markdown(f"Peak: {value:.1f} mg/L")
                    
                    with col2:
                        st.markdown("**Recommended Regimen:**")
                        st.success(new_regimen)
                        
                        # Display predicted levels with appropriate indicators
                        predicted_new_levels = best_regimen['predicted_levels']
                        for parameter, value in predicted_new_levels.items():
                            if parameter == 'auc':
                                auc_min = targets['AUC']['min']
                                auc_max = targets['AUC']['max']
                                if value < auc_min:
                                    st.markdown(f"❌ AUC₂₄: {value:.1f} mg·hr/L (BELOW target)")
                                elif value > auc_max:
                                    st.markdown(f"⚠️ AUC₂₄: {value:.1f} mg·hr/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ AUC₂₄: {value:.1f} mg·hr/L (within target)")
                            
                            elif parameter == 'trough':
                                trough_min = targets['trough']['min']
                                trough_max = targets['trough']['max']
                                if value < trough_min:
                                    st.markdown(f"❌ Trough: {value:.1f} mg/L (BELOW target)")
                                elif value > trough_max:
                                    st.markdown(f"⚠️ Trough: {value:.1f} mg/L (ABOVE target)")
                                else:
                                    st.markdown(f"✅ Trough: {value:.1f} mg/L (within target)")
                                    
                            elif parameter == 'peak':
                                st.markdown(f"Peak: {value:.1f} mg/L")
                    
                    # Display clinical reasoning
                    st.markdown("### Clinical Reasoning")
                    st.markdown(best_regimen['reasoning'])
                    
                    # Clinical interpretation
                    interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)

                    # First assess current levels
                    current_assessment, current_status = interpreter.assess_levels(measured_levels)

                    # Then assess predicted new levels
                    new_assessment, new_status = interpreter.assess_levels(predicted_new_levels)

                    # Generate recommendations based on the NEW predicted levels
                    recommendations = interpreter.generate_recommendations(new_status, patient_data['crcl'])
                    
                    # Add resampling recommendation
                    resampling_rec = interpreter.recommend_resampling_date(
                        best_regimen['interval'], 
                        new_status, 
                        patient_data['crcl']
                    )
                    recommendations.append(resampling_rec)

                    st.markdown("### Clinical Interpretation")
                    interpretation = interpreter.format_recommendations_for_regimen_change(
                        old_regimen,
                        measured_levels,
                        new_regimen,
                        predicted_new_levels, 
                        patient_data
                    )
                    st.markdown(interpretation)

                    # Generate and display print button
                    report = UIComponents.generate_report(
                        "Vancomycin",
                        f"{regimen} therapy - Peak/Trough adjustment",
                        patient_data,
                        individual_params,
                        measured_levels,
                        f"Changed from {old_regimen} to {new_regimen}",
                        interpretation
                    )
                    UIComponents.create_print_button(report)

                    # Visualize the predicted concentration-time curves
                    st.markdown("### Predicted Concentration-Time Profiles")
                    tab1, tab2 = st.tabs(["Current Regimen", "New Regimen"])

                    with tab1:
                        PKVisualizer.display_pk_chart(
                            individual_params,
                            measured_levels,
                            {'tau': current_interval, 'infusion_duration': infusion_duration},
                            key_suffix="current_pt"
                        )

                    with tab2:
                        PKVisualizer.display_pk_chart(
                            individual_params,
                            predicted_new_levels,
                            {'tau': best_regimen['interval'], 'infusion_duration': infusion_duration},
                            key_suffix="new_pt"
                        )
                else:
                    st.error("Could not determine optimal dosing regimen. Please check input values.")
            except Exception as e:
                st.error(f"An error occurred during calculations: {str(e)}")
                st.info("Please verify that all input values are clinically reasonable.")
