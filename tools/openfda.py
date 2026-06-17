import requests
from typing import List

OPENFDA_BASE = "https://api.fda.gov/drug"

def check_medication_interactions(medications: List[dict]) -> dict:
    """
    Check for known drug interactions using OpenFDA.
    Returns flagged interactions for human review.
    """
    flags = []
    details = []

    med_names = [m["name"].lower() for m in medications]

    for med in medications:
        try:
            response = requests.get(
                f"{OPENFDA_BASE}/label.json",
                params={
                    "search": f'openfda.brand_name:"{med["name"]}" OR openfda.generic_name:"{med["name"]}"',
                    "limit": 1
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    label = data["results"][0]

                    # Check drug interactions section
                    interactions = label.get("drug_interactions", [])
                    warnings = label.get("warnings", [])
                    boxed_warning = label.get("boxed_warning", [])

                    for other_med in med_names:
                        if other_med != med["name"].lower():
                            for interaction_text in interactions:
                                if other_med in interaction_text.lower():
                                    flags.append(med["name"])
                                    details.append({
                                        "drug_1": med["name"],
                                        "drug_2": other_med,
                                        "interaction_text": interaction_text[:500],
                                        "severity": "REVIEW_REQUIRED"
                                    })

                    if boxed_warning:
                        details.append({
                            "drug_1": med["name"],
                            "drug_2": None,
                            "interaction_text": str(boxed_warning[0])[:500],
                            "severity": "BOXED_WARNING"
                        })

        except requests.Timeout:
            details.append({
                "drug_1": med["name"],
                "drug_2": None,
                "interaction_text": "OpenFDA API timeout — flag for pharmacist review",
                "severity": "API_ERROR"
            })
        except Exception as e:
            details.append({
                "drug_1": med["name"],
                "drug_2": None,
                "interaction_text": f"Check failed: {str(e)}",
                "severity": "API_ERROR"
            })

    return {
        "flagged_medications": list(set(flags)),
        "interaction_details": details,
        "all_clear": len(flags) == 0
    }