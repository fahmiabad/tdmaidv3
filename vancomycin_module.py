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
        st.title("🧪 Vancomycin Dosing")
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
        
        # Recommend interval based on CrCl
        crcl = patient_data['crcl']
        recommended_interval = VancomycinModule._get_recommended_interval(crcl)
            
        interval_options = [8, 12, 24, 36, 48]
        recommended_index = interval_options.index(recommended_interval) if recommended_interval in interval_options else 1
        
        col1, col2 = st.columns(2)
        with col1:
            interval = st.selectbox(
                "Recommended Interval (hr)", 
                interval_options, 
                index=recommended_index,
                help=f"Interval of {recommended_interval}h suggested based on CrCl of {crcl} mL/min"
            )
        with col2:
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
            VancomycinModule._generate_clinical_interpretation(
                "Vancomycin",
                regimen,
                targets,
                pk_params,
                predicted_levels,
                f"Recommended dose: {practical_dose} mg every {interval} hours",
                patient_data,
                infusion_duration,
                interval
            )
    
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
        
        # Display target ranges
        trough_min, trough_max = VancomycinModule._get_trough_range(regimen)
        st.info(f"{regimen.capitalize()} therapy target trough range: {trough_min}-{trough_max} mg/L")
        
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
            
            # Calculate new dose recommendation
            best_rec = VancomycinModule._calculate_best_dosing_recommendation(
                calculator, adjusted_params, target_auc, trough_min, trough_max, 
                infusion_duration, patient_data['crcl']
            )
            
            # Display recommendations
            old_regimen = f"{current_dose} mg every {current_interval} hours"
            new_regimen = f"{best_rec['dose']} mg every {best_rec['interval']} hours"
            
            VancomycinModule._display_regimen_comparison(
                old_regimen, new_regimen,
                measured_trough=measured_trough,
                current_auc=current_auc,
                predicted_trough=best_rec['predicted_trough'],
                predicted_auc=best_rec['predicted_auc']
            )
            
            # Generate new levels dictionary for the clinical interpretation
            predicted_new_levels = {
                'peak': best_rec['predicted_peak'],
                'trough': best_rec['predicted_trough'],
                'auc': best_rec['predicted_auc']
            }
            
            # Generate clinical interpretation
            interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
            
            # First assess current levels
            current_levels = {
                'peak': predicted_levels['peak'], 
                'trough': measured_trough,
                'auc': current_auc
            }
            
            VancomycinModule._generate_regimen_comparison_interpretation(
                "Vancomycin", 
                regimen, 
                targets, 
                adjusted_params, 
                current_levels, 
                predicted_new_levels,
                old_regimen,
                new_regimen,
                patient_data,
                current_interval,
                best_rec['interval'],
                current_dose,
                best_rec['dose'],
                infusion_duration
            )
    
    @staticmethod
    def _adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Peak & Trough")
        
        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0)
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12)
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)
        
        # Display target ranges
        trough_min, trough_max = VancomycinModule._get_trough_range(regimen)
        st.info(f"{regimen.capitalize()} therapy target trough range: {trough_min}-{trough_max} mg/L")
        
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
        
        if st.button("Calculate PK Parameters"):
            try:
                # Calculate PK parameters from the two concentrations
                individual_params, measured_levels = VancomycinModule._calculate_individual_pk_params(
                    calculator, current_dose, current_interval, infusion_duration, 
                    measured_peak, measured_trough, t_peak, t_trough
                )
                
                # Display results using consistent format
                UIComponents.display_results(
                    individual_params,
                    measured_levels,
                    ""
                )
                
                # Calculate new dose recommendation
                if individual_params['cl'] > 0:
                    best_rec = VancomycinModule._calculate_best_dosing_recommendation_individual(
                        calculator, individual_params, target_auc, trough_min, trough_max, 
                        infusion_duration, patient_data['crcl']
                    )
                    
                    # Generate display and interpretation
                    old_regimen = f"{current_dose} mg every {current_interval} hours"
                    new_regimen = f"{best_rec['dose']} mg every {best_rec['interval']} hours"
                    
                    # Full regimen comparison display
                    VancomycinModule._display_regimen_comparison(
                        old_regimen, new_regimen,
                        measured_peak=measured_peak,
                        measured_trough=measured_trough,
                        current_auc=measured_levels['auc'],
                        predicted_peak=best_rec['predicted_peak'],
                        predicted_trough=best_rec['predicted_trough'],
                        predicted_auc=best_rec['predicted_auc']
                    )
                    
                    # Generate new levels dictionary for the clinical interpretation
                    predicted_new_levels = {
                        'peak': best_rec['predicted_peak'],
                        'trough': best_rec['predicted_trough'],
                        'auc': best_rec['predicted_auc']
                    }
                    
                    VancomycinModule._generate_regimen_comparison_interpretation(
                        "Vancomycin", 
                        regimen, 
                        targets, 
                        individual_params, 
                        measured_levels, 
                        predicted_new_levels,
                        old_regimen,
                        new_regimen,
                        patient_data,
                        current_interval,
                        best_rec['interval'],
                        current_dose,
                        best_rec['dose'],
                        infusion_duration
                    )
                else:
                    st.error("Unable to calculate new dose due to invalid clearance calculation")
                
            except Exception as e:
                st.error(f"Calculation error: {e}")
                st.info("Please verify that sampling times and concentration values are correct.")
    
    # Helper methods to reduce code duplication
    
    @staticmethod
    def _get_recommended_interval(crcl):
        """Get recommended interval based on creatinine clearance"""
        if crcl < 20:
            return 48
        elif crcl < 30:
            return 36
        elif crcl < 40:
            return 24
        elif crcl < 60:
            return 12
        else:
            return 8
    
    @staticmethod
    def _get_trough_range(regimen):
        """Get trough range based on regimen type"""
        if regimen == "empiric":
            return 10, 15
        else:  # definitive
            return 15, 20
    
    @staticmethod
    def _calculate_individual_pk_params(calculator, current_dose, current_interval, infusion_duration, 
                                        measured_peak, measured_trough, t_peak, t_trough):
        """Calculate individual PK parameters from peak and trough measurements"""
        # Handle two scenarios:
        # 1. Pre/Post levels around a single dose (trough before dose, peak after dose)
        # 2. Traditional PK (trough at end of interval, peak after dose)
        
        if t_trough < 0 and t_peak > 0:
            # Scenario 1: Pre/Post levels around a single dose
            # Trough is pre-dose, peak is post-dose
            st.info("Using Pre/Post level calculation")
            
            # Calculate ke using the peak to trough decline over one dosing interval
            # Peak occurs at t_peak, next trough would occur at (current_interval + t_trough)
            delta_t = current_interval - t_peak + abs(t_trough)
            
            if delta_t <= 0:
                raise ValueError("Invalid time calculations. Please check your sampling times.")
            
            # Calculate ke from peak to next trough projection
            ke_ind = math.log(measured_peak / measured_trough) / delta_t
            ke_ind = max(1e-6, abs(ke_ind))  # Ensure positive ke
            t_half_ind = 0.693 / ke_ind
            
            # Calculate Vd from peak concentration
            if t_peak > infusion_duration:
               # Back extrapolate to find Cmax at end of infusion
                cmax_ind = measured_peak * math.exp(ke_ind * (t_peak - infusion_duration))
            else:
                # Peak is during infusion - estimate Cmax
                cmax_ind = measured_peak / (t_peak / infusion_duration)
            
            # Calculate Cmin at end of interval
            cmin_ind = cmax_ind * math.exp(-ke_ind * (current_interval - infusion_duration))
            
        else:
            # Scenario 2: Traditional PK (both levels after dose)
            st.info("Using traditional PK calculation")
            
            # Handle next day scenario if needed
            if t_peak < 0:
                t_peak += 24
            if t_trough < 0:
                t_trough += 24
            
            # Calculate delta time between measurements
            if t_trough < t_peak:
                delta_t = t_peak - t_trough
            else:
                delta_t = (current_interval - t_trough) + t_peak
            
            if delta_t <= 0:
                raise ValueError("Invalid time calculations. Please check your sampling times.")
            
            ke_ind = (math.log(measured_peak) - math.log(measured_trough)) / delta_t
            ke_ind = max(1e-6, abs(ke_ind))  # Ensure positive ke
            t_half_ind = 0.693 / ke_ind
            
            # Calculate Cmax and Cmin
            if t_peak > infusion_duration:
                cmax_ind = measured_peak * math.exp(ke_ind * (t_peak - infusion_duration))
            else:
                cmax_ind = measured_peak / (t_peak / infusion_duration)
            
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
        
        return individual_params, measured_levels
    
    @staticmethod
    def _calculate_best_dosing_recommendation(calculator, pk_params, target_auc, trough_min, trough_max, 
                                             infusion_duration, crcl):
        """Calculate best dosing recommendation based on adjusted PK parameters"""
        # Logic to determine optimal interval based on t_half and clinical factors
        interval_options = [8, 12, 24, 36, 48]
        
        # Start with CrCl-based recommendation
        recommended_interval = VancomycinModule._get_recommended_interval(crcl)
        st.info(f"Based on CrCl of {crcl} mL/min, a dosing interval of {recommended_interval}h is generally recommended")
        
        # Prepare all possible dosing recommendations
        all_recommendations = []
        for potential_interval in interval_options:
            # Calculate dose needed to achieve target AUC
            target_daily_dose = target_auc * pk_params['cl']
            dose_per_interval = target_daily_dose / (24 / potential_interval)
            practical_dose = calculator._round_dose(dose_per_interval)
            
            # Predict new levels with this dose
            new_levels = calculator.predict_levels(practical_dose, potential_interval, infusion_duration)
            new_auc = calculator.calculate_vancomycin_auc(
                new_levels['peak'],
                new_levels['trough'],
                pk_params['ke'],
                potential_interval,
                infusion_duration
            )
            
            # Calculate how well this matches our targets
            auc_match = abs(new_auc - target_auc) / target_auc
            
            # Check if trough is within range instead of distance from a specific target
            trough_in_range = trough_min <= new_levels['trough'] <= trough_max
            
            # If trough not in range, calculate distance from nearest boundary
            if not trough_in_range:
                if new_levels['trough'] < trough_min:
                    trough_match = (trough_min - new_levels['trough']) / trough_min
                else:  # trough > trough_max
                    trough_match = (new_levels['trough'] - trough_max) / trough_max
            else:
                trough_match = 0  # No penalty if in range
            
            # Weight AUC more heavily, but ensure trough is in range
            match_score = (auc_match * 0.7) + (trough_match * 1.3)
            
            # Adjust score if trough is way out of range
            if new_levels['trough'] < trough_min * 0.8 or new_levels['trough'] > trough_max * 1.2:
                match_score += 1  # Significant penalty
            
            all_recommendations.append({
                'interval': potential_interval,
                'dose': practical_dose,
                'predicted_auc': new_auc,
                'predicted_trough': new_levels['trough'],
                'predicted_peak': new_levels['peak'],
                'auc_match': auc_match,
                'trough_match': trough_match,
                'match_score': match_score,  # Lower is better
                'trough_in_range': trough_in_range
            })
        
        # Sort by match score (best match first)
        all_recommendations.sort(key=lambda x: x['match_score'])
        
        # Check if we have any recommendations with trough in range - prioritize these
        in_range_recs = [rec for rec in all_recommendations if rec['trough_in_range']]
        
        # If we have in-range recommendations, prefer those over out-of-range ones
        if in_range_recs:
            display_recs = in_range_recs[:3]
            st.success(f"Found {len(in_range_recs)} recommendations with trough in target range ({trough_min}-{trough_max} mg/L)")
        else:
            display_recs = all_recommendations[:3]
            st.warning(f"No recommendations have trough exactly in target range ({trough_min}-{trough_max} mg/L). Showing closest matches.")
        
        # Display top recommendations in a table
        st.subheader("Dosing Options (Best Match First)")
        rec_data = []
        
        for i, rec in enumerate(display_recs):
            trough_status = "✅ In range" if rec['trough_in_range'] else "❌ Out of range"
            
            rec_data.append({
                "Rank": i+1,
                "Dose (mg)": rec['dose'],
                "Interval (hr)": rec['interval'],
                "Predicted AUC": f"{rec['predicted_auc']:.1f}",
                "Predicted Trough": f"{rec['predicted_trough']:.1f}",
                "Trough Status": trough_status
            })
        
        st.table(rec_data)
        
        # Return the best recommendation
        return display_recs[0]
        in_range_recs = [rec for rec in all_recommendations if rec['trough_in_range']]
        
        # If we have in-range recommendations, prefer those over out-of-range ones
        if in_range_recs:
            display_recs = in_range_recs[:3]
            st.success(f"Found {len(in_range_recs)} recommendations with trough in target range ({trough_min}-{trough_max} mg/L)")
        else:
            display_recs = all_recommendations[:3]
            st.warning(f"No recommendations have trough exactly in target range ({trough_min}-{trough_max} mg/L). Showing closest matches.")
        
        # Display top recommendations in a table
        st.subheader("Dosing Options (Best Match First)")
        rec_data = []
        
        for i, rec in enumerate(display_recs):
            trough_status = "✅ In range" if rec['trough_in_range'] else "❌ Out of range"
            
            rec_data.append({
                "Rank": i+1,
                "Dose (mg)": rec['dose'],
                "Interval (hr)": rec['interval'],
                "Predicted AUC": f"{rec['predicted_auc']:.1f}",
                "Predicted Trough": f"{rec['predicted_trough']:.1f}",
                "Trough Status": trough_status
            })
        
        st.table(rec_data)
        
        # Return the best recommendation
        return display_recs[0]
    
    @staticmethod
    def _calculate_best_dosing_recommendation_individual(calculator, pk_params, target_auc, trough_min, trough_max, 
                                                        infusion_duration, crcl):
        """Calculate best dosing recommendation based on individual PK parameters"""
        interval_options = [8, 12, 24, 36, 48]
        recommended_interval = VancomycinModule._get_recommended_interval(crcl)
        st.info(f"Based on CrCl of {crcl} mL/min, a dosing interval of {recommended_interval}h is generally recommended")
        
        # Prepare all possible dosing recommendations
        all_recommendations = []
        
        for potential_interval in interval_options:
            # Calculate dose needed to achieve target AUC
            target_daily_dose = target_auc * pk_params['cl']
            dose_per_interval = target_daily_dose / (24 / potential_interval)
            practical_dose = calculator._round_dose(dose_per_interval)
            
            # For simplicity, calculate peak and trough using individual PK parameters
            ke = pk_params['ke']
            vd = pk_params['vd']
            
            # Calculate peak (Cmax) at end of infusion
            term1 = (practical_dose / (vd * ke * infusion_duration))
            term2 = (1 - math.exp(-ke * infusion_duration))
            term3 = (1 / (1 - math.exp(-ke * potential_interval)))
            peak_ind = term1 * term2 * term3
            
            # Calculate trough (Cmin) just before next dose
            trough_ind = peak_ind * math.exp(-ke * (potential_interval - infusion_duration))
            
            # Calculate new AUC
            new_auc = calculator.calculate_vancomycin_auc(
                peak_ind,
                trough_ind,
                ke,
                potential_interval,
                infusion_duration
            )
            
            # Check if trough is within range
            trough_in_range = trough_min <= trough_ind <= trough_max
            
            # Calculate match scores
            auc_match = abs(new_auc - target_auc) / target_auc
            
            # If trough not in range, calculate distance from nearest boundary
            if not trough_in_range:
                if trough_ind < trough_min:
                    trough_match = (trough_min - trough_ind) / trough_min
                else:  # trough > trough_max
                    trough_match = (trough_ind - trough_max) / trough_max
            else:
                trough_match = 0  # No penalty if in range
            
            # Weight AUC more heavily, but ensure trough is in range
            match_score = (auc_match * 0.7) + (trough_match * 1.3)
            
            # Adjust score if trough is way out of range
            if trough_ind < trough_min * 0.8 or trough_ind > trough_max * 1.2:
                match_score += 1  # Significant penalty
            
            all_recommendations.append({
                'interval': potential_interval,
                'dose': practical_dose,
                'predicted_auc': new_auc,
                'predicted_trough': trough_ind,
                'predicted_peak': peak_ind,
                'auc_match': auc_match,
                'trough_match': trough_match,
                'match_score': match_score,  # Lower is better
                'trough_in_range': trough_in_range
            })
        
        # Sort by match score (best match first)
        all_recommendations.sort(key=lambda x: x['match_score'])
        
        # Check if we have any recommendations with trough in range - prioritize these
