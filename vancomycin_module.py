# vancomycin_module.py
import streamlit as st
import math
# Assume these imports exist and are correct
# from pk_calculations import PKCalculator
# from clinical_logic import ClinicalInterpreter
# from visualization import PKVisualizer
# from ui_components import UIComponents
# from config import DRUG_CONFIGS

# Placeholder classes/functions if the actual ones are not available
# Replace these with your actual imports
class PKCalculator:
    def __init__(self, drug, weight, crcl): self.drug = drug; self.weight = weight; self.crcl = crcl
    def calculate_initial_parameters(self): return {'ke': 0.1, 't_half': 6.9, 'vd': 50.0, 'cl': 5.0}
    def predict_levels(self, dose, interval, infusion_duration): return {'peak': 30.0, 'trough': 10.0}
    def predict_levels_with_params(self, params, dose, interval, infusion_duration):
        ke = params['ke']
        vd = params['vd']
        T = infusion_duration
        tau = interval
        term_inf = 1 - math.exp(-ke * T)
        term_tau = 1 - math.exp(-ke * tau)
        if abs(term_tau) < 1e-9: term_tau = 1e-9
        if abs(ke) < 1e-9: ke = 1e-9
        if vd <=0: vd = 50 # Failsafe

        cmax = (dose / (vd * ke * T)) * term_inf / term_tau if T > 0 else 0
        cmin = cmax * math.exp(-ke * (tau - T))
        return {'peak': cmax, 'trough': cmin}

    def calculate_vancomycin_auc(self, peak, trough, ke, interval, infusion_duration):
        # Using Dose/CL method assuming CL is derived correctly
        # AUC = Dose / CL = Dose / (ke * Vd)
        # Or using trapezoidal rule approx:
        # AUC_interval = Dose / (ke * Vd) # Needs Vd
        # A simpler approximation often used: AUC = Dose / CL
        # Let's use Dose/CL if possible, requires calculating CL first.
        # If CL is available from params: return (dose / interval) * 24 / cl
        # For now, let's assume a simple linear-log trapezoidal based on peak/trough if ke is known
        # This isn't strictly trapezoidal but uses the levels.
        # A common clinical approximation: AUC = (Peak + Trough)/2 * interval - needs validation
        # Using Dose/CL derived from the levels:
        cl = ke * self.calculate_vd_from_levels(peak, trough, ke, interval, infusion_duration, 1000) # Assume 1000mg dose for calculation
        if cl > 0:
             # Need the actual dose that produced these levels
             # Let's fall back to a basic estimate or require CL
             # AUC24 = CL * TargetAUC / CL = TargetAUC? No.
             # AUC per interval = Dose / CL
             # For now return a placeholder calculation based on levels
             try:
                 # Approximate AUC for one interval using linear-log trapezoid idea
                 # Area during infusion (approx linear) + Area during elimination (log)
                 auc_inf = (peak / 2) * infusion_duration # Very rough
                 # Need concentration at start of elimination C(T) = peak
                 # Need concentration at end C(tau) = trough
                 time_elim = interval - infusion_duration
                 if time_elim > 0 and ke > 0:
                     auc_elim = (peak - trough) / ke
                 else:
                     auc_elim = 0
                 auc_interval = auc_inf + auc_elim # Still very approximate
                 return auc_interval * (24 / interval) # Scale to AUC24
             except:
                 return 400 # Fallback
        else:
             return 400 # Fallback estimate

    def calculate_vd_from_levels(self, peak, trough, ke, interval, infusion_duration, dose):
         # Estimate Vd from Cmax/Cmin
         T = infusion_duration
         tau = interval
         cmax_ss = peak
         cmin_ss = trough
         term_inf = 1 - math.exp(-ke * T)
         term_tau = 1 - math.exp(-ke * tau)
         if abs(term_tau) < 1e-9 or abs(ke) < 1e-9 or T <= 0 or cmax_ss <= 0: return 50 # Failsafe
         try:
            vd = (dose / (cmax_ss * ke * T)) * term_inf / term_tau
            return vd if vd > 0 else 50
         except:
            return 50 # Failsafe

    def _round_dose(self, dose): return round(dose / 250) * 250 if dose > 0 else 250

class ClinicalInterpreter:
    def __init__(self, drug, regimen, targets): self.drug = drug; self.regimen = regimen; self.targets = targets
    def assess_levels(self, levels): return "Assessment placeholder", "Status placeholder"
    def generate_recommendations(self, status, crcl): return ["Recommendation placeholder"]
    def format_recommendations(self, assessment, status, recommendations, patient_data): return f"**Assessment:** {assessment}\n**Status:** {status}\n**Recommendations:**\n- {' '.join(recommendations)}"

class PKVisualizer:
    @staticmethod
    def display_pk_chart(pk_params, levels, dose_info): st.write("PK Chart Placeholder")

class UIComponents:
    @staticmethod
    def display_results(params, levels, recommendation):
        st.write("---")
        st.subheader("Calculated PK Parameters")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Elimination Rate (ke)", f"{params.get('ke', 0):.3f} hr⁻¹")
            st.metric("Volume of Distribution (Vd)", f"{params.get('vd', 0):.1f} L")
        with col2:
            st.metric("Half-life (t½)", f"{params.get('t_half', 0):.1f} hr")
            st.metric("Clearance (CL)", f"{params.get('cl', 0):.2f} L/hr")

        st.subheader("Levels")
        col1, col2, col3 = st.columns(3)
        peak_val = levels.get('peak', 0)
        trough_val = levels.get('trough', 0)
        auc_val = levels.get('auc', 0)
        with col1:
            st.metric("Est. Peak", f"{peak_val:.1f} mg/L")
            if 'measured_peak_conc' in levels:
                 st.caption(f"Measured: {levels['measured_peak_conc']:.1f} mg/L at {levels.get('peak_sample_time_rel', ''):.1f} hr post-dose")
        with col2:
            st.metric("Est. Trough", f"{trough_val:.1f} mg/L")
            if 'measured_trough_conc' in levels:
                 st.caption(f"Measured: {levels['measured_trough_conc']:.1f} mg/L at {abs(levels.get('trough_sample_time_rel', '')):.1f} hr pre-dose")
        with col3:
            st.metric("Est. AUC₂₄", f"{auc_val:.1f} mg·hr/L")

        if recommendation:
            st.success(recommendation)
        st.write("---")

    @staticmethod
    def create_time_input(label, default_hour, default_minute, key):
        cols = st.columns([0.6, 0.2, 0.2])
        with cols[0]:
            st.write(label)
        with cols[1]:
            hour = st.number_input("H", 0, 23, default_hour, format="%02d", key=f"{key}_hr")
        with cols[2]:
            minute = st.number_input("M", 0, 59, default_minute, format="%02d", key=f"{key}_min")
        display = f"{hour:02d}:{minute:02d}"
        return hour, minute, display

    @staticmethod
    def calculate_time_difference(h1, m1, h2, m2):
        # Simple difference in hours, can be negative
        time1_minutes = h1 * 60 + m1
        time2_minutes = h2 * 60 + m2
        diff_minutes = time2_minutes - time1_minutes
        # Handle wrap around midnight? No, keep simple difference for relative calc.
        return diff_minutes / 60.0

    @staticmethod
    def generate_report(*args): return "Report Content Placeholder"
    @staticmethod
    def create_print_button(report_content): st.button("Print Report")

DRUG_CONFIGS = {
    "Vancomycin": {
        "regimens": {
            "empiric": {"targets": {"auc": (400, 600), "trough": (10, 15)}},
            "definitive": {"targets": {"auc": (400, 600), "trough": (15, 20)}}
        }
    }
}
# End Placeholder definitions


class VancomycinModule:
    @staticmethod
    def auc_dosing(patient_data):
        st.title("🧪 Vancomycin AUC-Based Dosing")
        st.info("AUC24 is calculated using the Linear-Log Trapezoidal method (approximation)")

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

        # Use placeholder patient data if not provided
        if not patient_data:
             patient_data = {'weight': 70, 'crcl': 80}

        calculator = PKCalculator("Vancomycin", patient_data.get('weight', 70), patient_data.get('crcl', 80))

        if method == "Calculate Initial Dose":
            VancomycinModule._initial_dose(calculator, target_auc, targets, regimen, patient_data)
        elif method == "Adjust Using Trough":
            VancomycinModule._adjust_with_trough(calculator, target_auc, targets, regimen, patient_data)
        else:
            # Ensure unique keys for widgets within this branch if they might conflict
            # with other branches when method changes. Add suffixes like '_pt'.
            VancomycinModule._adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data, key_suffix='_pt')

    @staticmethod
    def _initial_dose(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Initial Dose Calculation")

        interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48], index=1, key="initial_interval")
        infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0, key="initial_infusion")

        # Population PK estimates
        pk_params = calculator.calculate_initial_parameters()

        # Calculate dose for target AUC
        target_daily_dose = target_auc * pk_params['cl']
        dose_per_interval = target_daily_dose / (24 / interval)
        practical_dose = calculator._round_dose(dose_per_interval)

        # Predict levels
        predicted_levels = calculator.predict_levels_with_params(pk_params, practical_dose, interval, infusion_duration)
        predicted_auc = calculator.calculate_vancomycin_auc(
            predicted_levels['peak'],
            predicted_levels['trough'],
            pk_params['ke'],
            interval,
            infusion_duration
            # Pass dose for potential Dose/CL AUC calculation inside the method
            # dose=practical_dose, cl=pk_params['cl']
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
        if st.button("Generate Clinical Interpretation", key="initial_interpret"):
            interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
            assessment, status = interpreter.assess_levels(predicted_levels)
            recommendations = interpreter.generate_recommendations(status, patient_data.get('crcl', 80))

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
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0, key="trough_dose")
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12, key="trough_interval")
        with col2:
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0, key="trough_measured")
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0, key="trough_infusion")

        # Optional timing information for better context
        st.markdown("##### Timing Information (optional, for context)")
        include_timing = st.checkbox("Include specific dose and trough times?", key="trough_timing_cb")

        t_trough_context = None
        if include_timing:
            col1, col2 = st.columns(2)
            with col1:
                dose_hour, dose_minute, dose_display = UIComponents.create_time_input("Dose Start Time", 9, 0, key="trough_dose_time")
                st.info(f"Dose given at: {dose_display}")
            with col2:
                trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key="trough_sample_time")
                st.info(f"Trough drawn at: {trough_display}")

            # Calculate time difference for context (not used in core calculation here)
            t_trough_context = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)
            st.info(f"Time from dose start to trough sample: {t_trough_context:.1f} hours") # Should be negative if trough is before dose

        if st.button("Calculate PK Parameters & Adjust Dose", key="trough_calculate"):
            # Estimate parameters using population Vd and measured trough
            pk_params_pop = calculator.calculate_initial_parameters()
            vd_pop = pk_params_pop['vd'] # Use population Vd estimate

            # Estimate CL based on trough using ratio method (simplified)
            # Predict trough using population CL and Vd
            predicted_trough_pop = calculator.predict_levels_with_params(
                 pk_params_pop, current_dose, current_interval, infusion_duration
            )['trough']

            cl_adjusted = pk_params_pop['cl'] # Start with population CL
            if predicted_trough_pop > 0.1 and measured_trough > 0.1:
                # Adjust CL proportionally to the difference between predicted and measured trough
                cl_ratio = measured_trough / predicted_trough_pop
                # Avoid extreme adjustments, maybe cap the ratio e.g., 0.2 to 5
                cl_ratio = max(0.2, min(cl_ratio, 5.0))
                # CL is inversely proportional to trough concentration
                cl_adjusted = pk_params_pop['cl'] / cl_ratio
            else:
                 st.warning("Cannot adjust CL based on trough ratio (predicted or measured trough is too low). Using population CL.")
                 cl_adjusted = pk_params_pop['cl']

            # Ensure CL is realistic
            cl_adjusted = max(0.1, cl_adjusted) # Ensure CL is at least 0.1 L/hr

            ke_adjusted = cl_adjusted / vd_pop # Ke based on adjusted CL and pop Vd
            ke_adjusted = max(1e-6, ke_adjusted) # Ensure positive ke
            t_half_adjusted = 0.693 / ke_adjusted

            adjusted_params = {
                'ke': ke_adjusted,
                't_half': t_half_adjusted,
                'vd': vd_pop, # Keep population Vd
                'cl': cl_adjusted
            }

            # Calculate current estimated Peak and AUC with adjusted params
            # Use measured trough as the Cmin
            cmin_current = measured_trough
            # Extrapolate Cmax from measured trough
            cmax_current = cmin_current / math.exp(-ke_adjusted * (current_interval - infusion_duration))

            current_auc = calculator.calculate_vancomycin_auc(
                cmax_current,
                cmin_current,
                ke_adjusted,
                current_interval,
                infusion_duration
                # Pass dose/cl if needed by AUC calc
                # dose=current_dose, cl=cl_adjusted
            )

            current_levels_display = {
                'peak': cmax_current,   # Estimated peak based on measured trough
                'trough': cmin_current, # Measured trough
                'auc': current_auc,
                'measured_trough_conc': measured_trough # Store actual measured value
            }

            # Display results using consistent format
            UIComponents.display_results(
                adjusted_params,
                current_levels_display,
                ""
            )

            # Calculate new dose
            st.markdown("### Dose Adjustment")
            # Ensure unique key for selectbox
            desired_interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48],
                                            index=[8, 12, 24, 36, 48].index(current_interval) if current_interval in [8, 12, 24, 36, 48] else 1,
                                            key="trough_desired_interval")

            if cl_adjusted > 0:
                new_daily_dose = target_auc * cl_adjusted
                new_dose_interval = new_daily_dose / (24 / desired_interval)
                practical_new_dose = calculator._round_dose(new_dose_interval)

                recommendation = f"Suggested new dose: {practical_new_dose} mg every {desired_interval} hours"
                st.success(recommendation)

                # Predict levels for the new dose
                predicted_new_levels = calculator.predict_levels_with_params(
                    adjusted_params, practical_new_dose, desired_interval, infusion_duration
                )
                predicted_new_auc = calculator.calculate_vancomycin_auc(
                    predicted_new_levels['peak'],
                    predicted_new_levels['trough'],
                    adjusted_params['ke'],
                    desired_interval,
                    infusion_duration
                    # Pass dose/cl if needed
                    # dose=practical_new_dose, cl=adjusted_params['cl']
                )
                predicted_new_levels['auc'] = predicted_new_auc

                st.write("Predicted levels for the new dose:")
                st.write(f"- Est. Peak: {predicted_new_levels['peak']:.1f} mg/L")
                st.write(f"- Est. Trough: {predicted_new_levels['trough']:.1f} mg/L")
                st.write(f"- Est. AUC₂₄: {predicted_new_levels['auc']:.1f} mg·hr/L")

                # Clinical interpretation based on current levels (using measured trough)
                interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
                assessment_levels = {'trough': measured_trough, 'auc': current_auc}
                assessment, status = interpreter.assess_levels(assessment_levels)
                recommendations = interpreter.generate_recommendations(status, patient_data.get('crcl', 80))

                st.markdown("### Clinical Interpretation (Based on Current Dose)")
                interpretation = interpreter.format_recommendations(assessment, status, recommendations, patient_data)
                st.markdown(interpretation)

                # Generate and display print button
                report = UIComponents.generate_report(
                    "Vancomycin",
                    f"{regimen} therapy - Trough adjustment",
                    patient_data,
                    adjusted_params,
                    current_levels_display,
                    recommendation,
                    interpretation
                )
                UIComponents.create_print_button(report)
            else:
                 st.error("Unable to calculate new dose due to invalid clearance calculation")


    @staticmethod
    def _adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data, key_suffix=''):
        """ Adjusts dose using measured peak and trough levels. """
        st.markdown("### Dose Adjustment Using Peak & Trough")

        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0, key=f"pt_dose{key_suffix}")
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12, key=f"pt_interval{key_suffix}")
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0, key=f"pt_infusion{key_suffix}")

        # Dose administration time
        st.subheader("Dose Administration Time")
        dose_hour, dose_minute, dose_display = UIComponents.create_time_input("Dose Start Time", 9, 0, key=f"pt_dose_time{key_suffix}")
        st.info(f"Dose given at: {dose_display}")

        # Sampling times and concentrations
        st.subheader("Sampling Times & Measured Concentrations")
        col1, col2 = st.columns(2)
        with col1:
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0, key=f"pt_trough_conc{key_suffix}")
            trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key=f"pt_trough_sample_time{key_suffix}")
            st.info(f"Trough drawn at: {trough_display} (Should be before Dose Start Time)")
        with col2:
            measured_peak = st.number_input("Measured Peak (mg/L)", 0.1, 100.0, 30.0, key=f"pt_peak_conc{key_suffix}")
            peak_hour, peak_minute, peak_display = UIComponents.create_time_input("Peak Sample Time", 11, 0, key=f"pt_peak_sample_time{key_suffix}")
            st.info(f"Peak drawn at: {peak_display} (Should be after Dose Start Time)")

        # Calculate time differences RELATIVE TO DOSE START
        # t_peak_rel: Time from dose start to peak sample
        # t_trough_rel: Time from dose start to trough sample
        t_peak_rel = UIComponents.calculate_time_difference(dose_hour, dose_minute, peak_hour, peak_minute)
        t_trough_rel = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)

        # Display calculated relative times for user verification
        st.caption(f"Time from dose start to peak sample: {t_peak_rel:.2f} hr")
        st.caption(f"Time from dose start to trough sample: {t_trough_rel:.2f} hr")


        if st.button("Calculate PK Parameters & Adjust Dose", key=f"pt_calculate{key_suffix}"):
            # --- Start of Validation and Logic ---
            error_messages = []
            # Validate timing: Trough should be before dose, Peak should be after dose
            if t_trough_rel >= 0:
                error_messages.append("Trough level must be drawn *before* the dose start time.")
            if t_peak_rel <= 0:
                 error_messages.append("Peak level must be drawn *after* the dose start time.")
            # Validate concentrations
            if measured_peak <= 0:
                error_messages.append("Measured peak concentration must be positive.")
            if measured_trough <= 0:
                error_messages.append("Measured trough concentration must be positive.")
            if measured_peak <= measured_trough:
                 error_messages.append("Measured peak must be greater than measured trough.")
            # Validate interval and infusion
            if current_interval <= 0:
                 error_messages.append("Dosing interval must be positive.")
            if infusion_duration <= 0:
                 error_messages.append("Infusion duration must be positive.")
            if infusion_duration >= current_interval:
                 error_messages.append("Infusion duration cannot be longer than the dosing interval.")
            # Optional: Check if peak is drawn after infusion end (recommended)
            if t_peak_rel < infusion_duration:
               st.warning("Note: Peak level was drawn *during* the infusion. Calculations proceed, but post-infusion peaks generally yield more reliable Vd estimates.")

            if error_messages:
                for msg in error_messages:
                    st.error(f"Input Error: {msg}")
                return # Stop calculation if basic input errors exist

            # Calculate time points relative to the dose interval structure
            t_peak_sample_after_dose = t_peak_rel
            t_trough_sample_time_before_dose = abs(t_trough_rel) # Time from trough sample to dose start

            # Calculate the time elapsed BETWEEN the peak sample and the trough sample
            # This assumes the measured trough (before dose 'n') represents the concentration
            # at the end of the previous interval, and we are calculating the decay from the
            # peak (after dose 'n') to the next trough (before dose 'n+1').
            # Time from Peak Sample to End of Interval = current_interval - t_peak_sample_after_dose
            # Time from Start of Next Interval to Trough Sample = t_trough_sample_time_before_dose
            delta_t = (current_interval - t_peak_sample_after_dose) + t_trough_sample_time_before_dose

            if delta_t <= 0:
                st.error(f"Calculation Error: Invalid time difference between peak and trough samples ({delta_t:.2f} hours). This usually means peak time + time before next trough > interval. Please check sampling times and interval.")
                return # Stop calculation
            # --- End of Validation and Logic ---

            try:
                # Calculate individual PK parameters using the corrected delta_t
                # Ke calculation: ln(C1/C2) / delta_t = (ln(C1) - ln(C2)) / delta_t
                # Here C1=Peak, C2=Trough. Time flows from Peak sample to Trough sample.
                ke_ind = (math.log(measured_peak) - math.log(measured_trough)) / delta_t

                # Ensure ke is positive (concentration should decrease over time)
                if ke_ind <= 1e-6: # Use a small threshold to avoid issues with almost zero ke
                     st.error(f"Calculation Error: Elimination rate constant (ke) is not positive ({ke_ind:.4f}). This might indicate trough >= peak or an issue with timing calculation ({delta_t=}). Please check concentrations and times.")
                     return # Stop calculation

                t_half_ind = 0.693 / ke_ind

                # --- Calculate Vd and extrapolate true Cmax/Cmin ---
                # Extrapolate Cmax (concentration right at the end of infusion)
                cmax_ind = 0
                if t_peak_sample_after_dose >= infusion_duration:
                    # Peak drawn post-infusion: Back-extrapolate from measured_peak to end of infusion
                    time_after_infusion_end = t_peak_sample_after_dose - infusion_duration
                    cmax_ind = measured_peak * math.exp(ke_ind * time_after_infusion_end)
                else:
                    # Peak drawn during infusion: Extrapolate forward from measured_peak to end of infusion
                    time_remaining_infusion = infusion_duration - t_peak_sample_after_dose
                    # Need concentration change during remaining infusion. Requires Vd. Chicken-and-egg.
                    # Alternative: Use measured trough to estimate Cmax_ss (more robust)
                    # Assume steady state: Cmax = Cmin / exp(-ke * (tau - T))
                    cmax_ind = measured_trough / math.exp(-ke_ind * (current_interval - infusion_duration))
                    st.info("Peak was during infusion. Extrapolated Cmax from measured trough assuming steady state.")


                # Extrapolate Cmin (concentration right before next dose) from Cmax_ind
                cmin_ind = cmax_ind * math.exp(-ke_ind * (current_interval - infusion_duration))

                # Calculate Vd using the standard Sawchuk-Zaske method based on extrapolated Cmax/Cmin
                term_inf = 1 - math.exp(-ke_ind * infusion_duration)
                term_tau = 1 - math.exp(-ke_ind * current_interval)
                if abs(term_tau) < 1e-9: term_tau = 1e-9 # Avoid division by zero if interval is huge or ke is tiny

                # Vd = (Dose / (Cmax_ss * ke * T)) * (1 - exp(-ke*T)) / (1 - exp(-ke*tau))
                denom_vd = cmax_ind * ke_ind * infusion_duration * term_tau
                if abs(denom_vd) < 1e-9:
                    st.error("Calculation Error: Denominator for Vd calculation is near zero (check Cmax, ke, T, tau). Check inputs.")
                    return
                vd_ind = (current_dose * term_inf) / denom_vd

                # Ensure Vd is positive and realistic
                if vd_ind <= 0:
                     st.error(f"Calculation Error: Calculated Volume of Distribution (Vd) is not positive ({vd_ind:.2f} L). Check inputs and calculated ke/Cmax.")
                     return

                # Calculate CL
                cl_ind = ke_ind * vd_ind
                if cl_ind <= 0:
                     st.error(f"Calculation Error: Calculated Clearance (CL) is not positive ({cl_ind:.2f} L/hr). Check inputs.")
                     return

                individual_params = {
                    'ke': ke_ind,
                    't_half': t_half_ind,
                    'vd': vd_ind,
                    'cl': cl_ind
                }

                # Calculate current AUC using the derived individual parameters
                # AUC = Dose / CL (most reliable method once CL is individualized)
                # Scale to AUC24: AUC24 = (Dose / CL) * (24 / interval)
                current_auc = (current_dose / cl_ind) * (24 / current_interval) if cl_ind > 0 else 0

                # Store levels for display - use extrapolated Cmax/Cmin as they represent steady state
                measured_levels_display = {
                    'peak': cmax_ind,   # Display extrapolated peak at end of infusion
                    'trough': cmin_ind, # Display extrapolated trough right before next dose
                    'auc': current_auc,
                    'measured_peak_conc': measured_peak, # Also store actual measured values & times for context
                    'measured_trough_conc': measured_trough,
                    'peak_sample_time_rel': t_peak_sample_after_dose,
                    'trough_sample_time_rel': t_trough_rel
                }

                # Display results using consistent format
                UIComponents.display_results(
                    individual_params,
                    measured_levels_display, # Pass the dict with extrapolated values
                    ""
                )

                # --- Calculate new dose based on individual CL ---
                st.markdown("### Dose Adjustment")
                desired_interval = st.selectbox("Desired Interval (hr)", [8, 12, 24, 36, 48],
                                                index=[8, 12, 24, 36, 48].index(current_interval) if current_interval in [8, 12, 24, 36, 48] else 1,
                                                key=f"pt_desired_interval{key_suffix}") # Add unique key

                if cl_ind > 0:
                    # Target daily dose = Target AUC24 * CL
                    target_daily_dose = target_auc * cl_ind
                    # Dose per desired interval
                    new_dose_interval = target_daily_dose / (24 / desired_interval)
                    practical_new_dose = calculator._round_dose(new_dose_interval)

                    recommendation = f"Suggested new dose: {practical_new_dose} mg every {desired_interval} hours"
                    st.success(recommendation)

                    # Predict levels for the new dose using individualized parameters
                    predicted_new_levels = calculator.predict_levels_with_params(
                        individual_params, practical_new_dose, desired_interval, infusion_duration
                    )
                    # Calculate AUC for the new dose
                    predicted_new_auc = (practical_new_dose / cl_ind) * (24 / desired_interval) if cl_ind > 0 else 0
                    predicted_new_levels['auc'] = predicted_new_auc

                    st.write("Predicted levels for the new dose:")
                    st.write(f"- Est. Peak: {predicted_new_levels['peak']:.1f} mg/L")
                    st.write(f"- Est. Trough: {predicted_new_levels['trough']:.1f} mg/L")
                    st.write(f"- Est. AUC₂₄: {predicted_new_levels['auc']:.1f} mg·hr/L")


                    # Clinical interpretation using current dose's calculated AUC and extrapolated Trough
                    interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
                    # Use the *extrapolated* Cmin for assessment as it represents the true trough
                    assessment_levels = {'trough': cmin_ind, 'auc': current_auc}
                    assessment, status = interpreter.assess_levels(assessment_levels)
                    recommendations = interpreter.generate_recommendations(status, patient_data.get('crcl', 80))

                    st.markdown("### Clinical Interpretation (Based on Current Dose's Estimated PK/Levels)")
                    interpretation = interpreter.format_recommendations(assessment, status, recommendations, patient_data)
                    st.markdown(interpretation)

                    # Generate and display print button
                    report = UIComponents.generate_report(
                        "Vancomycin",
                        f"{regimen} therapy - Peak and Trough adjustment",
                        patient_data,
                        individual_params,
                        measured_levels_display, # Report extrapolated levels and AUC
                        recommendation,
                        interpretation
                    )
                    UIComponents.create_print_button(report)
                else:
                    st.error("Unable to calculate new dose due to invalid clearance calculation (CL <= 0)")

            except Exception as e:
                st.error(f"An unexpected calculation error occurred: {e}")
                st.exception(e) # Show detailed traceback for debugging
                st.info("Please double-check all input values: dose, interval, infusion duration, sampling times, and concentrations.")

# Example usage (if running this file directly)
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.sidebar.title("Patient Data")
    weight = st.sidebar.number_input("Weight (kg)", 40.0, 200.0, 70.0)
    scr = st.sidebar.number_input("Serum Creatinine (mg/dL)", 0.1, 15.0, 1.0)
    age = st.sidebar.number_input("Age (years)", 18, 100, 65)
    sex = st.sidebar.radio("Sex", ["Male", "Female"])

    # Basic CrCl calculation (Cockcroft-Gault) - replace with your preferred method
    def calculate_crcl(weight_kg, scr_mgdl, age_yr, sex):
        if scr_mgdl <= 0: return 100 # Avoid division by zero
        crcl = ((140 - age_yr) * weight_kg) / (72 * scr_mgdl)
        if sex == "Female":
            crcl *= 0.85
        return max(5, crcl) # Floor CrCl at 5

    crcl = calculate_crcl(weight, scr, age, sex)
    st.sidebar.metric("Est. CrCl (ml/min)", f"{crcl:.1f}")

    patient_data = {
        'weight': weight,
        'scr': scr,
        'age': age,
        'sex': sex,
        'crcl': crcl
    }

    VancomycinModule.auc_dosing(patient_data)
