
antimicrobial-tdm-app/
├── app.py                     # Main Streamlit application
├── config.py                  # Drug configurations
├── ui_components.py           # UI components
├── pk_calculations.py         # PK calculations
├── clinical_logic.py          # Clinical interpretation
├── visualization.py           # Visualization functions
├── aminoglycoside_module.py   # Aminoglycoside module
├── vancomycin_module.py       # Vancomycin module
├── requirements.txt           # Dependencies
├── .streamlit/
│   └── secrets.toml          # API keys
└── README.md                 # Documentation


# Antimicrobial TDM Calculator

A Streamlit web application for therapeutic drug monitoring (TDM) of antimicrobial medications, focusing on aminoglycosides and vancomycin.

## Features

- **Aminoglycoside Initial Dose Calculator**: Calculate initial doses based on population pharmacokinetics
- **Aminoglycoside Dose Adjustment**: Adjust doses based on measured peak and trough levels (C1/C2)
- **Vancomycin AUC-based Dosing**: Calculate and adjust vancomycin doses using AUC methodology
- **Clinical Interpretation**: Automated clinical recommendations based on calculated parameters
- **Concentration-Time Curves**: Visual representation of drug concentrations over time
- **Patient-specific Adjustments**: Considers renal function, weight, and other patient factors

## Quick Start

### Local Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/antimicrobial-tdm-flat.git
   cd antimicrobial-tdm-flat
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create secrets file for OpenAI API (optional):
   ```bash
   mkdir .streamlit
   echo '[openai]\napi_key = "your-openai-api-key"' > .streamlit/secrets.toml
   ```

5. Run the application:
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

## Deployment to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Select `app.py` as the main file
5. Add secrets in the Streamlit Cloud dashboard:
   - Go to App Settings > Secrets
   - Add your OpenAI API key (optional)

## Project Structure (Flat Structure)

```
antimicrobial-tdm-flat/
├── app.py                     # Main Streamlit application
├── config.py                  # Drug configurations
├── pk_calculations.py         # Pharmacokinetic calculations
├── clinical_logic.py          # Clinical interpretation logic
├── visualization.py           # Concentration-time curve visualization
├── ui_components.py           # Reusable UI components
├── aminoglycoside_module.py   # Aminoglycoside-specific calculations
├── vancomycin_module.py       # Vancomycin-specific calculations
├── requirements.txt           # Python dependencies
├── .streamlit/
│   └── secrets.toml          # Local secrets (don't commit!)
├── .gitignore                # Git ignore file
└── README.md                 # This documentation
```

## Technologies Used

- **Streamlit**: Web application framework
- **Python 3.8+**: Core programming language
- **NumPy & Pandas**: Mathematical calculations and data handling
- **Altair**: Interactive visualizations
- **SciPy**: Advanced mathematical calculations
- **OpenAI API**: Clinical interpretation assistance (optional)

## Usage Guide

### 1. Patient Information
- Enter patient demographics in the sidebar
- System automatically calculates creatinine clearance
- Add clinical notes and current medication information

### 2. Module Selection
Choose from three main modules:
- **Aminoglycoside Initial Dose**: For new patients starting therapy
- **Aminoglycoside Dose Adjustment**: When you have measured levels
- **Vancomycin AUC-based Dosing**: For AUC/MIC-guided therapy

### 3. Drug Selection
- Select specific drug (Gentamicin, Amikacin, or Vancomycin)
- Choose dosing strategy (MDD, SDD, Synergy, etc.)
- Set target ranges based on indication

### 4. Results Interpretation
- View calculated PK parameters
- Check predicted levels against targets
- Review clinical recommendations
- Visualize concentration-time profile

## Clinical Algorithms

### Aminoglycoside Dosing
- Uses population pharmacokinetics
- Adjusts for renal function and weight
- Supports multiple dosing strategies (MDD, SDD, Synergy)
- Level-based adjustment using Sawchuk-Zaske method

### Vancomycin Dosing
- AUC-based dosing as per latest guidelines
- Linear-log trapezoidal method for AUC calculation
- Bayesian-like adjustment based on measured levels
- Supports empiric and definitive therapy targets

## Important Notes

- This tool is designed to assist healthcare professionals in therapeutic drug monitoring
- It should not replace clinical judgment
- Always verify calculations and recommendations before making clinical decisions
- Consider patient-specific factors not captured by the calculator

## Contributing

Issues and pull requests are welcome. Please ensure any contributions maintain the flat structure for easier deployment.

## Support

For support, please open an issue on GitHub or contact the maintainers.

## Disclaimer

This tool is provided for educational and clinical support purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment.

## License

MIT License - See LICENSE file for details

---

Developed with ❤️ for better patient care
