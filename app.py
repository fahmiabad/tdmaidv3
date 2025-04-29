# app.py
import streamlit as st
from ui_components import UIComponents
from aminoglycoside_module import AminoglycosideModule
from vancomycin_module import VancomycinModule
from validation_utils import ValidationUtils

# Set page configuration
st.set_page_config(
    page_title="Antimicrobial TDM Calculator",
    page_icon="💊",
    layout="wide"
)

# Add custom CSS for improved styling
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    h1, h2, h3 {
        margin-top: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .stAlert {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
    /* Improve warning and error styling */
    .stAlert.st-ae.st-af {
        border-left-width: 4px !important;
    }
    /* Custom icon colors */
    .green-icon {
        color: #28a745;
    }
    .red-icon {
        color: #dc3545;
    }
    .yellow-icon {
        color: #ffc107;
    }
    /* Chart container */
    .chart-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application entry point"""
    # Create sidebar and get patient data
    page, patient_data = UIComponents.create_patient_sidebar()
    
    # Display application header
    st.title("Antimicrobial TDM Calculator")
    st.markdown("A clinical decision support tool for therapeutic drug monitoring of antimicrobials")
    
    # Display patient snapshot if patient data is available
    if patient_data['patient_id'] != "N/A" or patient_data['diagnosis']:
        st.info(f"**Patient**: {patient_data['patient_id']} | **Diagnosis**: {patient_data.get('diagnosis', 'N/A')} | " +
                f"**Weight**: {patient_data['weight']} kg | **CrCl**: {patient_data['crcl']:.1f} mL/min | " +
                f"**Renal Function**: {patient_data['renal_function']}")
    
    st.markdown("---")
    
    # Route to appropriate module
    if page == "Aminoglycoside: Initial Dose":
        AminoglycosideModule.initial_dose(patient_data)
    elif page == "Aminoglycoside: Conventional Dosing (C1/C2)":
        AminoglycosideModule.conventional_dosing(patient_data)
    elif page == "Vancomycin AUC-based Dosing":
        VancomycinModule.auc_dosing(patient_data)
    
    # Display footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p><small>This tool is provided for educational and clinical support purposes only.<br>
        It is not a substitute for professional medical judgment.</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
