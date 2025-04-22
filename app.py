# app.py
import streamlit as st
from ui_components import UIComponents
from aminoglycoside_module import AminoglycosideModule
from vancomycin_module import VancomycinModule

st.set_page_config(
    page_title="Antimicrobial TDM App",
    page_icon="💊",
    layout="wide"
)

def main():
    # Create sidebar and get patient data
    page, patient_data = UIComponents.create_patient_sidebar()
    
    # Display header
    st.title("Antimicrobial TDM Calculator")
    st.markdown("---")
    
    # Route to appropriate module
    if page == "Aminoglycoside: Initial Dose":
        AminoglycosideModule.initial_dose(patient_data)
    elif page == "Aminoglycoside: Conventional Dosing (C1/C2)":
        AminoglycosideModule.conventional_dosing(patient_data)
    elif page == "Vancomycin AUC-based Dosing":
        VancomycinModule.auc_dosing(patient_data)

if __name__ == "__main__":
    main()
