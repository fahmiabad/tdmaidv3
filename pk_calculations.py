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
        """Calculate initial PK parameters based on population estimates."""
        vd = self.config["Vd_L_kg"] * self.weight
        
        if self.drug == "Vancomycin":
            # For vancomycin, clearance is typically calculated as:
            # CL (L/hr) = CrCl (mL/min) * 0.8 * 60 / 1000
            cl = self.crcl * self.config["cl_factor"] * 60 / 1000
        else:
            # For aminoglycosides
            cl = self.crcl * self.config["cl_factor"] * 60 / 1000
        
        cl = max(0.1, cl)  # Minimum clearance
        ke = cl / vd if vd > 0 else 0.01
        ke = max(0.005, ke)  # Minimum Ke
        t_half = 0.693 / ke if ke > 0 else float('inf')
        
        return {
            "vd": vd,
            "cl": cl,
            "ke": ke,
            "t_half": t_half
        }
    
    def calculate_dose(self, target_peak, target_trough, tau, infusion_duration):
        """Calculate dose to achieve target levels."""
        pk_params = self.calculate_initial_parameters()
        vd, ke = pk_params["vd"], pk_params["ke"]
        
        try:
            term_inf = 1 - math.exp(-ke * infusion_duration)
            term_tau = 1 - math.exp(-ke * tau)
            
            if abs(term_inf) > 1e-9:
                dose = (target_peak * vd * ke * infusion_duration * term_tau) / term_inf
            else:
                # Fallback for very short infusions
                dose = target_peak * vd * (1 - math.exp(-ke * tau))
            
            return self._round_dose(dose), pk_params
        except (OverflowError, ValueError):
            return 0, pk_params
    
    def _round_dose(self, dose):
        """Round to practical dose increments."""
        base = self.config["rounding_base"]
        return max(base, round(dose / base) * base)
    
    def predict_levels(self, dose, tau, infusion_duration):
        """Predict peak and trough levels for a given dose."""
        pk_params = self.calculate_initial_parameters()
        vd, ke = pk_params["vd"], pk_params["ke"]
        
        try:
            term_inf = 1 - math.exp(-ke * infusion_duration)
            term_tau = 1 - math.exp(-ke * tau)
            denom = vd * ke * infusion_duration * term_tau
            
            if abs(denom) > 1e-9 and abs(term_inf) > 1e-9:
                peak = (dose * term_inf) / denom
                trough = peak * math.exp(-ke * (tau - infusion_duration))
                return {"peak": peak, "trough": trough}
            
            return {"peak": 0, "trough": 0}
        except (OverflowError, ValueError):
            return {"peak": 0, "trough": 0}
    
    def calculate_vancomycin_auc(self, cmax, cmin, ke, tau, infusion_duration):
        """Calculate vancomycin AUC using trapezoidal method."""
        try:
            # Calculate concentration at start of infusion
            c0 = cmax * math.exp(ke * infusion_duration)
            
            # AUC during infusion phase (linear trapezoid)
            auc_inf = infusion_duration * (c0 + cmax) / 2
            
            # AUC during elimination phase (log trapezoid)
            if ke > 0 and cmax > cmin:
                auc_elim = (cmax - cmin) / ke
            else:
                auc_elim = (tau - infusion_duration) * (cmax + cmin) / 2
            
            # Total AUC for one interval
            auc_interval = auc_inf + auc_elim
            
            # Convert to AUC24
            auc24 = auc_interval * (24 / tau)
            
            return auc24
        except (OverflowError, ValueError):
            return 0
