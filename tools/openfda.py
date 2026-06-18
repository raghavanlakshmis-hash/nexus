import requests
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

OPENFDA_BASE = "https://api.fda.gov/drug"

def _check_one_medication(med: dict, med_names: List[str]) -> List[dict]:
    """Check a single medication against OpenFDA. Returns list of interaction detail dicts."""
    details = []
    try:
        response = requests.get(
            f"{OPENFDA_BASE}/label.json",
            params={
                "search": f'openfda.brand_name:"{med["name"]}" OR openfda.generic_name:"{med["name"]}"',
                "limit": 1
            },
            timeout=8
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                label = data["results"][0]

                interactions = label.get("drug_interactions", [])
                boxed_warning = label.get("boxed_warning", [])

                for other_med in med_names:
                    if other_med != med["name"].lower():
                        for interaction_text in interactions:
                            if other_med in interaction_text.lower():
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

    return details


def check_medication_interactions(medications: List[dict]) -> dict:
    """
    Check for known drug interactions using OpenFDA.
    All medications are checked in parallel to minimise latency.
    Returns flagged interactions for human review.
    """
    if not medications:
        return {"flagged_medications": [], "interaction_details": [], "all_clear": True}

    med_names = [m["name"].lower() for m in medications]
    all_details = []

    with ThreadPoolExecutor(max_workers=min(len(medications), 8)) as executor:
        futures = {executor.submit(_check_one_medication, med, med_names): med for med in medications}
        for future in as_completed(futures):
            all_details.extend(future.result())

    flags = list({d["drug_1"] for d in all_details if d["severity"] != "API_ERROR"})

    return {
        "flagged_medications": flags,
        "interaction_details": all_details,
        "all_clear": len(flags) == 0
    }
