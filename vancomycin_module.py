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
        # ... (keep existing _initial_dose code as is) ...
        st.markdown("### Initial Dose Calculation")

        # Recommend interval based on CrCl
        crcl = patient_data['crcl']
        recommended_interval = 12 # Default

        if crcl < 20:
            recommended_interval = 48
        elif crcl < 30:
            recommended_interval = 36
        elif crcl < 40:
            recommended_interval = 24
        elif crcl < 60:
            recommended_interval = 12
        else: # crcl >= 60
            recommended_interval = 8

        interval_options = [8, 12, 24, 36, 48]
        try:
            recommended_index = interval_options.index(recommended_interval)
        except ValueError:
             recommended_index = 1 # Default to 12h if calculated isn't standard

        col1, col2 = st.columns(2)
        with col1:
            interval = st.selectbox(
                "Selected Interval (hr)", # Renamed for clarity
                interval_options,
                index=recommended_index,
                help=f"Initial interval of {recommended_interval}h suggested based on CrCl of {crcl:.1f} mL/min. You can adjust if needed."
            )
        with col2:
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0, 0.25) # Allow 0.25 steps

        # Population PK estimates
        try:
            pk_params = calculator.calculate_initial_parameters()

            # Calculate dose for target AUC
            target_daily_dose = target_auc * pk_params['cl']
            dose_per_interval = target_daily_dose / (24 / interval)
            practical_dose = calculator._round_dose(dose_per_interval)

            # Predict levels
            predicted_levels = calculator.predict_levels(practical_dose, interval, infusion_duration, pk_params) # Pass params
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
                f"Recommended initial dose: **{practical_dose} mg every {interval} hours**"
            )

            # Display concentration-time curve
            PKVisualizer.display_pk_chart(
                pk_params,
                predicted_levels,
                {'tau': interval, 'infusion_duration': infusion_duration},
                key_suffix="initial_dose"
            )

            # Clinical interpretation
            if st.button("Generate Clinical Interpretation", key="interpret_initial"):
                interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)
                assessment, status = interpreter.assess_levels(predicted_levels)
                recommendations = interpreter.generate_recommendations(status, patient_data['crcl'])

                # Add standard monitoring recommendation
                recommendations.append("Recommend drawing trough level just prior to the 4th dose to assess steady state.")
                recommendations.append(f"Target AUC: {target_auc} mg·hr/L. Target Trough: {targets['trough_min']}-{targets['trough_max']} mg/L.")


                st.markdown("### Clinical Interpretation")
                interpretation = interpreter.format_recommendations(assessment, status, recommendations, patient_data)
                st.markdown(interpretation)

                # Generate and display print button
                report = UIComponents.generate_report(
                    "Vancomycin",
                    f"Initial {regimen} therapy",
                    patient_data,
                    pk_params,
                    predicted_levels,
                    f"Recommended initial dose: {practical_dose} mg every {interval} hours",
                    interpretation
                )
                UIComponents.create_print_button(report)

        except ZeroDivisionError:
            st.error("Calculation Error: Division by zero. Check if interval is > 0.")
        except ValueError as ve:
            st.error(f"Calculation Error: Invalid value ({ve}). Check inputs.")
        except Exception as e:
            st.error(f"An unexpected error occurred during initial dose calculation: {str(e)}")


    @staticmethod
    def _adjust_with_trough(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Trough")

        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0, step=50.0)
            current_interval = st.selectbox("Current Interval (hr)", [4, 6, 8, 12, 18, 24, 36, 48, 72], index=3) # Use selectbox for common intervals
        with col2:
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0, step=0.1, format="%.1f")
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0, step=0.25)

        # Display target ranges based on therapy type selected earlier
        trough_min = targets['trough_min']
        trough_max = targets['trough_max']
        st.info(f"{regimen.capitalize()} therapy target trough range: {trough_min}-{trough_max} mg/L")

        # Optional timing information (keep as is)
        st.markdown("##### Timing Information (optional, improves accuracy if available)")
        include_timing = st.checkbox("Include specific dose and trough times?", key="timing_trough")
        t_trough_actual = None # Use this if timing is provided
        if include_timing:
            col1, col2 = st.columns(2)
            with col1:
                dose_hour, dose_minute, dose_display = UIComponents.create_time_input("Dose Start Time", 9, 0, key="dose_trough")
                st.write(f"Dose given at: {dose_display}")
            with col2:
                trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key="trough_trough")
                st.write(f"Trough drawn at: {trough_display}")

            t_trough_actual = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)
            # Assume trough is drawn before the dose it relates to
            if t_trough_actual > 0:
                 t_trough_actual = t_trough_actual - current_interval # Adjust if trough drawn after the dose
            st.write(f"Time from trough draw to dose start: {abs(t_trough_actual):.1f} hours")
             # Add validation: Trough should ideally be close to end of interval
            if abs(t_trough_actual) > 2: # If drawn > 2 hours before dose time
                st.warning("Trough appears to be drawn significantly earlier than expected (just before the next dose). Results may be less accurate.")


        if st.button("Calculate Adjusted Dose", key="calc_adjust_trough"):
            try:
                # --- Calculate Individualized PK ---
                # Start with population Vd
                pop_params = calculator.calculate_initial_parameters()
                vd = pop_params['vd']

                # Estimate Ke based on trough level (using iterative approach or simplified ratio if needed)
                # This is a simplified approach. A more robust method might iterate Ke/CL
                # until predicted trough matches measured trough. Let's use the ratio method for simplicity here.

                # Predict trough using population Ke
                pop_ke = pop_params['cl'] / vd
                pop_levels = calculator.predict_levels(current_dose, current_interval, infusion_duration, {'ke': pop_ke, 'vd': vd})
                predicted_trough_pop = pop_levels['trough']

                # Estimate adjusted Ke/CL based on the ratio of predicted pop trough to measured trough
                if predicted_trough_pop > 0.1 and measured_trough > 0.1:
                    # Simple ratio adjustment for Ke (assumes Vd is constant)
                    ratio = math.log(predicted_trough_pop / measured_trough) / current_interval # Approximation factor
                    # Adjust ke based on deviation - needs careful implementation
                    # A more direct CL adjustment might be better:
                    # Assume AUC_current / AUC_pop = Dose / CL_current / (Dose / CL_pop) => CL_current = CL_pop * (AUC_pop / AUC_current)
                    # Since AUC is proportional to Dose/CL and often influenced by Trough:
                    # Rough approximation: CL_adjusted might be proportional to CL_pop * (predicted_trough_pop / measured_trough)
                    cl_adjusted = pop_params['cl'] * (predicted_trough_pop / measured_trough)
                    # Add bounds to prevent extreme values
                    cl_adjusted = max(pop_params['cl'] * 0.2, min(cl_adjusted, pop_params['cl'] * 3)) # Allow 20% to 300% of pop CL
                    ke_adjusted = cl_adjusted / vd
                else:
                    st.warning("Measured or predicted population trough is very low (<0.1). Using population Ke for calculations.")
                    ke_adjusted = pop_ke
                    cl_adjusted = pop_params['cl']

                # Recalculate t_half
                t_half_adjusted = 0.693 / ke_adjusted if ke_adjusted > 1e-6 else float('inf')

                adjusted_params = {
                    'ke': ke_adjusted,
                    't_half': t_half_adjusted,
                    'vd': vd, # Keep Vd from population estimate in this method
                    'cl': cl_adjusted
                }

                # Calculate current AUC with the *adjusted* ke and *measured* trough
                # First, estimate Peak corresponding to the measured trough using adjusted Ke
                c_max_estimated = measured_trough / math.exp(-ke_adjusted * (current_interval - infusion_duration))

                current_auc = calculator.calculate_vancomycin_auc(
                    c_max_estimated,
                    measured_trough,
                    ke_adjusted,
                    current_interval,
                    infusion_duration
                )

                current_levels = {
                    'peak': c_max_estimated,  # Store the estimated peak based on measured trough
                    'trough': measured_trough,
                    'auc': current_auc
                }

                # Display *individualized* PK parameters
                UIComponents.display_results(
                    adjusted_params,
                    current_levels, # Display levels based on measured trough
                    f"Parameters estimated using measured trough ({measured_trough:.1f} mg/L)"
                )

                # --- Calculate New Dose Recommendation ---
                st.markdown("### Dose Adjustment Recommendation")

                # Use the *adjusted* CL for dose calculation
                target_daily_dose = target_auc * cl_adjusted

                # Determine optimal interval based on adjusted t_half and clinical factors
                interval_options = [8, 12, 24, 36, 48]
                all_recommendations = []

                for potential_interval in interval_options:
                    dose_per_interval = target_daily_dose / (24 / potential_interval)
                    practical_dose = calculator._round_dose(dose_per_interval)

                    # Predict new levels with this dose using *adjusted* parameters
                    new_levels = calculator.predict_levels(practical_dose, potential_interval, infusion_duration, adjusted_params)
                    new_auc = calculator.calculate_vancomycin_auc(
                        new_levels['peak'],
                        new_levels['trough'],
                        ke_adjusted,
                        potential_interval,
                        infusion_duration
                    )

                    # Calculate match scores (same logic as before)
                    auc_match = abs(new_auc - target_auc) / target_auc
                    trough_in_range = trough_min <= new_levels['trough'] <= trough_max
                    if not trough_in_range:
                        if new_levels['trough'] < trough_min: trough_match = (trough_min - new_levels['trough']) / trough_min
                        else: trough_match = (new_levels['trough'] - trough_max) / trough_max
                    else:
                        trough_match = 0
                    match_score = (auc_match * 0.7) + (trough_match * 1.3)
                    if new_levels['trough'] < trough_min * 0.8 or new_levels['trough'] > trough_max * 1.2:
                        match_score += 1

                    all_recommendations.append({
                        'interval': potential_interval,
                        'dose': practical_dose,
                        'predicted_auc': new_auc,
                        'predicted_trough': new_levels['trough'],
                        'predicted_peak': new_levels['peak'],
                        'match_score': match_score,
                        'trough_in_range': trough_in_range
                    })

                # Sort by match score
                all_recommendations.sort(key=lambda x: x['match_score'])

                # Prioritize recommendations with trough in range
                in_range_recs = [rec for rec in all_recommendations if rec['trough_in_range']]
                if in_range_recs:
                    best_rec = in_range_recs[0]
                    st.success(f"Selected recommendation has predicted trough within target range ({trough_min}-{trough_max} mg/L).")
                elif all_recommendations: # If no in-range, take the absolute best score
                    best_rec = all_recommendations[0]
                    st.warning(f"No recommendations have predicted trough exactly in target range ({trough_min}-{trough_max} mg/L). Selected the closest match.")
                else:
                    st.error("Could not generate a dosing recommendation.")
                    return # Stop if no recommendations

                # --- REMOVED: Display multiple dosing options table ---
                # st.subheader("Dosing Options (Best Match First)")
                # ... (code to create and display rec_data table) ...
                # st.table(rec_data)

                # --- ENHANCED: Recommendation Summary ---
                old_regimen = f"{current_dose} mg every {current_interval} hours"
                new_regimen = f"{best_rec['dose']} mg every {best_rec['interval']} hours"

                st.subheader("Recommendation Summary")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Current Regimen:**")
                    st.metric(label="Regimen", value=old_regimen)
                    st.metric(label="Measured Trough", value=f"{measured_trough:.1f} mg/L")
                    st.metric(label="Estimated Current AUC", value=f"{current_auc:.1f} mg·hr/L")
                    st.markdown(f"Based on Trough: {measured_trough:.1f} mg/L")


                with col2:
                    st.markdown("**Recommended New Regimen:**")
                    st.metric(label="Regimen", value=new_regimen, delta="Adjusted")
                    st.metric(label="Predicted Trough", value=f"{best_rec['predicted_trough']:.1f} mg/L")
                    st.metric(label="Predicted AUC", value=f"{best_rec['predicted_auc']:.1f} mg·hr/L")
                    st.markdown(f"Target Trough: {trough_min}-{trough_max} mg/L")
                    st.markdown(f"Target AUC: {target_auc} mg·hr/L")

                # --- ENHANCED: Clinical Interpretation ---
                st.markdown("### Clinical Interpretation")
                interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)

                # Assess current levels based on *measured* trough and *estimated* peak/AUC
                current_assessment, current_status = interpreter.assess_levels(current_levels)

                # Assess predicted new levels
                predicted_new_levels = {
                    'peak': best_rec['predicted_peak'],
                    'trough': best_rec['predicted_trough'],
                    'auc': best_rec['predicted_auc']
                }
                new_assessment, new_status = interpreter.assess_levels(predicted_new_levels)

                # Combine assessments
                combined_assessment = [
                    f"**CURRENT REGIMEN ASSESSMENT ({old_regimen}):**"
                ] + current_assessment + [
                    "",
                    f"**RECOMMENDED REGIMEN ASSESSMENT ({new_regimen}):**"
                ] + new_assessment

                # Generate detailed recommendations
                recommendations = []
                # Justification for change
                if best_rec['dose'] != current_dose or best_rec['interval'] != current_interval:
                     recommendations.append(f"Adjustment needed from {old_regimen} to achieve target AUC ({target_auc} mg·hr/L) and Trough ({trough_min}-{trough_max} mg/L).")
                     if best_rec['interval'] != current_interval:
                         recommendations.append(f"Interval changed to {best_rec['interval']}h based on estimated half-life ({adjusted_params['t_half']:.1f} hr) and target levels.")
                     if best_rec['dose'] != current_dose:
                        dose_change_pct = abs(best_rec['dose'] - current_dose) / current_dose * 100 if current_dose > 0 else float('inf')
                        change_direction = "increased" if best_rec['dose'] > current_dose else "decreased"
                        recommendations.append(f"Dose {change_direction} to {best_rec['dose']} mg (approx. {dose_change_pct:.0f}%) to better match target AUC based on estimated clearance ({adjusted_params['cl']:.2f} L/hr).")
                else:
                     recommendations.append("Current regimen appears appropriate based on the measured trough, but re-assessment confirms targets are met.")

                # Add standard monitoring + context
                recommendations.extend(interpreter.generate_recommendations(new_status, patient_data['crcl'])) # Add generic ones like renal monitoring
                recommendations.append(f"**Monitoring:** Recommend drawing a trough level just prior to the 4th dose of the *new* regimen ({new_regimen}) to confirm target attainment.")
                recommendations.append(f"Rationale: This regimen ({new_regimen}) is predicted to yield an AUC of {best_rec['predicted_auc']:.1f} (Target: {target_auc}) and a trough of {best_rec['predicted_trough']:.1f} (Target: {trough_min}-{trough_max}).")
                if not best_rec['trough_in_range']:
                     recommendations.append(f"NOTE: The predicted trough ({best_rec['predicted_trough']:.1f} mg/L) is slightly outside the target range, but this regimen provides the best balance for achieving the target AUC.")


                interpretation = interpreter.format_recommendations(combined_assessment, new_status, recommendations, patient_data)
                st.markdown(interpretation)

                # Generate and display print button (using adjusted params and *new* predicted levels for context)
                report = UIComponents.generate_report(
                    "Vancomycin",
                    f"{regimen} therapy - Trough adjustment",
                    patient_data,
                    adjusted_params, # Report the calculated individual params
                    predicted_new_levels, # Report the levels predicted for the NEW regimen
                    f"Recommendation: Change from {old_regimen} to {new_regimen}",
                    interpretation
                )
                UIComponents.create_print_button(report)

                # Visualize the predicted concentration-time curves
                st.markdown("### Predicted Concentration-Time Profiles")
                # Use tabs to show comparison if useful, otherwise just show the new one
                tab1, tab2 = st.tabs(["Recommended Regimen", "Previous Regimen (Estimated)"])

                with tab1: # Show NEW regimen first
                    st.markdown(f"**Profile for Recommended: {new_regimen}**")
                    PKVisualizer.display_pk_chart(
                        adjusted_params,
                        predicted_new_levels, # Use levels for the new dose
                        {'tau': best_rec['interval'], 'infusion_duration': infusion_duration},
                        key_suffix="new_trough"
                    )
                with tab2: # Show OLD regimen based on estimated peak
                    st.markdown(f"**Estimated Profile for Previous: {old_regimen}**")
                    PKVisualizer.display_pk_chart(
                        adjusted_params,
                        current_levels, # Use levels derived from measured trough
                        {'tau': current_interval, 'infusion_duration': infusion_duration},
                        key_suffix="current_trough"
                    )

            # --- Add Error Handling ---
            except ZeroDivisionError:
                st.error("Calculation Error: Division by zero occurred. Check interval, infusion duration, or calculated PK parameters.")
            except ValueError as ve:
                st.error(f"Calculation Error: Invalid value encountered ({ve}). Check logs or concentration inputs.")
            except OverflowError as oe:
                 st.error(f"Calculation Error: Numerical overflow occurred ({oe}). Check inputs for extreme values.")
            except Exception as e:
                st.error(f"An unexpected error occurred during trough adjustment calculation: {str(e)}")
                st.warning("Please double-check input values.")


    @staticmethod
    def _adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Peak & Trough")

        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0, step=50.0, key="dose_pt_val")
            current_interval = st.selectbox("Current Interval (hr)", [4, 6, 8, 12, 18, 24, 36, 48, 72], index=3, key="int_pt_val")
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0, step=0.25, key="inf_pt_val")
        with col2:
            # Inputs moved to sampling section below for better flow
            pass # Keep column structure

        # Display target ranges
        trough_min = targets['trough_min']
        trough_max = targets['trough_max']
        st.info(f"{regimen.capitalize()} therapy target trough range: {trough_min}-{trough_max} mg/L")
        st.info(f"Target AUC: {target_auc} mg·hr/L")


        # Dose administration time
        st.subheader("Dose Administration & Sampling Times")
        col_dose, col_peak, col_trough = st.columns(3)
        with col_dose:
            st.markdown("**Dose Info**")
            dose_hour, dose_minute, dose_display = UIComponents.create_time_input("Dose Start Time", 9, 0, key="dose_time_pt")
            st.write(f"Dose Start: {dose_display}")
        with col_peak:
             st.markdown("**Peak Level**")
             measured_peak = st.number_input("Measured Peak (mg/L)", 0.1, 100.0, 30.0, step=0.1, format="%.1f", key="peak_val_pt")
             peak_hour, peak_minute, peak_display = UIComponents.create_time_input("Peak Sample Time", 11, 0, key="peak_time_pt")
             st.write(f"Peak Drawn: {peak_display}")
        with col_trough:
             st.markdown("**Trough Level**")
             measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0, step=0.1, format="%.1f", key="trough_val_pt")
             trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key="trough_time_pt")
             st.write(f"Trough Drawn: {trough_display}")


        if st.button("Calculate Adjusted Dose", key="calc_adjust_pt"):
            # --- WRAP ALL CALCULATIONS IN TRY-EXCEPT ---
            try:
                # Calculate time differences relative to dose *start* time
                t_trough_draw = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)
                t_peak_draw = UIComponents.calculate_time_difference(dose_hour, dose_minute, peak_hour, peak_minute)

                # Add validation for timing
                if t_peak_draw <= infusion_duration / 2:
                    st.warning(f"Peak drawn very early ({t_peak_draw:.1f} hr after dose start, during infusion {infusion_duration:.1f} hr). Accuracy may be reduced.")
                if t_peak_draw <= 0:
                    st.error("Peak draw time cannot be before or exactly at dose start time.")
                    return
                # Allow trough before or after dose for flexibility, calculation adjusts
                # if abs(t_trough_draw) < 0.1 or (t_trough_draw > 0 and abs(t_trough_draw - current_interval) > 2):
                #      st.warning(f"Trough draw time ({t_trough_draw:.1f} hr relative to dose start) seems unusual. Ensure it's a true trough (just before a dose).")


                # --- Calculate Individual PK (Sawchuk-Zaske or similar) ---
                # Use the calculator method designed for two levels
                individual_params = calculator.calculate_pk_from_levels(
                    dose=current_dose,
                    tau=current_interval,
                    infusion_duration=infusion_duration,
                    level1=measured_peak,
                    time1=t_peak_draw,
                    level2=measured_trough,
                    time2=t_trough_draw
                )

                if not individual_params or individual_params['ke'] <= 0 or individual_params['vd'] <= 0:
                     st.error("Failed to calculate valid individual PK parameters from the provided levels and times. Please check inputs.")
                     # Optionally, attempt fallback to population Vd + Ke from levels?
                     # For now, we stop if individual params fail.
                     return

                # Calculate steady-state Cmax, Cmin, and AUC using the *individualized* parameters
                ss_levels = calculator.predict_levels(current_dose, current_interval, infusion_duration, individual_params)
                current_auc = calculator.calculate_vancomycin_auc(
                    ss_levels['peak'],
                    ss_levels['trough'],
                    individual_params['ke'],
                    current_interval,
                    infusion_duration
                )

                # For reporting, show the calculated SS levels, not necessarily the measured ones if they weren't true SS peak/trough
                current_ss_levels_display = {
                    'peak': ss_levels['peak'], # Calculated steady-state peak
                    'trough': ss_levels['trough'], # Calculated steady-state trough
                    'auc': current_auc
                }

                # Display *individualized* PK parameters and *calculated* SS levels
                UIComponents.display_results(
                    individual_params,
                    current_ss_levels_display,
                    f"PK parameters estimated from measured Peak ({measured_peak:.1f} at {t_peak_draw:.1f}h) and Trough ({measured_trough:.1f} at {t_trough_draw:.1f}h post-dose start)"
                )

                # --- Dose Adjustment Recommendation ---
                st.markdown("### Dose Adjustment Recommendation")

                # Use the *individualized* CL and Vd for dose calculation
                target_daily_dose = target_auc * individual_params['cl']
                interval_options = [8, 12, 24, 36, 48]
                all_recommendations = []

                for potential_interval in interval_options:
                    dose_per_interval = target_daily_dose / (24 / potential_interval)
                    practical_dose = calculator._round_dose(dose_per_interval)

                    # Predict new levels using *individual* PK parameters
                    new_levels = calculator.predict_levels(practical_dose, potential_interval, infusion_duration, individual_params)
                    new_auc = calculator.calculate_vancomycin_auc(
                        new_levels['peak'],
                        new_levels['trough'],
                        individual_params['ke'],
                        potential_interval,
                        infusion_duration
                    )

                    # Calculate match scores (same logic)
                    auc_match = abs(new_auc - target_auc) / target_auc
                    trough_in_range = trough_min <= new_levels['trough'] <= trough_max
                    if not trough_in_range:
                        if new_levels['trough'] < trough_min: trough_match = (trough_min - new_levels['trough']) / trough_min
                        else: trough_match = (new_levels['trough'] - trough_max) / trough_max
                    else:
                        trough_match = 0
                    match_score = (auc_match * 0.7) + (trough_match * 1.3)
                    if new_levels['trough'] < trough_min * 0.8 or new_levels['trough'] > trough_max * 1.2:
                        match_score += 1

                    all_recommendations.append({
                        'interval': potential_interval,
                        'dose': practical_dose,
                        'predicted_auc': new_auc,
                        'predicted_trough': new_levels['trough'],
                        'predicted_peak': new_levels['peak'],
                        'match_score': match_score,
                        'trough_in_range': trough_in_range
                    })

                # Sort and select best recommendation (same logic)
                all_recommendations.sort(key=lambda x: x['match_score'])
                in_range_recs = [rec for rec in all_recommendations if rec['trough_in_range']]
                if in_range_recs:
                    best_rec = in_range_recs[0]
                    st.success(f"Selected recommendation has predicted trough within target range ({trough_min}-{trough_max} mg/L).")
                elif all_recommendations:
                    best_rec = all_recommendations[0]
                    st.warning(f"No recommendations have predicted trough exactly in target range ({trough_min}-{trough_max} mg/L). Selected the closest match.")
                else:
                    st.error("Could not generate a dosing recommendation.")
                    return

                # --- REMOVED: Dosing Options Table ---

                # --- ENHANCED: Recommendation Summary ---
                old_regimen = f"{current_dose} mg every {current_interval} hours"
                new_regimen = f"{best_rec['dose']} mg every {best_rec['interval']} hours"

                st.subheader("Recommendation Summary")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Current Regimen & Levels:**")
                    st.metric(label="Regimen", value=old_regimen)
                    # Show measured levels for context, but calculated SS for PK summary
                    st.metric(label="Measured Peak", value=f"{measured_peak:.1f} mg/L (at {t_peak_draw:.1f} hr)")
                    st.metric(label="Measured Trough", value=f"{measured_trough:.1f} mg/L (at {t_trough_draw:.1f} hr)")
                    st.metric(label="Calculated Current AUC", value=f"{current_auc:.1f} mg·hr/L")


                with col2:
                    st.markdown("**Recommended New Regimen:**")
                    st.metric(label="Regimen", value=new_regimen, delta="Adjusted")
                    st.metric(label="Predicted Peak", value=f"{best_rec['predicted_peak']:.1f} mg/L")
                    st.metric(label="Predicted Trough", value=f"{best_rec['predicted_trough']:.1f} mg/L")
                    st.metric(label="Predicted AUC", value=f"{best_rec['predicted_auc']:.1f} mg·hr/L")
                    st.markdown(f"Target Trough: {trough_min}-{trough_max} mg/L")
                    st.markdown(f"Target AUC: {target_auc} mg·hr/L")


                # --- ENHANCED: Clinical Interpretation ---
                st.markdown("### Clinical Interpretation")
                interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)

                # Assess current situation based on *calculated steady-state* levels derived from measurements
                current_assessment, current_status = interpreter.assess_levels(current_ss_levels_display)

                # Assess predicted new levels
                predicted_new_levels = {
                    'peak': best_rec['predicted_peak'],
                    'trough': best_rec['predicted_trough'],
                    'auc': best_rec['predicted_auc']
                }
                new_assessment, new_status = interpreter.assess_levels(predicted_new_levels)

                # Combine assessments
                combined_assessment = [
                    f"**CURRENT REGIMEN ASSESSMENT ({old_regimen} - based on calculated steady state):**"
                ] + current_assessment + [
                    "",
                    f"**RECOMMENDED REGIMEN ASSESSMENT ({new_regimen}):**"
                ] + new_assessment

                # Generate detailed recommendations
                recommendations = []
                # Justification for change
                if best_rec['dose'] != current_dose or best_rec['interval'] != current_interval:
                     recommendations.append(f"Adjustment needed from {old_regimen} to achieve target AUC ({target_auc} mg·hr/L) and Trough ({trough_min}-{trough_max} mg/L), based on patient-specific PK.")
                     recommendations.append(f"Patient's estimated Vd: {individual_params['vd']:.2f} L, Ke: {individual_params['ke']:.3f} /hr, CL: {individual_params['cl']:.2f} L/hr, T½: {individual_params['t_half']:.1f} hr.")
                     if best_rec['interval'] != current_interval:
                         recommendations.append(f"Interval changed to {best_rec['interval']}h based on calculated half-life and target levels.")
                     if best_rec['dose'] != current_dose:
                        dose_change_pct = abs(best_rec['dose'] - current_dose) / current_dose * 100 if current_dose > 0 else float('inf')
                        change_direction = "increased" if best_rec['dose'] > current_dose else "decreased"
                        recommendations.append(f"Dose {change_direction} to {best_rec['dose']} mg (approx. {dose_change_pct:.0f}%) based on calculated clearance and target AUC.")
                else:
                     recommendations.append("Current regimen appears appropriate based on measured levels and calculated PK, re-assessment confirms targets met.")


                # Add standard monitoring + context
                recommendations.extend(interpreter.generate_recommendations(new_status, patient_data['crcl']))
                recommendations.append(f"**Monitoring:** Recommend drawing a trough level just prior to the 4th dose of the *new* regimen ({new_regimen}) to confirm target attainment.")
                recommendations.append(f"Rationale: This regimen ({new_regimen}) utilizes patient-specific PK parameters and is predicted to yield an AUC of {best_rec['predicted_auc']:.1f} (Target: {target_auc}) and a trough of {best_rec['predicted_trough']:.1f} (Target: {trough_min}-{trough_max}).")
                if not best_rec['trough_in_range']:
                     recommendations.append(f"NOTE: The predicted trough ({best_rec['predicted_trough']:.1f} mg/L) is slightly outside the target range, but this regimen provides the best balance for achieving the target AUC using the calculated PK.")


                interpretation = interpreter.format_recommendations(combined_assessment, new_status, recommendations, patient_data)
                st.markdown(interpretation)

                # Generate report and print button
                report = UIComponents.generate_report(
                    "Vancomycin", f"{regimen} therapy - Peak/Trough adjustment", patient_data,
                    individual_params, # Report the calculated individual params
                    predicted_new_levels, # Report the levels predicted for the NEW regimen
                    f"Recommendation: Change from {old_regimen} to {new_regimen}", interpretation
                )
                UIComponents.create_print_button(report)

                # Visualize profiles
                st.markdown("### Predicted Concentration-Time Profiles")
                tab1, tab2 = st.tabs(["Recommended Regimen", "Current Regimen (Calculated SS)"])
                with tab1: # Show NEW regimen first
                    st.markdown(f"**Profile for Recommended: {new_regimen}**")
                    PKVisualizer.display_pk_chart(
                        individual_params, predicted_new_levels,
                        {'tau': best_rec['interval'], 'infusion_duration': infusion_duration}, key_suffix="new_peaktrough"
                    )
                with tab2: # Show OLD regimen calculated SS profile
                     st.markdown(f"**Calculated Steady-State Profile for Previous: {old_regimen}**")
                     PKVisualizer.display_pk_chart(
                        individual_params, current_ss_levels_display, # Use calculated SS levels
                        {'tau': current_interval, 'infusion_duration': infusion_duration}, key_suffix="current_peaktrough"
                     )


            # --- END OF TRY BLOCK ---
            except ZeroDivisionError:
                st.error("Calculation Error: Division by zero occurred. Check interval, infusion duration, or calculated PK parameters (Ke, Vd).")
            except ValueError as ve:
                st.error(f"Calculation Error: Invalid value encountered ({ve}). This might be due to log(non-positive concentration) or invalid time inputs.")
            except OverflowError as oe:
                 st.error(f"Calculation Error: Numerical overflow occurred ({oe}). Check inputs for extreme values or very long intervals.")
            except Exception as e:
                st.error(f"An unexpected error occurred during peak/trough adjustment calculations: {str(e)}")
                st.warning("Please double-check input values (dose, interval, levels, times) and ensure they are clinically reasonable.")

# --- Make sure PKCalculator has the necessary methods ---
# Assume PKCalculator has:
# - calculate_initial_parameters() -> {'ke', 'vd', 'cl', 't_half'}
# - predict_levels(dose, tau, infusion_duration, pk_params) -> {'peak', 'trough'}
# - calculate_vancomycin_auc(peak, trough, ke, tau, infusion_duration) -> float
# - _round_dose(dose) -> float
# - calculate_pk_from_levels(dose, tau, infusion_duration, level1, time1, level2, time2) -> {'ke', 'vd', 'cl', 't_half'} or None

# Assume ClinicalInterpreter has:
# - assess_levels(levels_dict) -> (assessment_list, status_dict)
# - generate_recommendations(status_dict, crcl) -> recommendations_list
# - format_recommendations(assessment, status, recommendations, patient_data) -> formatted_string

# Assume UIComponents has:
# - display_results(pk_params, levels, message)
# - create_time_input(label, default_hour, default_min, key) -> (hour, minute, display_string)
# - calculate_time_difference(h1, m1, h2, m2) -> float_hours
# - generate_report(...) -> report_string
# - create_print_button(report_string)

# Assume PKVisualizer has:
# - display_pk_chart(pk_params, levels, dose_info, key_suffix)

# Assume config.py has DRUG_CONFIGS structure as used.
