
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

### Core Functionality
- **Aminoglycoside Initial Dose Calculator**: Calculate initial doses based on population pharmacokinetics
- **Aminoglycoside Dose Adjustment**: Adjust doses based on measured peak and trough levels (C1/C2)
- **Vancomycin AUC-based Dosing**: Calculate and adjust vancomycin doses using AUC methodology
- **Single Level Adjustments**: Adjust vancomycin doses based on a single trough or random level
- **Peak/Trough Adjustments**: Adjust vancomycin doses using both peak and trough levels
- **Clinical Interpretation**: Automated clinical recommendations based on calculated parameters
- **Concentration-Time Curves**: Visual representation of drug concentrations over time

### Enhanced Features
- **Patient-specific Adjustments**: Considers renal function, weight, and other patient factors
- **Clear Therapeutic Range Indicators**: Visual indicators for below/within/above target levels
- **Practical Dosing Intervals**: Supports intervals of 6, 8, 12, 24, 36, 48, and 72 hours
- **Single Best Regimen Recommendations**: Provides one optimal dosing recommendation
- **Detailed Clinical Reasoning**: Explains why a specific regimen was recommended
- **Input Validation**: Warns about clinically implausible or unusual values
- **Improved Error Handling**: Better error messages and fallbacks for edge cases

## Quick Start

### Local Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/antimicrobial-tdm-app.git
   cd antimicrobial-tdm-app
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

## User Guide

### 1. Patient Information
- Enter patient demographics in the sidebar
- System automatically calculates creatinine clearance
- Add clinical notes, diagnosis, and current medication information
- All inputs are validated to ensure clinically reasonable values

### 2. Module Selection
Choose from three main modules:
- **Aminoglycoside Initial Dose**: For new patients starting therapy
- **Aminoglycoside Dose Adjustment**: When you have measured levels
- **Vancomycin AUC-based Dosing**: For AUC/MIC-guided therapy

### 3. Vancomycin Dosing Methods
Choose from three approaches:
- **Calculate Initial Dose**: For new patients with no levels
- **Adjust Using Single Level**: Using a trough or random level
- **Adjust Using Peak & Trough**: When both peak and trough are available

#### 3.1 Single Level Adjustment
- Enter current dose and interval
- Specify whether the level is a trough or random level
- Enter the timing of dose administration and sample collection
- The system calculates individualized PK parameters
- A single optimal regimen is recommended based on:
  - Target AUC/MIC achievement
  - Trough within target range
  - Appropriateness for renal function
  - Practical dosing considerations

#### 3.2 Peak/Trough Adjustment
- Enter current dose, interval, and infusion duration
- Enter peak and trough levels with timing information
- The system calculates individualized PK parameters
- A single optimal regimen is recommended with clinical reasoning

### 4. Results Interpretation
- View calculated PK parameters (ke, t½, Vd, CL)
- Check predicted levels against targets with clear visual indicators
- Review the detailed clinical reasoning behind recommendations
- Visualize concentration-time profile
- Download a comprehensive report for documentation

### 5. Clinical Recommendations
- Recommendations include specific actions needed
- Visual indicators clearly show if levels are below/within/above range
- System suggests appropriate timing for repeat level measurements
- Special warnings for patients with impaired renal function

## Technical Details

### Vancomycin AUC Calculation
- Uses linear-log trapezoidal method for AUC calculation
- Supports single-level Bayesian-like estimation
- Handles random levels drawn at any point in the dosing interval
- Provides robust error handling for edge cases

### Optimal Regimen Selection
- Scores potential regimens based on multiple factors:
  - AUC target achievement (weighted heavily)
  - Trough within target range
  - Appropriateness for renal function
  - Practical dosing considerations
- Presents a single clear recommendation with explanation
- Provides detailed clinical reasoning for the selected regimen

### Clinical Assessment
- Clearly labels levels as below/within/above therapeutic range
- Uses color-coded icons for visual clarity
- Provides specific, actionable recommendations
- Suggests timing for follow-up monitoring based on clinical status

## Important Notes

- This tool is designed to assist healthcare professionals in therapeutic drug monitoring
- It should not replace clinical judgment
- Always verify calculations and recommendations before making clinical decisions
- Consider patient-specific factors not captured by the calculator

## Contributing

Issues and pull requests are welcome. Please ensure any contributions maintain the structure for easier deployment.

## Support

For support, please open an issue on GitHub or contact the maintainers.

## Disclaimer

This tool is provided for educational and clinical support purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment.

## License

MIT License - See LICENSE file for details

---

Developed with ❤️ for better patient care
