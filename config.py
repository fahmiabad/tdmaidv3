# config.py

DRUG_CONFIGS = {
    "Gentamicin": {
        "pk_parameters": {
            "Vd_L_kg": 0.26,
            "cl_factor": 0.05,
            "rounding_base": 20
        },
        "regimens": {
            "MDD": {
                "display_name": "Traditional (Multiple Daily - MDD)",
                "default_interval": 8,
                "targets": {
                    "peak": {"min": 5, "max": 10, "info": "5-10 mg/L"},
                    "trough": {"min": 0, "max": 2, "info": "<2 mg/L"}
                }
            },
            "SDD": {
                "display_name": "Extended Interval (Once Daily - SDD)",
                "default_interval": 24,
                "targets": {
                    "peak": {"min": 15, "max": 30, "info": "15-30 mg/L (or 10x MIC)"},
                    "trough": {"min": 0, "max": 1, "info": "<1 mg/L (often undetectable)"}
                }
            },
            "Synergy": {
                "display_name": "Synergy (e.g., Endocarditis)",
                "default_interval": 12,
                "targets": {
                    "peak": {"min": 3, "max": 5, "info": "3-5 mg/L"},
                    "trough": {"min": 0, "max": 1, "info": "<1 mg/L"}
                }
            },
            "Hemodialysis": {
                "display_name": "Hemodialysis",
                "default_interval": 48,
                "targets": {
                    "peak": {"min": 0, "max": 0, "info": "Peak not routinely targeted"},
                    "trough": {"min": 0, "max": 2, "info": "<2 mg/L (pre-dialysis)"}
                }
            }
        }
    },
    "Amikacin": {
        "pk_parameters": {
            "Vd_L_kg": 0.3,
            "cl_factor": 0.06,
            "rounding_base": 50
        },
        "regimens": {
            "MDD": {
                "display_name": "Traditional (Multiple Daily - MDD)",
                "default_interval": 8,
                "targets": {
                    "peak": {"min": 20, "max": 30, "info": "20-30 mg/L"},
                    "trough": {"min": 0, "max": 10, "info": "<10 mg/L"}
                }
            },
            "SDD": {
                "display_name": "Extended Interval (Once Daily - SDD)",
                "default_interval": 24,
                "targets": {
                    "peak": {"min": 50, "max": 70, "info": "50-70 mg/L (or 10x MIC)"},
                    "trough": {"min": 0, "max": 5, "info": "<5 mg/L (often undetectable)"}
                }
            }
        }
    },
    "Vancomycin": {
        "pk_parameters": {
            "Vd_L_kg": 0.7,
            "cl_fraction": 0.8,
            "rounding_base": 250
        },
        "regimens": {
            "empiric": {
                "display_name": "Empiric Therapy",
                "default_interval": 12,
                "targets": {
                    "AUC": {"min": 400, "max": 600, "info": "400-600 mg·hr/L"},
                    "trough": {"min": 10, "max": 15, "info": "10-15 mg/L"},
                    "peak": {"min": 20, "max": 30, "info": "20-30 mg/L"}
                }
            },
            "definitive": {
                "display_name": "Definitive Therapy",
                "default_interval": 12,
                "targets": {
                    "AUC": {"min": 400, "max": 600, "info": "400-600 mg·hr/L"},
                    "trough": {"min": 15, "max": 20, "info": "15-20 mg/L"},
                    "peak": {"min": 25, "max": 40, "info": "25-40 mg/L"}
                }
            }
        }
    }
}
