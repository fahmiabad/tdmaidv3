# clinical_logic.py
import streamlit as st

class ClinicalInterpreter:
    def __init__(self, drug, regimen, targets):
        self.drug = drug
        self.regimen = regimen
        self.targets = targets
    
    def assess_levels(self, measured_levels):
        """Assess levels against targets."""
        assessment = []
        overall_status = "appropriately dosed"
        
        for level_type, value in measured_levels.items():
            if level_type in self.targets:
                target = self.targets[level_type]
                if isinstance(value, (int, float)):
                    status = self._assess_single_level(value, target['min'], target['max'])
                    assessment.append({
                        'name': level_type.capitalize(),
                        'value': value,
                        'target': target['info'],
                        'status': status
                    })
                    
                    # Determine overall status
                    if status == "above" and level_type == "trough":
                        overall_status = "potentially toxic"
                    elif status == "below" and level_type == "peak":
                        if overall_status == "appropriately dosed":
                            overall_status = "subtherapeutic"
        
        return assessment, overall_status
    
    def _assess_single_level(self, value, min_target, max_target):
        """Assess a single level."""
        if value < min_target:
            return "below"
        elif value > max_target:
            return "above"
        return "within"
    
    def generate_recommendations(self, overall_status, crcl=None):
        """Generate clinical recommendations."""
        dosing_recs = []
        monitoring_recs = []
        cautions = []
        
        # Basic recommendations based on status
        if overall_status == "appropriately dosed":
            dosing_recs.append("CONTINUE current regimen")
            monitoring_recs.append("MONITOR renal function per protocol")
            monitoring_recs.append("REPEAT levels if clinical status changes")
        elif overall_status == "subtherapeutic":
            dosing_recs.append("INCREASE dose or shorten interval")
            monitoring_recs.append("RECHECK levels after adjustment")
        elif overall_status == "potentially toxic":
            dosing_recs.append("REDUCE dose or lengthen interval")
            monitoring_recs.append("MONITOR renal function daily")
            monitoring_recs.append("RECHECK levels within 24-48 hours")
            cautions.append("Risk of toxicity - close monitoring required")
        
        # Add renal function considerations
        if crcl and crcl < 60:
            cautions.append(f"Impaired renal function (CrCl: {crcl:.1f} mL/min) - adjust carefully")
            monitoring_recs.append("More frequent monitoring of renal function recommended")
        
        # Drug-specific cautions
        if self.drug in ["Gentamicin", "Amikacin"]:
            cautions.append(f"{self.drug} carries risk of nephrotoxicity and ototoxicity")
            if overall_status == "potentially toxic":
                cautions.append("Monitor for signs of nephrotoxicity (rising SCr) and ototoxicity")
        
        return {
            'dosing': dosing_recs,
            'monitoring': monitoring_recs,
            'cautions': cautions
        }
    
    def format_recommendations(self, assessment, status, recommendations):
        """Format recommendations for display."""
        output = "## CLINICAL ASSESSMENT\n\n"
        output += "📊 **MEASURED/ESTIMATED LEVELS:**\n"
        
        for item in assessment:
            icon = "✅" if item['status'] == "within" else "⚠️" if item['status'] == "below" else "🔴"
            output += f"- {item['name']}: {item['value']:.1f} mg/L (Target: {item['target']}) {icon}\n"
        
        output += f"\n⚕️ **ASSESSMENT:**\nPatient is **{status.upper()}**\n\n"
        output += "## RECOMMENDATIONS\n\n"
        output += "🔵 **DOSING:**\n"
        
        for rec in recommendations['dosing']:
            output += f"- {rec}\n"
        
        output += "\n🔵 **MONITORING:**\n"
        for rec in recommendations['monitoring']:
            output += f"- {rec}\n"
        
        if recommendations['cautions']:
            output += "\n⚠️ **CAUTIONS:**\n"
            for caution in recommendations['cautions']:
                output += f"- {caution}\n"
        
        return output
