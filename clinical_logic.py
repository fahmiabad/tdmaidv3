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
