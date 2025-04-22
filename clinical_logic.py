# clinical_logic.py
import streamlit as st
import os

class ClinicalInterpreter:
    def __init__(self, drug, regimen, targets):
        self.drug = drug
        self.regimen = regimen
        self.targets = targets
    
    def assess_levels(self, levels):
        """Assess levels against target ranges and return status"""
        assessment = []
        status = "therapeutic"
        
        if self.drug == "Vancomycin":
            # AUC assessment for vancomycin
            if 'auc' in levels and 'auc' in self.targets:
                auc = levels['auc']
                auc_min = self.targets['auc']['min']
                auc_max = self.targets['auc']['max']
                
                if auc < auc_min:
                    assessment.append(f"AUC₂₄ ({auc:.0f} mg·hr/L) is below target ({auc_min}-{auc_max} mg·hr/L)")
                    status = "subtherapeutic"
                elif auc > auc_max:
                    assessment.append(f"AUC₂₄ ({auc:.0f} mg·hr/L) is above target ({auc_min}-{auc_max} mg·hr/L)")
                    status = "high"
                else:
                    assessment.append(f"AUC₂₄ ({auc:.0f} mg·hr/L) is within target range")
            
            # Trough assessment for vancomycin
            if 'trough' in levels:
                trough = levels['trough']
                trough_min = self.targets['trough']['min']
                trough_max = self.targets['trough']['max']
                
                if trough < trough_min:
                    assessment.append(f"Trough ({trough:.1f} mg/L) is below target ({trough_min}-{trough_max} mg/L)")
                elif trough > trough_max:
                    assessment.append(f"Trough ({trough:.1f} mg/L) is above target ({trough_min}-{trough_max} mg/L)")
                    status = "toxic" if status == "high" else "high"
                else:
                    assessment.append(f"Trough ({trough:.1f} mg/L) is within target range")
        
        else:  # Aminoglycosides
            peak_min = self.targets['peak']['min']
            peak_max = self.targets['peak']['max']
            trough_max = self.targets['trough']['max']
            trough_min = self.targets['trough']['min']
            
            # Peak assessment
            if levels['peak'] < peak_min:
                assessment.append(f"Peak ({levels['peak']:.1f} mg/L) is below target ({peak_min}-{peak_max} mg/L)")
                status = "subtherapeutic"
            elif levels['peak'] > peak_max:
                assessment.append(f"Peak ({levels['peak']:.1f} mg/L) is above target ({peak_min}-{peak_max} mg/L)")
                status = "high"
            else:
                assessment.append(f"Peak ({levels['peak']:.1f} mg/L) is within target range")
            
            # Trough assessment
            if levels['trough'] > trough_max:
                assessment.append(f"Trough ({levels['trough']:.1f} mg/L) is above target (<{trough_max} mg/L)")
                status = "toxic" if status == "high" else "high"
            elif levels['trough'] < trough_min:
                assessment.append(f"Trough ({levels['trough']:.1f} mg/L) is below target ({trough_min}-{trough_max} mg/L)")
            else:
                assessment.append(f"Trough ({levels['trough']:.1f} mg/L) is within acceptable range")
        
        return assessment, status
    
    def generate_recommendations(self, status, crcl):
        """Generate clinical recommendations based on status"""
        recommendations = []
        
        if self.drug == "Vancomycin":
            if status == "subtherapeutic":
                recommendations.append("Consider increasing dose to achieve target AUC")
                recommendations.append("Monitor for clinical response and signs of infection")
            elif status == "high":
                recommendations.append("Consider reducing dose to avoid toxicity")
                recommendations.append("Monitor for signs of nephrotoxicity")
                recommendations.append("Consider extending dosing interval if trough is elevated")
            elif status == "toxic":
                recommendations.append("Reduce dose immediately")
                recommendations.append("Monitor renal function closely")
                recommendations.append("Consider holding next dose if trough is significantly elevated")
            else:
                recommendations.append("Current regimen achieves therapeutic targets")
                recommendations.append("Continue monitoring levels per protocol")
            
            # Special considerations
            if crcl < 30:
                recommendations.append("Close monitoring needed due to reduced renal function")
                recommendations.append("Consider extending dosing interval")
            
            recommendations.append("Continue therapeutic drug monitoring with trough levels")
        
        else:  # Aminoglycosides
            if status == "subtherapeutic":
                recommendations.append("Increase dose to achieve therapeutic peak")
                recommendations.append("Consider clinical efficacy and MIC")
            elif status == "high":
                recommendations.append("Consider reducing dose or extending interval")
                recommendations.append("Monitor for signs of toxicity")
            elif status == "toxic":
                recommendations.append("Extend interval immediately")
                recommendations.append("Monitor for nephrotoxicity and ototoxicity")
                recommendations.append("Consider dose reduction if interval extension alone insufficient")
            else:
                recommendations.append("Current regimen achieves therapeutic targets")
                recommendations.append("Continue monitoring per protocol")
            
            # Special considerations
            if self.regimen == "extended_interval":
                recommendations.append("Ensure adequate interval to allow trough <1 mg/L")
            
            if crcl < 30:
                recommendations.append("Increased risk of toxicity - close monitoring required")
                recommendations.append("Consider alternative antimicrobial if possible")
        
        return recommendations
    
    def format_recommendations(self, assessment, status, recommendations, patient_data=None):
        """Format recommendations in markdown with patient details"""
        formatted = ""
        
        if patient_data:
            formatted += f"""
**Patient Information:**
- Patient ID: {patient_data['patient_id']}
- Ward: {patient_data['ward']}
- Diagnosis: {patient_data.get('diagnosis', 'N/A')}
- Current Regimen: {patient_data.get('current_regimen', 'N/A')}
- Renal Function: {patient_data['renal_function']}

"""
        
        formatted += f"""
**Assessment:** {status.capitalize()}

**Findings:**
"""
        for item in assessment:
            formatted += f"- {item}\n"
        
        formatted += "\n**Recommendations:**\n"
        for item in recommendations:
            formatted += f"- {item}\n"
        
        return formatted
    
    def generate_llm_interpretation(self, pk_params, levels, recommendations, patient_data=None):
        """Generate detailed interpretation using LLM"""
        # Check if we have API key
        api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
        
        if not api_key:
            return "Note: LLM interpretation not available (API key not configured)"
        
        # This is a placeholder for LLM integration
        # In production, you would integrate with OpenAI API here
        assessment, status = self.assess_levels(levels)
        return self.format_recommendations(
            assessment,
            status,
            self.generate_recommendations(status, pk_params.get('crcl', 80)),
            patient_data
        )
