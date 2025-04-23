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
        recommended_interval = 12

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
            {'tau': interval, 'infusion_duration': infusion_duration},
            key_suffix="initial_dose"
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

        # Display target ranges based on therapy type
        if "Empiric" in regimen:
            trough_min, trough_max = 10, 15
            st.info(f"Empiric therapy target trough range: {trough_min}-{trough_max} mg/L")
        else:  # Definitive
            trough_min, trough_max = 15, 20
            st.info(f"Definitive therapy target trough range: {trough_min}-{trough_max} mg/L")

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

            # Calculate new dose - automatically suggest the best interval
            st.markdown("### Dose Adjustment Recommendation")

            # Determine optimal interval based on renal function and clinical needs
            crcl = patient_data['crcl']

            # Logic to determine optimal interval based on t_half and clinical factors
            interval_options = [8, 12, 24, 36, 48]

            # Start with CrCl-based recommendation
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

            # Adjust based on measured trough relative to target range midpoint
            target_trough_midpoint = (trough_min + trough_max) / 2

            # Prepare all possible dosing recommendations
            all_recommendations = []
            for potential_interval in interval_options:
                # Calculate dose needed to achieve target AUC
                target_daily_dose = target_auc * cl_adjusted
                dose_per_interval = target_daily_dose / (24 / potential_interval)
                practical_dose = calculator._round_dose(dose_per_interval)

                # Predict new levels with this dose
                new_levels = calculator.predict_levels(practical_dose, potential_interval, infusion_duration)
                new_auc = calculator.calculate_vancomycin_auc(
                    new_levels['peak'],
                    new_levels['trough'],
                    ke_adjusted,
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

            # Get the single best recommendation
            if in_range_recs:
                best_rec = in_range_recs[0]
                st.success("Found optimal regimen with trough within target range")
            else:
                best_rec = all_recommendations[0]
                st.warning(f"No regimens have trough exactly in target range ({trough_min}-{trough_max} mg/L). Using best available match.")

            # Format for detailed recommendation
            old_regimen = f"{current_dose} mg every {current_interval} hours"
            new_regimen = f"{best_rec['dose']} mg every {best_rec['interval']} hours"

            # Calculate changes from current regimen
            dose_change_pct = ((best_rec['dose'] - current_dose) / current_dose * 100) if current_dose > 0 else float('inf')
            dose_change_direction = "increased" if best_rec['dose'] > current_dose else "decreased"
            interval_change = "unchanged" if best_rec['interval'] == current_interval else f"changed from {current_interval}h to {best_rec['interval']}h"
            daily_dose_current = (24 / current_interval) * current_dose if current_interval > 0 else 0
            daily_dose_new = (24 / best_rec['interval']) * best_rec['dose'] if best_rec['interval'] > 0 else 0
            daily_dose_change_pct = ((daily_dose_new - daily_dose_current) / daily_dose_current * 100) if daily_dose_current > 0 else float('inf')
            
            # Enhanced target information
            auc_target_status = "within target range" if abs(best_rec['predicted_auc'] - target_auc) / target_auc < 0.1 else (
                "below target range" if best_rec['predicted_auc'] < target_auc * 0.9 else "above target range"
            )
            
            trough_target_status = "within target range" if trough_min <= best_rec['predicted_trough'] <= trough_max else (
                "below target range" if best_rec['predicted_trough'] < trough_min else "above target range"
            )

            # Display detailed recommendation
            st.subheader("Optimal Dose Recommendation")
            
            st.markdown("#### Current Regimen Assessment")
            st.info(old_regimen)
            st.markdown(f"• Measured Trough: **{measured_trough:.1f} mg/L** ({trough_target_status})")
            st.markdown(f"• Estimated AUC: **{current_auc:.1f} mg·hr/L** ({auc_target_status})")
            st.markdown(f"• Daily Dose: **{daily_dose_current:.1f} mg/day**")
            
            st.markdown("#### Recommended New Regimen")
            st.success(new_regimen)
            st.markdown(f"• Predicted Trough: **{best_rec['predicted_trough']:.1f} mg/L** ({trough_target_status})")
            st.markdown(f"• Predicted AUC: **{best_rec['predicted_auc']:.1f} mg·hr/L** ({auc_target_status})")
            st.markdown(f"• Daily Dose: **{daily_dose_new:.1f} mg/day** " +
                       f"({abs(daily_dose_change_pct):.1f}% {dose_change_direction} from current)")
            
            st.markdown("#### Clinical Rationale")
            rationale_points = []
            
            # Add AUC-related rationale
            if abs(best_rec['predicted_auc'] - target_auc) <= target_auc * 0.05:
                rationale_points.append(f"• The recommended regimen achieves AUC of {best_rec['predicted_auc']:.1f} mg·hr/L, " +
                                       f"which is very close to the target AUC of {target_auc} mg·hr/L.")
            elif abs(best_rec['predicted_auc'] - target_auc) <= target_auc * 0.1:
                rationale_points.append(f"• The recommended regimen achieves AUC of {best_rec['predicted_auc']:.1f} mg·hr/L, " +
                                       f"which is within 10% of the target AUC of {target_auc} mg·hr/L.")
            else:
                rationale_points.append(f"• The recommended regimen achieves AUC of {best_rec['predicted_auc']:.1f} mg·hr/L, " +
                                       f"which is the closest achievable to the target AUC of {target_auc} mg·hr/L " +
                                       f"while balancing other clinical factors.")
            
            # Add trough-related rationale
            if trough_min <= best_rec['predicted_trough'] <= trough_max:
                rationale_points.append(f"• The predicted trough of {best_rec['predicted_trough']:.1f} mg/L falls within " +
                                       f"the target range of {trough_min}-{trough_max} mg/L for {regimen} therapy.")
            else:
                closest_boundary = trough_min if best_rec['predicted_trough'] < trough_min else trough_max
                rationale_points.append(f"• The predicted trough of {best_rec['predicted_trough']:.1f} mg/L is outside " +
                                       f"the target range of {trough_min}-{trough_max} mg/L, but is the closest achievable " +
                                       f"while maintaining an appropriate AUC.")
            
            # Add interval rationale based on renal function
            if best_rec['interval'] == recommended_interval:
                rationale_points.append(f"• The interval of {best_rec['interval']} hours is optimal based on the patient's " +
                                       f"renal function (CrCl = {crcl:.1f} mL/min).")
            else:
                rationale_points.append(f"• While {recommended_interval} hours would be the standard interval for CrCl of {crcl:.1f} mL/min, " +
                                       f"an interval of {best_rec['interval']} hours better achieves the target AUC and trough.")
            
            # Add clinical considerations
            if regimen == "empiric":
                rationale_points.append("• This empiric regimen aims to achieve adequate exposure for most pathogens while " +
                                       "minimizing toxicity risk during initial therapy.")
            else:  # definitive
                rationale_points.append("• This definitive therapy regimen targets higher exposures appropriate for documented " +
                                       "infections requiring more aggressive vancomycin therapy.")
            
            # Add PK parameter considerations
            if adjusted_params['cl'] < 0.05:
                rationale_points.append("• Patient has severely impaired vancomycin clearance, requiring extended interval to " +
                                       "prevent drug accumulation.")
            elif adjusted_params['cl'] > 0.1:
                rationale_points.append(f"• Patient's vancomycin clearance of {adjusted_params['cl']:.3f} L/kg/hr is relatively high, " +
                                       "which has been accounted for in the dosing recommendation.")
            
                            st.markdown("\n".join(rationale_points))
                
                # Add practical notes
                st.markdown("#### Practical Considerations")
                prac_notes = []
                
                # Round dose to nearest vial size if appropriate
                standard_vials = [500, 750, 1000, 1250, 1500, 1750, 2000]
                closest_vial = min(standard_vials, key=lambda x: abs(x - best_rec['dose']))
                if abs(closest_vial - best_rec['dose']) <= 50:  # Within 50mg
                    prac_notes.append(f"• The recommended dose ({best_rec['dose']} mg) is close to a standard vial size of {closest_vial} mg.")
                    
                # Add infusion time note
                if best_rec['dose'] > 1000 and infusion_duration < 1.5:
                    prac_notes.append(f"• Consider extending infusion time to 1.5-2 hours for doses > 1000 mg to minimize infusion reactions.")
                
                # Add monitoring notes based on PK parameters
                if t_half_ind > 12:
                    next_level_time = "16-24 hours after the next dose"
                    prac_notes.append(f"• With extended half-life of {t_half_ind:.1f} hours, recommend checking follow-up levels at {next_level_time}.")
                else:
                    next_level_time = "30 minutes before the next dose" if best_rec['interval'] <= 24 else "at a consistent time of day"
                    prac_notes.append(f"• Recommend checking a follow-up trough level after 3-4 doses (at steady state), drawn {next_level_time}.")
                
                # Add a note about timing if peak/trough timing was unusual
                if t_peak < 2.0 or t_trough > -1.0 and t_trough < current_interval - 2.0:
                    prac_notes.append("• Note that the timing of peak and trough samples was not at typical times. " +
                                     "For future monitoring, consider drawing peak 1-2 hours after end of infusion and trough 30 minutes before next dose.")
                
                # Add renal function monitoring if necessary
                if crcl < 50:
                    prac_notes.append(f"• With CrCl of {crcl:.1f} mL/min, recommend monitoring renal function at least every 2-3 days while on therapy.")
                
                if len(prac_notes) > 0:
                    st.markdown("\n".join(prac_notes))

                # Clinical interpretation
                interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)

                # First assess current levels
                current_levels_for_interp = { 'peak': cmax_ind, 'trough': cmin_ind, 'auc': current_auc }
                current_assessment, current_status = interpreter.assess_levels(current_levels_for_interp)

                predicted_new_levels = { 'peak': best_rec['predicted_peak'], 'trough': best_rec['predicted_trough'], 'auc': best_rec['predicted_auc'] }
                new_assessment, new_status = interpreter.assess_levels(predicted_new_levels)

                combined_assessment = [f"CURRENT REGIMEN: {old_regimen}"] + current_assessment + ["", f"RECOMMENDED REGIMEN: {new_regimen}"] + new_assessment
                recommendations = interpreter.generate_recommendations(new_status, patient_data['crcl'])

                if best_rec['dose'] != current_dose or best_rec['interval'] != current_interval:
                     dose_change_pct = abs(best_rec['dose'] - current_dose) / current_dose * 100 if current_dose > 0 else float('inf')
                     if dose_change_pct > 20:
                          change_direction = "increased" if best_rec['dose'] > current_dose else "decreased"
                          recommendations.insert(0, f"Dose {change_direction} by {dose_change_pct:.0f}% to achieve target AUC and trough")
                     if best_rec['interval'] != current_interval:
                          recommendations.insert(0, f"Interval changed from {current_interval}h to {best_rec['interval']}h based on individual PK parameters and target levels")

                st.markdown("### Complete Clinical Interpretation")
                interpretation = interpreter.format_recommendations(combined_assessment, new_status, recommendations, patient_data)
                st.markdown(interpretation)

                # Generate report and print button
                report = UIComponents.generate_report(
                    "Vancomycin", 
                    f"{regimen} therapy - Peak/Trough adjustment", 
                    patient_data,
                    individual_params, 
                    measured_levels_display, # Use calculated levels for report consistency
                    f"Changed from {old_regimen} to {new_regimen}", 
                    interpretation
                )
                UIComponents.create_print_button(report)

                # Visualize profiles
                st.markdown("### Predicted Concentration-Time Profiles")
                tab1, tab2 = st.tabs(["Current Regimen", "New Regimen"])
                with tab1:
                    PKVisualizer.display_pk_chart(
                        individual_params, 
                        current_levels_for_interp,
                        {'tau': current_interval, 'infusion_duration': infusion_duration}, 
                        key_suffix="current_peaktrough"
                    )
                with tab2:
                    PKVisualizer.display_pk_chart(
                        individual_params, 
                        predicted_new_levels,
                        {'tau': best_rec['interval'], 'infusion_duration': infusion_duration}, 
                        key_suffix="new_peaktrough"
                    )

            # --- END OF TRY BLOCK ---
            except ZeroDivisionError:
                 st.error("Calculation Error: Division by zero occurred. This might be due to zero interval, infusion duration, or invalid PK parameters. Please check inputs.")
            except ValueError as ve:
                 st.error(f"Calculation Error: Invalid value encountered ({ve}). This might be due to taking the log of non-positive concentrations or issues with time inputs. Please check measured levels and times.")
            except OverflowError as oe:
                 st.error(f"Calculation Error: Numerical overflow occurred ({oe}). This might indicate extreme PK parameters or very long intervals/infusion times. Please check inputs.")
            except Exception as e:
                st.error(f"An unexpected error occurred during calculations: {str(e)}")
                st.warning("Please double-check your input values (dose, interval, levels, times) and ensure they are clinically reasonable.")
            
            # Add practical notes
            st.markdown("#### Practical Considerations")
            prac_notes = []
            
            # Round dose to nearest vial size if appropriate
            standard_vials = [500, 750, 1000, 1250, 1500, 1750, 2000]
            closest_vial = min(standard_vials, key=lambda x: abs(x - best_rec['dose']))
            if abs(closest_vial - best_rec['dose']) <= 50:  # Within 50mg
                prac_notes.append(f"• The recommended dose ({best_rec['dose']} mg) is close to a standard vial size of {closest_vial} mg.")
                
            # Add infusion time note
            if best_rec['dose'] > 1000 and infusion_duration < 1.5:
                prac_notes.append(f"• Consider extending infusion time to 1.5-2 hours for doses > 1000 mg to minimize infusion reactions.")
            
            # Add monitoring notes
            next_level_time = "30 minutes before the next dose" if best_rec['interval'] <= 24 else "at a consistent time of day"
            prac_notes.append(f"• Recommend checking a follow-up trough level after 3-4 doses (at steady state), drawn {next_level_time}.")
            
            if len(prac_notes) > 0:
                st.markdown("\n".join(prac_notes))

            # Clinical interpretation
            interpreter = ClinicalInterpreter("Vancomycin", regimen, targets)

            # First assess current levels
            current_levels = {
                'peak': predicted_levels['peak'],  # Estimated peak from current dose
                'trough': measured_trough,
                'auc': current_auc
            }

            current_assessment, current_status = interpreter.assess_levels(current_levels)

            # Then assess predicted new levels
            predicted_new_levels = {
                'peak': best_rec['predicted_peak'],
                'trough': best_rec['predicted_trough'],
                'auc': best_rec['predicted_auc']
            }

            new_assessment, new_status = interpreter.assess_levels(predicted_new_levels)

            # Combine assessments for a comprehensive clinical interpretation
            combined_assessment = [
                f"CURRENT REGIMEN: {old_regimen}"
            ] + current_assessment + [
                "",
                f"RECOMMENDED REGIMEN: {new_regimen}"
            ] + new_assessment

            # Generate recommendations based on new predicted levels
            recommendations = interpreter.generate_recommendations(new_status, patient_data['crcl'])

            # If new regimen is significantly different from current, add justification
            if best_rec['dose'] != current_dose or best_rec['interval'] != current_interval:
                dose_change_pct = abs(best_rec['dose'] - current_dose) / current_dose * 100 if current_dose > 0 else float('inf')
                if dose_change_pct > 20:
                    if best_rec['dose'] > current_dose:
                        recommendations.insert(0, f"Dose increased by {dose_change_pct:.0f}% to achieve target AUC and trough")
                    else:
                        recommendations.insert(0, f"Dose decreased by {dose_change_pct:.0f}% to avoid excessive AUC or trough")

                if best_rec['interval'] != current_interval:
                    recommendations.insert(0, f"Interval changed from {current_interval}h to {best_rec['interval']}h based on renal function and target levels")

            st.markdown("### Clinical Interpretation")
            interpretation = interpreter.format_recommendations(combined_assessment, new_status, recommendations, patient_data)
            st.markdown(interpretation)

            # Generate and display print button
            report = UIComponents.generate_report(
                "Vancomycin",
                f"{regimen} therapy - Trough adjustment",
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
                    current_levels,
                    {'tau': current_interval, 'infusion_duration': infusion_duration},
                    key_suffix="current_trough"
                )

            with tab2:
                PKVisualizer.display_pk_chart(
                    adjusted_params,
                    predicted_new_levels,
                    {'tau': best_rec['interval'], 'infusion_duration': infusion_duration},
                    key_suffix="new_trough"
                )

    @staticmethod
    def _adjust_with_peak_trough(calculator, target_auc, targets, regimen, patient_data):
        st.markdown("### Dose Adjustment Using Peak & Trough")

        col1, col2 = st.columns(2)
        with col1:
            current_dose = st.number_input("Current Dose (mg)", 250.0, 3000.0, 1000.0)
            current_interval = st.number_input("Current Interval (hr)", 4, 72, 12)
            infusion_duration = st.number_input("Infusion Duration (hr)", 0.5, 4.0, 1.0)

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
            measured_trough = st.number_input("Measured Trough (mg/L)", 0.1, 100.0, 12.0)
            trough_hour, trough_minute, trough_display = UIComponents.create_time_input("Trough Sample Time", 8, 30, key="trough_pt")
            st.info(f"Trough drawn at: {trough_display}")
        with col2:
            measured_peak = st.number_input("Measured Peak (mg/L)", 0.1, 100.0, 30.0)
            peak_hour, peak_minute, peak_display = UIComponents.create_time_input("Peak Sample Time", 11, 0, key="peak_pt")
            st.info(f"Peak drawn at: {peak_display}")


        if st.button("Calculate PK Parameters"):
            # --- WRAP ALL CALCULATIONS IN TRY-EXCEPT ---
            try:
                # Calculate time differences
                t_trough = UIComponents.calculate_time_difference(dose_hour, dose_minute, trough_hour, trough_minute)
                t_peak = UIComponents.calculate_time_difference(dose_hour, dose_minute, peak_hour, peak_minute)

                # Handle two scenarios:
                # 1. Pre/Post levels around a single dose (trough before dose, peak after dose)
                # 2. Traditional PK (trough at end of interval, peak after dose)

                if t_trough < 0 and t_peak > 0:
                    # Scenario 1: Pre/Post levels around a single dose
                    st.info("Using Pre/Post level calculation")
                    delta_t = current_interval - t_peak + abs(t_trough)

                    if delta_t <= 0:
                        st.error("Invalid time calculations (delta_t <= 0). Please check your sampling times.")
                        return # Stop execution if time calculation is invalid

                    ke_ind = math.log(measured_peak / measured_trough) / delta_t
                    ke_ind = max(1e-6, abs(ke_ind))  # Ensure positive ke
                    t_half_ind = 0.693 / ke_ind

                    if t_peak > infusion_duration:
                        cmax_ind = measured_peak * math.exp(ke_ind * (t_peak - infusion_duration))
                    else:
                        cmax_ind = measured_peak / (t_peak / infusion_duration) if infusion_duration > 0 else measured_peak # Avoid division by zero

                    cmin_ind = cmax_ind * math.exp(-ke_ind * (current_interval - infusion_duration))

                else:
                    # Scenario 2: Traditional PK (both levels after dose, potentially across intervals)
                    st.info("Using traditional PK calculation")

                    # Adjust times if they cross midnight relative to dose time
                    if t_peak < 0: t_peak += 24
                    if t_trough < 0: t_trough += 24 # Assuming trough is before next dose start

                    # Ensure peak time is after trough time for calculation
                    if t_peak > t_trough:
                        delta_t = t_peak - t_trough
                        level1, level2 = measured_trough, measured_peak
                        t1, t2 = t_trough, t_peak
                    elif t_trough > t_peak: # Trough measured after peak sample in the same interval
                        delta_t = t_trough - t_peak
                        level1, level2 = measured_peak, measured_trough
                        t1, t2 = t_peak, t_trough
                    else: # t_peak == t_trough, cannot calculate ke
                         st.error("Peak and Trough cannot be drawn at the exact same time.")
                         return
