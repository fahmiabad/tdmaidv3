# visualization.py
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
import math

class PKVisualizer:
    @staticmethod
    def plot_concentration_curve(peak, trough, ke, tau, infusion_time=1.0):
        """
        Generate a concentration-time curve visualization.
        
        Parameters:
        - peak: Peak concentration (mg/L)
        - trough: Trough concentration (mg/L)
        - ke: Elimination rate constant (hr^-1)
        - tau: Dosing interval (hr)
        - infusion_time: Duration of infusion (hr)
        
        Returns:
        - Altair chart object
        """
        # Generate time points for 1.5 dosing intervals
        times = np.linspace(0, tau * 1.5, 150)
        concentrations = []
        
        # Calculate concentrations for each time point
        for t_cycle in times:
            t = t_cycle % tau  # Time within current dosing cycle
            
            if t <= infusion_time:
                # During infusion: linear increase
                conc = trough + (peak - trough) * (t / infusion_time)
            else:
                # Post-infusion: exponential decay
                time_since_peak = t - infusion_time
                conc = peak * math.exp(-ke * time_since_peak)
            
            concentrations.append(max(0, conc))
        
        # Create DataFrame for plotting
        df = pd.DataFrame({
            'Time (hr)': times,
            'Concentration (mg/L)': concentrations
        })
        
        # Create target bands based on drug levels
        target_bands = PKVisualizer._create_target_bands(peak, trough)
        
        # Create concentration line
        line = alt.Chart(df).mark_line(color='firebrick').encode(
            x=alt.X('Time (hr)', title='Time (hours)'),
            y=alt.Y('Concentration (mg/L)', 
                   title='Drug Concentration (mg/L)', 
                   scale=alt.Scale(zero=True)),
            tooltip=['Time (hr)', alt.Tooltip('Concentration (mg/L)', format=".1f")]
        )
        
        # Add vertical lines for key events
        vertical_lines = PKVisualizer._create_vertical_lines(tau, infusion_time)
        
        # Combine all elements
        chart = alt.layer(*target_bands, line, vertical_lines).properties(
            width=alt.Step(4),
            height=400,
            title=f'Concentration-Time Profile (Tau={tau} hr)'
        ).interactive()
        
        return chart
    
    @staticmethod
    def _create_target_bands(peak, trough):
        """Create target range visualization bands."""
        target_bands = []
        
        # Determine drug type based on typical levels
        if peak > 45 or trough > 20:  # Likely vancomycin
            if trough <= 15:  # Empiric therapy
                target_bands.append(
                    alt.Chart(pd.DataFrame({'y1': [20], 'y2': [30]}))
                    .mark_rect(opacity=0.15, color='lightblue')
                    .encode(y='y1', y2='y2', 
                           tooltip=alt.value("Target Peak Range (Vanco Empiric)"))
                )
                target_bands.append(
                    alt.Chart(pd.DataFrame({'y1': [10], 'y2': [15]}))
                    .mark_rect(opacity=0.15, color='lightgreen')
                    .encode(y='y1', y2='y2', 
                           tooltip=alt.value("Target Trough Range (Vanco Empiric)"))
                )
            else:  # Definitive therapy
                target_bands.append(
                    alt.Chart(pd.DataFrame({'y1': [25], 'y2': [40]}))
                    .mark_rect(opacity=0.15, color='lightblue')
                    .encode(y='y1', y2='y2', 
                           tooltip=alt.value("Target Peak Range (Vanco Definitive)"))
                )
                target_bands.append(
                    alt.Chart(pd.DataFrame({'y1': [15], 'y2': [20]}))
                    .mark_rect(opacity=0.15, color='lightgreen')
                    .encode(y='y1', y2='y2', 
                           tooltip=alt.value("Target Trough Range (Vanco Definitive)"))
                )
        else:  # Likely aminoglycoside
            target_bands.append(
                alt.Chart(pd.DataFrame({'y1': [5], 'y2': [10]}))
                .mark_rect(opacity=0.15, color='lightblue')
                .encode(y='y1', y2='y2', 
                       tooltip=alt.value("Target Peak Range (Amino)"))
            )
            target_bands.append(
                alt.Chart(pd.DataFrame({'y1': [0], 'y2': [2]}))
                .mark_rect(opacity=0.15, color='lightgreen')
                .encode(y='y1', y2='y2', 
                       tooltip=alt.value("Target Trough Range (Amino)"))
            )
        
        return target_bands
    
    @staticmethod
    def _create_vertical_lines(tau, infusion_time):
        """Create vertical lines for key events."""
        vertical_lines_data = []
        
        # Mark end of infusion for each cycle
        for i in range(int(tau * 1.5 / tau) + 1):
            inf_end_time = i * tau + infusion_time
            if inf_end_time <= tau * 1.5:
                vertical_lines_data.append({
                    'Time': inf_end_time, 
                    'Event': 'Infusion End'
                })
        
        # Mark start of next dose for each cycle
        for i in range(1, int(tau * 1.5 / tau) + 1):
            dose_time = i * tau
            if dose_time <= tau * 1.5:
                vertical_lines_data.append({
                    'Time': dose_time, 
                    'Event': 'Next Dose'
                })
        
        if not vertical_lines_data:
            return alt.Chart()
        
        vertical_lines_df = pd.DataFrame(vertical_lines_data)
        
        return alt.Chart(vertical_lines_df).mark_rule(strokeDash=[4, 4]).encode(
            x='Time',
            color=alt.Color('Event', 
                           scale=alt.Scale(
                               domain=['Infusion End', 'Next Dose'],
                               range=['gray', 'black']
                           )),
            tooltip=['Event', 'Time']
        )
    
    @staticmethod
    def display_pk_chart(pk_params, levels, dose_info, key_suffix=""):
        """
        Display a concentration-time chart with proper error handling.
        
        Parameters:
        - pk_params: Dictionary with PK parameters (ke, t_half, etc.)
        - levels: Dictionary with peak and trough values
        - dose_info: Dictionary with tau and infusion_duration
        - key_suffix: Optional suffix to make checkbox key unique
        """
        # Generate a unique key for the checkbox
        checkbox_key = f"show_conc_time_curve_{key_suffix}"
        
        if st.checkbox("Show Concentration-Time Curve", key=checkbox_key):
            peak = levels.get('peak', 0)
            trough = levels.get('trough', 0)
            ke = pk_params.get('ke', 0)
            tau = dose_info.get('tau', 24)
            infusion_time = dose_info.get('infusion_duration', 1)
            
            if peak > 0 and trough >= 0 and ke > 0 and tau > 0:
                try:
                    chart = PKVisualizer.plot_concentration_curve(
                        peak, trough, ke, tau, infusion_time
                    )
                    st.altair_chart(chart, use_container_width=True)
                except Exception as e:
                    st.warning(f"Unable to display curve: {e}")
            else:
                st.warning("Cannot display curve due to invalid parameters")
