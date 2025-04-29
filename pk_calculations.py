# pk_calculations.py
import math
from config import DRUG_CONFIGS

class PKCalculator:
    def __init__(self, drug, weight, crcl):
        self.drug = drug
        self.weight = weight
        self.crcl = crcl
        self.config = DRUG_CONFIGS[drug]["pk_parameters"]
    
    def calculate_initial_parameters(self):
        """Calculate initial PK parameters based on population estimates with improved safety checks."""
        vd = self.config["Vd_L_kg"] * self.weight
        
        if self.drug == "Vancomycin":
            # For vancomycin, clearance is typically calculated as:
            # CL (L/hr) = CrCl (mL/min) * 0.8 * 60 / 1000
            cl = self.crcl * self.config["cl_factor"] * 60 / 1000
        else:
            # For aminoglycosides
            cl = self.crcl * self.config["cl_factor"] * 60 / 1000
        
        # Safety checks
        cl = max(0.1, min(cl, 15))  # Reasonable clearance range (L/hr)
        ke = cl / vd if vd > 0 else 0.01
        ke = max(0.005, min(ke, 0.4))  # Reasonable ke range (hr⁻¹)
        t_half = 0.693 / ke if ke > 0 else float('inf')
        
        return {
            "vd": vd,
            "cl": cl,
            "ke": ke,
            "t_half": t_half
        }
    
    def calculate_dose(self, target_peak, target_trough, tau, infusion_duration):
        """Calculate dose to achieve target levels with improved error handling."""
        pk_params = self.calculate_initial_parameters()
        vd, ke = pk_params["vd"], pk_params["ke"]
        
        try:
            # Safety checks for extreme values
            if tau <= 0 or infusion_duration <= 0:
                return 0, pk_params
                
            term_inf = 1 - math.exp(-ke * infusion_duration)
            term_tau = 1 - math.exp(-ke * tau)
            
            if abs(term_inf) > 1e-9 and abs(term_tau) > 1e-9:
                dose = (target_peak * vd * ke * infusion_duration * term_tau) / term_inf
            else:
                # Fallback for very short infusions
                dose = target_peak * vd * (1 - math.exp(-ke * tau))
            
            # Safety check for unrealistic doses
            if dose <= 0 or dose > 5000:  # Dose sanity check
                return self._round_dose(1000), pk_params  # Return a default dose as fallback
                
            return self._round_dose(dose), pk_params
        except (OverflowError, ValueError, ZeroDivisionError):
            # Fallback to a reasonable default dose based on drug and weight
            if self.drug == "Vancomycin":
                default_dose = 15 * self.weight  # ~15 mg/kg
            else:  # Aminoglycosides
                default_dose = 5 * self.weight   # ~5 mg/kg
                
            return self._round_dose(default_dose), pk_params
    
    def _round_dose(self, dose):
        """Round to practical dose increments with improved handling of edge cases."""
        base = self.config["rounding_base"]
        
        # Ensure base is positive
        if base <= 0:
            base = 50  # Default fallback
            
        # Floor division and multiply to round down to nearest base
        rounded_dose = int(dose / base) * base
        
        # If rounding down would make it zero, use the base value
        if rounded_dose < base and dose > 0:
            rounded_dose = base
            
        return max(base, rounded_dose)
    
    def predict_levels(self, dose, tau, infusion_duration):
        """Predict peak and trough levels for a given dose with improved error handling."""
        pk_params = self.calculate_initial_parameters()
        vd, ke = pk_params["vd"], pk_params["ke"]
        
        try:
            # Safety checks
            if tau <= 0 or infusion_duration <= 0 or dose <= 0:
                return {"peak": 0, "trough": 0}
                
            term_inf = 1 - math.exp(-ke * infusion_duration)
            term_tau = 1 - math.exp(-ke * tau)
            denom = vd * ke * infusion_duration * term_tau
            
            if abs(denom) > 1e-9 and abs(term_inf) > 1e-9:
                peak = (dose * term_inf) / denom
                # Safety check for unrealistic peak
                peak = max(0, min(peak, 100))  # Cap at reasonable maximum
                
                trough = peak * math.exp(-ke * (tau - infusion_duration))
                # Safety check for unrealistic trough
                trough = max(0, min(trough, 50))  # Cap at reasonable maximum
                
                return {"peak": peak, "trough": trough}
            
            return {"peak": 0, "trough": 0}
        except (OverflowError, ValueError, ZeroDivisionError):
            return {"peak": 0, "trough": 0}
    
    def calculate_vancomycin_auc(self, cmax, cmin, ke, tau, infusion_duration):
        """Calculate vancomycin AUC using trapezoidal method with improved error handling."""
        try:
            # Safety checks
            if ke <= 0 or tau <= 0 or infusion_duration <= 0:
                return 0
                
            # Calculate concentration at start of infusion
            c0 = cmax * math.exp(ke * infusion_duration) if cmax > 0 else 0
            
            # AUC during infusion phase (linear trapezoid)
            auc_inf = infusion_duration * (c0 + cmax) / 2
            
            # AUC during elimination phase (log trapezoid)
            if ke > 0 and cmax > cmin and cmin > 0:
                auc_elim = (cmax - cmin) / ke
            else:
                # Fallback to linear approximation if log method fails
                auc_elim = (tau - infusion_duration) * (cmax + cmin) / 2
            
            # Total AUC for one interval
            auc_interval = auc_inf + auc_elim
            
            # Convert to AUC24
            auc24 = auc_interval * (24 / tau)
            
            # Safety check for unrealistic values
            return max(0, min(auc24, 1500))  # Cap at reasonable maximum
        except (OverflowError, ValueError, ZeroDivisionError):
            return 0
    
    def estimate_ke_from_levels(self, level1, time1, level2, time2):
        """
        Estimate elimination rate constant from two concentration measurements
        
        Parameters:
        - level1, level2: Two concentration measurements (mg/L)
        - time1, time2: Times when levels were drawn (hours from dose)
        
        Returns:
        - ke: Estimated elimination rate constant (hr⁻¹)
        """
        try:
            # Validate inputs
            if level1 <= 0 or level2 <= 0 or time1 >= time2:
                return None
                
            # Calculate ke
            time_diff = time2 - time1
            ke = (math.log(level1) - math.log(level2)) / time_diff
            
            # Safety check for unrealistic ke
            ke = max(0.005, min(abs(ke), 0.4))  # Reasonable ke range (hr⁻¹)
            
            return ke
        except (ValueError, ZeroDivisionError, OverflowError):
            return None
    
    def extrapolate_level(self, measured_level, measured_time, target_time, ke):
        """
        Extrapolate concentration to a different time point
        
        Parameters:
        - measured_level: Measured concentration (mg/L)
        - measured_time: Time when level was drawn (hours from dose)
        - target_time: Time to extrapolate to (hours from dose)
        - ke: Elimination rate constant (hr⁻¹)
        
        Returns:
        - Extrapolated concentration (mg/L)
        """
        try:
            # Validate inputs
            if measured_level <= 0 or ke <= 0:
                return 0
                
            # Calculate time difference
            time_diff = target_time - measured_time
            
            # Extrapolate using first-order kinetics
            extrapolated_level = measured_level * math.exp(-ke * time_diff)
            
            # Safety check for unrealistic values
            extrapolated_level = max(0, min(extrapolated_level, 100))  # Cap at reasonable maximum
            
            return extrapolated_level
        except (ValueError, OverflowError):
            return 0
