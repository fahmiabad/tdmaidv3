# clinical_logic.py
import streamlit as st
import os
from datetime import datetime, timedelta

class ClinicalInterpreter:
    def __init__(self, drug, regimen, targets):
        self.drug = drug
        self.regimen = regimen
        self.targets = targets
    
    def assess_levels(self, levels):
        """Assess levels against target ranges with clear status indicators"""
        assessment = []
        status = "therapeutic"
        
        if self.drug == "Vancomycin":
            # AUC assessment for vancomycin
            if 'auc' in levels and 'auc' in self.targets:
                auc = levels['auc']
                auc_min = self.targets['auc']['min']
                auc_max = self.targets['auc']['max']
                
                if auc < auc_min:
                    assessment.append(f"BELOW THERAPEUTIC RANGE: AUC₂₄ ({auc:.0f} mg·hr/L) is below target ({auc_min}-{auc_max} mg·hr/L)")
                    status = "subtherapeutic"
                elif auc > auc_max:
                    assessment.append(f"ABOVE THERAPEUTIC RANGE: AUC₂₄ ({auc:.0f} mg·hr/L) is above target ({auc_min}-{auc_max} mg·hr/L)")
                    status = "high"
                else:
                    assessment.append(f"WITHIN THERAPEUTIC RANGE: AUC₂₄ ({auc:.0f} mg·hr/L) is within target range ({auc_min}-{auc_max} mg·hr/L)")
            
            # Trough assessment for vancomycin
            if 'trough' in levels:
                trough = levels['trough']
                trough_min = self.targets['trough']['min']
                trough_max = self.targets['trough']['max']
                
                if trough < trough_min:
                    assessment.append(f"BELOW THERAPEUTIC RANGE: Trough ({trough:.1f} mg/L) is below target ({trough_min}-{trough_max} mg/L)")
                    # Only override status if AUC isn't already out of range
                    if status == "therapeutic":
                        status = "subtherapeutic"
                elif trough > trough_max:
                    assessment.append(f"ABOVE THERAPEUTIC RANGE: Trough ({trough:.1f} mg/L) is above target ({trough_min}-{trough_max} mg/L)")
                    status = "toxic" if status == "high" else "high"
                else:
                    assessment.append(f"WITHIN THERAPEUTIC RANGE: Trough ({trough:.1f} mg/L) is within target range ({trough_min}-{trough_max} mg/L)")
        
        else:  # Aminoglycosides
            # Peak assessment with clear labeling
            peak_min = self.targets['peak']['min']
            peak_max = self.targets['peak']['max']
            trough_max = self.targets['trough']['max']
            trough_min = self.targets['trough']['min']
            
            # Peak assessment
            if levels['peak'] < peak_min:
                assessment.append(f"BELOW THERAPEUTIC RANGE: Peak ({levels['peak']:.1f} mg/L) is below target ({peak_min}-{peak_max} mg/L)")
                status = "subtherapeutic"
            elif levels['peak'] > peak_max:
                assessment.append(f"ABOVE THERAPEUTIC RANGE: Peak ({levels['peak']:.1f} mg/L) is above target ({peak_min}-{peak_max} mg/L)")
                status = "high"
            else:
                assessment.append(f"WITHIN THERAPEUTIC RANGE: Peak ({levels['peak']:.1f} mg/L) is within target range ({peak_min}-{peak_max} mg/L)")
            
            # Trough assessment
            if levels['trough'] > trough_max:
                assessment.append(f"ABOVE THERAPEUTIC RANGE: Trough ({levels['trough']:.1f} mg/L) is above target (<{trough_max} mg/L)")
                status = "toxic" if status == "high" else "high"
            elif levels['trough'] < trough_min:
                assessment.append(f"BELOW THERAPEUTIC RANGE: Trough ({levels['trough']:.1f} mg/L) is below target ({trough_min}-{trough_max} mg/L)")
            else:
                assessment.append(f"WITHIN THERAPEUTIC RANGE: Trough ({levels['trough']:.1f} mg/L) is within acceptable range ({trough_min}-{trough_max} mg/L)")
        
        return assessment, status
    
    def evaluate_proposed_regimen(self, current_levels, proposed_levels):
        """
        Evaluate if a proposed regimen improves therapeutic outcomes
        Returns True if the proposed regimen is better than the current one
        """
        current_assessment, current_status = self.assess_levels(current_levels)
        proposed_assessment, proposed_status = self.assess_levels(proposed_levels)
        
        # Define status priority (worst to best)
        status_priority = {
            "toxic": 0,
            "high": 1,
            "subtherapeutic": 2,
            "therapeutic": 3
        }
        
        # If proposed status is better than current, approve change
        if status_priority[proposed_status] > status_priority[current_status]:
            return True
            
        # If proposed status is worse than current, reject change
        if status_priority[proposed_status] < status_priority[current_status]:
            return False
            
        # If status is the same, need more detailed analysis
        if self.drug == "Vancomycin" and 'auc' in current_levels and 'auc' in proposed_levels:
            # For vancomycin, prioritize AUC optimization
            auc_target_mid = (self.targets['auc']['min'] + self.targets['auc']['max']) / 2
            
            # Calculate how close each regimen gets to the middle of the AUC target range
            current_auc_deviation = abs(current_levels['auc'] - auc_target_mid)
            proposed_auc_deviation = abs(proposed_levels['auc'] - auc_target_mid)
            
            # If proposed gets us closer to target midpoint, approve change
            return proposed_auc_deviation < current_auc_deviation
            
        # For other scenarios and drugs, if both regimens have the same status, prefer current regimen
        return False
    
    def generate_recommendations(self, status, crcl, indication=None):
        """Generate more specific clinical recommendations based on status and patient factors"""
        recommendations = []
        
        if self.drug == "Vancomycin":
            if status == "subtherapeutic":
                recommendations.append("Increase dose to achieve target AUC and improve clinical efficacy")
                
                # Add specific recommendations based on severity of subtherapeutic level
                if 'auc' in self.targets and hasattr(self, 'levels') and 'auc' in self.levels:
                    auc = self.levels['auc']
                    auc_min = self.targets['auc']['min']
                    if auc < auc_min * 0.7:  # Severely low
                        recommendations.append("🚨 Significantly subtherapeutic AUC may lead to treatment failure - consider loading dose")
                
                # Add indication-specific recommendations
                if indication:
                    if "meningitis" in indication.lower() or "cns" in indication.lower():
                        recommendations.append("🚨 Critical: CNS infections require adequate drug levels for blood-brain barrier penetration")
                    elif "endocarditis" in indication.lower():
                        recommendations.append("🚨 Note: Endocarditis treatment requires consistent therapeutic levels")
                
                recommendations.append("Monitor for clinical response and signs of infection")
            
            elif status == "high":
                recommendations.append("Consider reducing dose to avoid toxicity while maintaining efficacy")
                
                if crcl < 60:
                    recommendations.append("Monitor renal function closely due to reduced clearance")
                    if crcl < 30:
                        recommendations.append("🚨 High risk of nephrotoxicity with reduced renal function - consider extending interval")
                
                recommendations.append("Consider extending dosing interval if trough is significantly elevated")
            
            elif status == "toxic":
                recommendations.append("Reduce dose immediately to minimize risk of nephrotoxicity")
                recommendations.append("🚨 Monitor renal function daily")
                
                if crcl < 50:
                    recommendations.append("🚨 Consider holding next dose if trough >25 mg/L and renal function is declining")
                
                recommendations.append("Increase hydration if clinically appropriate")
            
            else:  # therapeutic
                recommendations.append("Current regimen achieves therapeutic targets")
                recommendations.append("Continue monitoring levels per protocol")
                
                if crcl < 60:
                    recommendations.append("Continue monitoring renal function due to potential nephrotoxicity")
            
            # Special considerations for all statuses
            if crcl < 30:
                recommendations.append("Close monitoring needed due to severely reduced renal function")
                recommendations.append("Consider extending dosing interval to reduce toxicity risk")
            
            recommendations.append("Continue therapeutic drug monitoring with trough levels")
        
        else:  # Aminoglycosides
            if status == "subtherapeutic":
                recommendations.append("Increase dose to achieve therapeutic peak concentration")
                
                if 'peak' in self.targets and hasattr(self, 'levels') and 'peak' in self.levels:
                    peak = self.levels['peak']
                    peak_min = self.targets['peak']['min']
                    if peak < peak_min * 0.7:  # Severely low
                        recommendations.append("🚨 Significantly subtherapeutic peak may lead to treatment failure")
                
                recommendations.append("Consider clinical efficacy and pathogen MIC")
            
            elif status == "high":
                recommendations.append("Consider reducing dose or extending interval")
                recommendations.append("Monitor for signs of toxicity (vestibular, auditory, renal)")
                
                if crcl < 60:
                    recommendations.append("🚨 Increased risk of toxicity with reduced renal function")
            
            elif status == "toxic":
                recommendations.append("Extend interval immediately to reduce toxicity risk")
                recommendations.append("🚨 Monitor for nephrotoxicity and ototoxicity")
                recommendations.append("Consider dose reduction if interval extension alone insufficient")
                
                if crcl < 50:
                    recommendations.append("🚨 Consider alternative antimicrobial agent due to high toxicity risk")
            
            else:  # therapeutic
                recommendations.append("Current regimen achieves therapeutic targets")
                recommendations.append("Continue monitoring per protocol")
            
            # Special considerations
            if self.regimen == "SDD" or self.regimen == "extended_interval":
                recommendations.append("Ensure adequate interval to allow trough <1 mg/L before next dose")
            
            if crcl < 30:
                recommendations.append("🚨 Increased risk of toxicity - close monitoring required")
                recommendations.append("Consider alternative antimicrobial if possible")
        
        return recommendations
    
    def recommend_resampling_date(self, current_interval, status, crcl):
        """Recommend when to resample based on regimen, status and renal function"""
        # Default sampling recommendation
        if self.drug == "Vancomycin":
            if status == "therapeutic":
                # For stable patients on target
                if crcl >= 60:
                    days = 7  # Weekly for stable patients with good renal function
                elif crcl >= 30:
                    days = 5  # Twice weekly for moderate renal impairment
                else:
                    days = 3  # More frequent for severe renal impairment
            else:
                # For patients not on target, check sooner
                if crcl >= 60:
                    days = 3  # Sooner for out-of-range with good renal function
                elif crcl >= 30:
                    days = 2  # Very soon for moderate renal impairment
                else:
                    days = 1  # Next day for severe renal impairment
                    
            # For extended intervals, make sure we capture steady state
            if current_interval >= 24:
                # Ensure we have at least 3-4 half-lives before resampling
                doses_before_resampling = max(3, days * 24 // current_interval)
                days = (doses_before_resampling * current_interval) // 24
                
            # Calculate the actual date
            resample_date = datetime.now() + timedelta(days=days)
            
            # Format the string based on time frame
            if days <= 1:
                return f"Recommend resampling tomorrow ({resample_date.strftime('%a, %b %d')})"
            elif days <= 3:
                return f"Recommend resampling in {days} days ({resample_date.strftime('%a, %b %d')})"
            else:
                return f"Recommend resampling in {days} days ({resample_date.strftime('%a, %b %d')}) after reaching steady state"
        else:
            # For aminoglycosides - typically more frequent monitoring
            if status == "therapeutic":
                if crcl >= 60:
                    days = 3
                else:
                    days = 2
            else:
                days = 1
                
            resample_date = datetime.now() + timedelta(days=days)
            return f"Recommend resampling in {days} days ({resample_date.strftime('%a, %b %d')})"
            
    def format_recommendations(self, assessment, status, recommendations, patient_data):
        """
        Format assessment and recommendations into a comprehensive clinical interpretation
        
        Parameters:
        - assessment: List of assessment strings for each measured level
        - status: Overall status (therapeutic, subtherapeutic, high, toxic)
        - recommendations: List of clinical recommendations
        - patient_data: Dictionary with patient information
        
        Returns:
        - Formatted markdown string with clinical interpretation
        """
        # Store assessment and status for potential future use
        self.assessment = assessment
        self.status = status
        
        # Start building the formatted interpretation
        formatted_text = "#### Assessment\n"
        
        # Add appropriate status icon
        if status == "therapeutic":
            formatted_text += "✅ **THERAPEUTIC LEVELS**\n\n"
        elif status == "subtherapeutic":
            formatted_text += "❌ **SUBTHERAPEUTIC LEVELS**\n\n"
        elif status == "toxic":
            formatted_text += "⚠️ **POTENTIALLY TOXIC LEVELS**\n\n"
        else:  # high
            formatted_text += "⚠️ **LEVELS ABOVE TARGET RANGE**\n\n"
        
        # Add each assessment point with appropriate formatting
        for point in assessment:
            if "BELOW" in point:
                formatted_text += f"❌ {point}\n\n"
            elif "ABOVE" in point:
                formatted_text += f"⚠️ {point}\n\n"
            else:
                formatted_text += f"✅ {point}\n\n"
        
        # Add patient-specific context
        formatted_text += f"**Patient Context:** {patient_data.get('gender', 'Unknown gender')}, {patient_data.get('age', 'Unknown age')} years old, "
        formatted_text += f"weight {patient_data.get('weight', 'Unknown')} kg, CrCl {patient_data.get('crcl', 'Unknown'):.1f} mL/min"
        
        if patient_data.get('diagnosis'):
            formatted_text += f", diagnosis: {patient_data.get('diagnosis')}"
        formatted_text += "\n\n"
        
        # Add recommendations section
        formatted_text += "#### Recommendations\n"
        for i, rec in enumerate(recommendations):
            # Add appropriate icon based on content
            if "🚨" in rec:
                # Already has an icon
                formatted_text += f"{rec}\n\n"
            elif "monitor" in rec.lower() or "watch" in rec.lower():
                formatted_text += f"👁️ {rec}\n\n"
            elif "increase" in rec.lower() or "higher" in rec.lower() or "raise" in rec.lower():
                formatted_text += f"📈 {rec}\n\n"
            elif "decrease" in rec.lower() or "lower" in rec.lower() or "reduce" in rec.lower():
                formatted_text += f"📉 {rec}\n\n"
            elif "resample" in rec.lower() or "follow-up" in rec.lower() or "next" in rec.lower():
                formatted_text += f"📅 {rec}\n\n"
            else:
                formatted_text += f"• {rec}\n\n"
        
        # Add disclaimer - ensure this is on one clean line with proper string concatenation
        formatted_text += "---\n"
        formatted_text += "*This clinical interpretation is provided for decision support only. "
        formatted_text += "Always use professional judgment when making clinical decisions.*"
        
        return formatted_text

    def format_recommendations_for_regimen_change(self, old_regimen, old_levels, new_regimen, new_levels, patient_data):
        """
        Format recommendations for a regimen change with comparison between old and new regimens
        
        Parameters:
        - old_regimen: String describing the old regimen
        - old_levels: Dictionary of predicted levels with the old regimen
        - new_regimen: String describing the new regimen
        - new_levels: Dictionary of predicted levels with the new regimen
        - patient_data: Dictionary with patient information
        
        Returns:
        - Formatted markdown string with clinical interpretation
        """
        # Assess old and new regimens
        old_assessment, old_status = self.assess_levels(old_levels)
        new_assessment, new_status = self.assess_levels(new_levels)
        
        # Generate recommendations based on new regimen
        recommendations = self.generate_recommendations(new_status, patient_data['crcl'])
        
        # Start building the formatted interpretation
        formatted_text = "#### Comparison of Regimens\n"
        
        # Compare regimen status with appropriate icons
        formatted_text += f"**Current Regimen ({old_regimen}):** "
        if old_status == "therapeutic":
            formatted_text += "✅ **THERAPEUTIC**\n"
        elif old_status == "subtherapeutic":
            formatted_text += "❌ **SUBTHERAPEUTIC**\n"
        elif old_status == "toxic":
            formatted_text += "⚠️ **POTENTIALLY TOXIC**\n"
        else:  # high
            formatted_text += "⚠️ **ABOVE TARGET RANGE**\n"
        
        formatted_text += f"**Recommended Regimen ({new_regimen}):** "
        if new_status == "therapeutic":
            formatted_text += "✅ **THERAPEUTIC**\n\n"
        elif new_status == "subtherapeutic":
            formatted_text += "❌ **SUBTHERAPEUTIC**\n\n"
        elif new_status == "toxic":
            formatted_text += "⚠️ **POTENTIALLY TOXIC**\n\n"
        else:  # high
            formatted_text += "⚠️ **ABOVE TARGET RANGE**\n\n"
        
        # Detailed level comparisons
        formatted_text += "#### Detailed Comparison\n"
        
        # AUC comparison if available
        if 'auc' in old_levels and 'auc' in new_levels:
            auc_old = old_levels['auc']
            auc_new = new_levels['auc']
            auc_min = self.targets['auc']['min']
            auc_max = self.targets['auc']['max']
            
            formatted_text += f"**AUC₂₄:** {auc_old:.1f} → {auc_new:.1f} mg·hr/L "
            
            if auc_old < auc_min and auc_new >= auc_min and auc_new <= auc_max:
                formatted_text += "(❌ → ✅ Now within target range)\n"
            elif auc_old > auc_max and auc_new >= auc_min and auc_new <= auc_max:
                formatted_text += "(⚠️ → ✅ Now within target range)\n"
            elif auc_old >= auc_min and auc_old <= auc_max and (auc_new < auc_min or auc_new > auc_max):
                formatted_text += "(✅ → ❌/⚠️ Now outside target range)\n"
            elif auc_old < auc_min and auc_new < auc_min:
                if auc_new > auc_old:
                    formatted_text += "(❌ → ❌ Still below target but improved)\n"
                else:
                    formatted_text += "(❌ → ❌ Still below target)\n"
            elif auc_old > auc_max and auc_new > auc_max:
                if auc_new < auc_old:
                    formatted_text += "(⚠️ → ⚠️ Still above target but improved)\n"
                else:
                    formatted_text += "(⚠️ → ⚠️ Still above target)\n"
            else:
                if auc_new >= auc_min and auc_new <= auc_max:
                    formatted_text += "(✅ Still within target range)\n"
                else:
                    formatted_text += "\n"
        
        # Trough comparison
        trough_old = old_levels['trough']
        trough_new = new_levels['trough']
        trough_min = self.targets['trough']['min']
        trough_max = self.targets['trough']['max']
        
        formatted_text += f"**Trough:** {trough_old:.1f} → {trough_new:.1f} mg/L "
        
        if trough_old < trough_min and trough_new >= trough_min and trough_new <= trough_max:
            formatted_text += "(❌ → ✅ Now within target range)\n"
        elif trough_old > trough_max and trough_new >= trough_min and trough_new <= trough_max:
            formatted_text += "(⚠️ → ✅ Now within target range)\n"
        elif trough_old >= trough_min and trough_old <= trough_max and (trough_new < trough_min or trough_new > trough_max):
            formatted_text += "(✅ → ❌/⚠️ Now outside target range)\n"
        elif trough_old < trough_min and trough_new < trough_min:
            if trough_new > trough_old:
                formatted_text += "(❌ → ❌ Still below target but improved)\n"
            else:
                formatted_text += "(❌ → ❌ Still below target)\n"
        elif trough_old > trough_max and trough_new > trough_max:
            if trough_new < trough_old:
                formatted_text += "(⚠️ → ⚠️ Still above target but improved)\n"
            else:
                formatted_text += "(⚠️ → ⚠️ Still above target)\n"
        else:
            if trough_new >= trough_min and trough_new <= trough_max:
                formatted_text += "(✅ Still within target range)\n"
            else:
                formatted_text += "\n"
        
        # Peak comparison
        peak_old = old_levels['peak']
        peak_new = new_levels['peak']
        
        formatted_text += f"**Peak:** {peak_old:.1f} → {peak_new:.1f} mg/L\n\n"
        
        # Add patient-specific context
        formatted_text += f"**Patient Context:** {patient_data.get('gender', 'Unknown gender')}, {patient_data.get('age', 'Unknown age')} years old, "
        formatted_text += f"weight {patient_data.get('weight', 'Unknown')} kg, CrCl {patient_data.get('crcl', 'Unknown'):.1f} mL/min"
        
        if patient_data.get('diagnosis'):
            formatted_text += f", diagnosis: {patient_data.get('diagnosis')}"
        formatted_text += "\n\n"
        
        # Add recommendations section
        formatted_text += "#### Recommendations\n"
        for i, rec in enumerate(recommendations):
            # Add appropriate icon based on content
            if "🚨" in rec:
                # Already has an icon
                formatted_text += f"{rec}\n\n"
            elif "monitor" in rec.lower() or "watch" in rec.lower():
                formatted_text += f"👁️ {rec}\n\n"
            elif "increase" in rec.lower() or "higher" in rec.lower() or "raise" in rec.lower():
                formatted_text += f"📈 {rec}\n\n"
            elif "decrease" in rec.lower() or "lower" in rec.lower() or "reduce" in rec.lower():
                formatted_text += f"📉 {rec}\n\n"
            elif "resample" in rec.lower() or "follow-up" in rec.lower() or "next" in rec.lower():
                formatted_text += f"📅 {rec}\n\n"
            else:
                formatted_text += f"• {rec}\n\n"
        
        # Add disclaimer - ensure this is on one clean line with proper string concatenation
        formatted_text += "---\n"
        formatted_text += "*This clinical interpretation is provided for decision support only. "
        formatted_text += "Always use professional judgment when making clinical decisions.*"
        
        return formatted_text
