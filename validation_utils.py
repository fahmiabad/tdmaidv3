# validation_utils.py
import streamlit as st
import math
from datetime import datetime, timedelta

class ValidationUtils:
    @staticmethod
    def validate_vancomycin_inputs(dose, interval, level, time_since_dose=None, patient_data=None):
        """
        Validate inputs for vancomycin calculations and provide warnings
        
        Parameters:
        - dose: Current dose in mg
        - interval: Current dosing interval in hours
        - level: Measured drug level in mg/L
        - time_since_dose: Time between dose and level measurement in hours (optional)
        - patient_data: Dictionary with patient information (optional)
        
        Returns:
        - List of warnings
        - List of errors
        """
        warnings = []
        errors = []
        
        # Default values if patient_data not provided
        weight = patient_data.get('weight', 70) if patient_data else 70
        crcl = patient_data.get('crcl', 90) if patient_data else 90
        
        # Dose validation
        if dose < 250 and weight > 40:
            warnings.append("Dose may be too low for adult patient")
        elif dose > 2000 and crcl < 50:
            warnings.append("Dose may be too high for patient with reduced renal function")
        
        if dose > 20 * weight and weight > 40:  # Adult
            warnings.append(f"Dose ({dose} mg) exceeds 20 mg/kg (patient weight: {weight} kg)")
        
        # Interval validation
        if interval < 12 and crcl < 30:
            warnings.append(f"Short interval ({interval}h) with CrCl of {crcl:.1f} mL/min may increase toxicity risk")
        
        # Level validation
        if level > 40:
            warnings.append("Level is unusually high. Verify sample timing and measurement")
        elif level < 3:
            warnings.append("Level is unusually low. Verify sample timing and measurement")
        
        # Time validation (if provided)
        if time_since_dose is not None:
            if time_since_dose < 0:
                errors.append("Negative time since dose. Please check timing inputs")
            elif time_since_dose > interval + 2:  # Allow slight overflow
                warnings.append(f"Time since dose ({time_since_dose:.1f}h) exceeds dosing interval ({interval}h). Verify timing")
        
        return warnings, errors
    
    @staticmethod
    def validate_aminoglycoside_inputs(drug, dose, interval, level, time_since_dose=None, patient_data=None):
        """
        Validate inputs for aminoglycoside calculations and provide warnings
        
        Parameters:
        - drug: "Gentamicin" or "Amikacin"
        - dose: Current dose in mg
        - interval: Current dosing interval in hours
        - level: Measured drug level in mg/L
        - time_since_dose: Time between dose and level measurement in hours (optional)
        - patient_data: Dictionary with patient information (optional)
        
        Returns:
        - List of warnings
        - List of errors
        """
        warnings = []
        errors = []
        
        # Default values if patient_data not provided
        weight = patient_data.get('weight', 70) if patient_data else 70
        crcl = patient_data.get('crcl', 90) if patient_data else 90
        
        # Dose validation based on drug
        if drug == "Gentamicin":
            if dose < 80 and weight > 40:
                warnings.append("Dose may be too low for adult patient")
            elif dose > 8 * weight:
                warnings.append(f"Dose ({dose} mg) exceeds 8 mg/kg (patient weight: {weight} kg)")
        else:  # Amikacin
            if dose < 300 and weight > 40:
                warnings.append("Dose may be too low for adult patient")
            elif dose > 25 * weight:
                warnings.append(f"Dose ({dose} mg) exceeds 25 mg/kg (patient weight: {weight} kg)")
        
        # Interval validation
        if interval < 24 and crcl < 30:
            warnings.append(f"Short interval ({interval}h) with CrCl of {crcl:.1f} mL/min increases toxicity risk")
        
        # Level validation
        if drug == "Gentamicin":
            if level > 20:
                warnings.append("Level is unusually high for Gentamicin. Verify sample timing and measurement")
        else:  # Amikacin
            if level > 60:
                warnings.append("Level is unusually high for Amikacin. Verify sample timing and measurement")
        
        # Time validation (if provided)
        if time_since_dose is not None:
            if time_since_dose < 0:
                errors.append("Negative time since dose. Please check timing inputs")
            elif time_since_dose > interval + 2:  # Allow slight overflow
                warnings.append(f"Time since dose ({time_since_dose:.1f}h) exceeds dosing interval ({interval}h). Verify timing")
        
        return warnings, errors
    
    @staticmethod
    def validate_peak_trough_timing(peak_time, trough_time, dose_time, interval):
        """
        Validate peak and trough timing relative to dose administration
        
        Parameters:
        - peak_time: Time of peak measurement (hours since dose)
        - trough_time: Time of trough measurement (hours since dose)
        - dose_time: Time of dose administration
        - interval: Dosing interval in hours
        
        Returns:
        - List of warnings
        - List of errors
        """
        warnings = []
        errors = []
        
        # Check for invalid times
        if peak_time < 0 or trough_time < 0:
            errors.append("Sample time cannot be before dose administration")
        
        # Check if samples are too close
        if abs(peak_time - trough_time) < 1:
            errors.append("Peak and trough samples are too close together for accurate calculations")
        
        # Traditional peak-trough timing expectations
        if peak_time > 0 and peak_time < 1:
            warnings.append("Peak sample drawn too early (before end of distribution phase)")
        
        if peak_time > 4:
            warnings.append("Peak sample drawn later than typical (standard is 30min-1hr after end of infusion)")
        
        # Trough timing expectations
        if trough_time < interval - 2:
            warnings.append(f"Trough sample drawn earlier than ideal (standard is within 30min of next dose)")
        
        if trough_time > interval + 2:
            warnings.append("Trough sample drawn after scheduled next dose time")
        
        return warnings, errors
    
    @staticmethod
    def display_validation_results(warnings, errors):
        """
        Display validation warnings and errors with proper formatting
        
        Parameters:
        - warnings: List of warning strings
        - errors: List of error strings
        
        Returns:
        - Boolean indicating whether validation passed (True) or failed (False)
        """
        if errors:
            st.error("Please correct the following errors before proceeding:")
            for error in errors:
                st.error(f"• {error}")
            return False  # Validation failed
        
        if warnings:
            st.warning("Please review the following warnings:")
            for warning in warnings:
                st.warning(f"• {warning}")
        
        return True  # Validation passed (may have warnings)
    
    @staticmethod
    def calculate_with_error_handling(func, *args, **kwargs):
        """
        Wrapper for calculation functions with improved error handling
        
        Parameters:
        - func: Function to call
        - *args, **kwargs: Arguments to pass to the function
        
        Returns:
        - Result from the function (or None if error)
        - Error message (or None if successful)
        """
        try:
            result = func(*args, **kwargs)
            return result, None
        except ZeroDivisionError:
            return None, "Calculation error: Division by zero. Check if interval or infusion duration is zero."
        except ValueError as e:
            if "log" in str(e).lower():
                return None, "Calculation error: Cannot take logarithm of zero or negative number. Check your concentration values."
            else:
                return None, f"Value error: {str(e)}. Check your input values."
        except OverflowError as e:
            return None, f"Calculation error: Numerical overflow occurred. This might indicate extreme values or very long intervals."
        except Exception as e:
            return None, f"Unexpected error: {str(e)}. Please verify all inputs."
    
    @staticmethod
    def validate_results(drug, pk_params, levels, patient_data=None):
        """
        Validate calculated PK parameters and levels for clinical plausibility
        
        Parameters:
        - drug: Drug name (e.g., "Vancomycin", "Gentamicin")
        - pk_params: Dictionary of PK parameters (ke, t_half, vd, cl)
        - levels: Dictionary of calculated levels (peak, trough, auc)
        - patient_data: Dictionary with patient information (optional)
        
        Returns:
        - List of warnings
        - List of errors
        """
        warnings = []
        errors = []
        
        # Default values if patient_data not provided
        weight = patient_data.get('weight', 70) if patient_data else 70
        crcl = patient_data.get('crcl', 90) if patient_data else 90
        
        # Check PK parameters
        if 'ke' in pk_params:
            ke = pk_params['ke']
            if ke < 0.01:
                warnings.append(f"Elimination rate constant is unusually low (ke = {ke:.4f})")
            elif ke > 0.3:
                warnings.append(f"Elimination rate constant is unusually high (ke = {ke:.4f})")
        
        if 't_half' in pk_params:
            t_half = pk_params['t_half']
            if drug == "Vancomycin":
                if t_half < 4:
                    warnings.append(f"Half-life is unusually short for Vancomycin (t½ = {t_half:.1f}h)")
                elif t_half > 150:
                    warnings.append(f"Half-life is extremely long (t½ = {t_half:.1f}h). Verify renal function.")
            else:  # Aminoglycosides
                if t_half < 1:
                    warnings.append(f"Half-life is unusually short (t½ = {t_half:.1f}h)")
                elif t_half > 50:
                    warnings.append(f"Half-life is extremely long (t½ = {t_half:.1f}h). Verify renal function.")
        
        if 'vd' in pk_params:
            vd = pk_params['vd']
            if drug == "Vancomycin":
                expected_vd = weight * 0.7  # L/kg
                if vd < expected_vd * 0.5 or vd > expected_vd * 2:
                    warnings.append(f"Volume of distribution ({vd:.1f}L) differs significantly from population estimate ({expected_vd:.1f}L)")
            else:  # Aminoglycosides
                expected_vd = weight * 0.3  # L/kg for aminoglycosides
                if vd < expected_vd * 0.5 or vd > expected_vd * 2:
                    warnings.append(f"Volume of distribution ({vd:.1f}L) differs significantly from population estimate ({expected_vd:.1f}L)")
        
        # Check calculated levels
        if drug == "Vancomycin":
            if 'peak' in levels:
                peak = levels['peak']
                if peak > 80:
                    warnings.append(f"Calculated peak ({peak:.1f} mg/L) is unusually high")
                elif peak < 10:
                    warnings.append(f"Calculated peak ({peak:.1f} mg/L) is unusually low")
            
            if 'trough' in levels:
                trough = levels['trough']
                if trough > 30:
                    warnings.append(f"Calculated trough ({trough:.1f} mg/L) is unusually high. Risk of nephrotoxicity.")
            
            if 'auc' in levels:
                auc = levels['auc']
                if auc > 800:
                    warnings.append(f"Calculated AUC ({auc:.0f} mg·hr/L) is very high. Risk of nephrotoxicity.")
                elif auc < 200:
                    warnings.append(f"Calculated AUC ({auc:.0f} mg·hr/L) is very low. Risk of therapeutic failure.")
        
        else:  # Aminoglycosides
            if drug == "Gentamicin":
                if 'peak' in levels and levels['peak'] > 20:
                    warnings.append(f"Calculated peak ({levels['peak']:.1f} mg/L) is unusually high")
                
                if 'trough' in levels and levels['trough'] > 4:
                    warnings.append(f"Calculated trough ({levels['trough']:.1f} mg/L) is high. Risk of toxicity.")
            
            elif drug == "Amikacin":
                if 'peak' in levels and levels['peak'] > 60:
                    warnings.append(f"Calculated peak ({levels['peak']:.1f} mg/L) is unusually high")
                
                if 'trough' in levels and levels['trough'] > 10:
                    warnings.append(f"Calculated trough ({levels['trough']:.1f} mg/L) is high. Risk of toxicity.")
        
        return warnings, errors
