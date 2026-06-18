from anthropic import Anthropic
from tools.pinecone_store import store_check_in, retrieve_patient_history
from dotenv import load_dotenv
import json
import re
from datetime import datetime

load_dotenv(override=True)

MONITORING_SYSTEM_PROMPT = """You are a recovery monitoring specialist.
You will receive a patient's daily check-in responses and their recovery context.
Your job is to classify the check-in and identify any flags.

Classification rules:
RED — Any of the following: patient reports an ER warning sign, weight gain >2lbs since 
      yesterday, chest pain, difficulty breathing at rest, confusion, disorientation.
      → ALWAYS classify RED if any ER warning sign is present, even mild.

YELLOW — Any of the following: mild symptom present (not on ER list), missed >1 medication,
          declining trend vs prior days, patient confused about care plan, weight up 1-2lbs.

GREEN — No flags, all medications taken, no concerning symptoms.

Also check for: declining trends across multiple check-ins (even if today is YELLOW).
If 3+ consecutive check-ins are YELLOW, elevate to RED.

Return ONLY valid JSON:
{
  "classification": "GREEN" | "YELLOW" | "RED",
  "flags": ["list of specific concerns"],
  "summary": "one sentence plain-language summary",
  "recommended_action": "what the patient should do next",
  "escalation_reason": "only if RED — specific reason"
}"""

def generate_checkin_questions(state: dict) -> list:
    """Generate personalized check-in questions based on diagnosis and day."""
    diagnosis = state.get("diagnosis", "general").lower()
    day = state.get("recovery_day", 1)
    meds = [m["name"] for m in state.get("medications", []) if not m.get("interaction_flag")]
    warning_signs = state.get("warning_signs_er", [])

    questions = []

    # Individual medication questions
    for med in meds:
        questions.append({
            "id": f"med_{med.replace(' ', '_').lower()}",
            "question": f"Did you take {med} today?",
            "type": "med_checkbox",
            "med_name": med
        })

    questions.append({
        "id": "general_feeling",
        "question": "How are you feeling overall today? (1 = terrible, 10 = great)",
        "type": "scale_1_10"
    })

    # Diagnosis-specific questions
    if "heart" in diagnosis or "chf" in diagnosis or "cardiac" in diagnosis:
        questions.append({
            "id": "weight",
            "question": "What was your weight this morning? (Daily weight is important for heart patients)",
            "type": "number_lbs"
        })
        questions.append({
            "id": "swelling",
            "question": "Any swelling in your ankles, feet, or legs compared to yesterday?",
            "type": "yes_no_detail"
        })
        questions.append({
            "id": "breathing",
            "question": "Any shortness of breath while resting or lying flat?",
            "type": "yes_no_detail"
        })

    # Warning sign check (always ask about ER signs)
    if warning_signs:
        questions.append({
            "id": "warning_signs",
            "question": "Are you experiencing any of these symptoms right now?",
            "type": "symptom_checklist",
            "options": warning_signs
        })

    questions.append({
        "id": "concerns",
        "question": "Anything else worrying you today that you'd like to flag?",
        "type": "free_text"
    })

    return questions

def run_monitoring_agent(state: dict, check_in_responses: dict) -> dict:
    """
    Monitoring Agent: Classify daily check-in, update history, return updated state.
    """
    client = Anthropic()
    print(f"[Monitoring Agent] Processing Day {state['recovery_day']} check-in...")

    # Retrieve recent history for trend analysis
    history = state.get("check_in_history", [])
    recent_history = history[-7:] if len(history) > 7 else history

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=MONITORING_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": json.dumps({
                    "day": state["recovery_day"],
                    "diagnosis": state["diagnosis"],
                    "er_warning_signs": state.get("warning_signs_er", []),
                    "call_warning_signs": state.get("warning_signs_call", []),
                    "todays_responses": check_in_responses,
                    "recent_check_in_history": recent_history
                }, indent=2)
            }]
        )

        result_text = response.content[0].text.strip()
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if not json_match:
            raise ValueError(f"No JSON object in model response: {result_text[:200]}")
        result = json.loads(json_match.group())

    except Exception as e:
        print(f"[Monitoring Agent] Classification error: {type(e).__name__}: {e}")
        result = {
            "classification": "YELLOW",
            "flags": [f"Classification system error: {str(e)}"],
            "summary": "Unable to classify check-in. Flagging for review.",
            "recommended_action": "Please call your doctor's office if you have any concerns.",
            "escalation_reason": None
        }

    # Build check-in record
    check_in_record = {
        "day": state["recovery_day"],
        "timestamp": datetime.now().isoformat(),
        "responses": check_in_responses,
        "classification": result["classification"],
        "flags": result.get("flags", []),
        "summary": result.get("summary", ""),
        "recommended_action": result.get("recommended_action", "")
    }

    # Store in Pinecone
    stored = store_check_in(state["patient_id"], check_in_record)
    if not stored:
        state["active_flags"].append("CHECKIN_STORAGE_FAILED")

    # Extract vitals and medication adherence from this check-in
    meds_taken = []
    meds_missed = []
    for med in state.get("medications", []):
        if med.get("interaction_flag"):
            continue
        key = f"med_{med['name'].replace(' ', '_').lower()}"
        val = check_in_responses.get(key)
        if val is not None:
            took_it = (val is True) or (isinstance(val, str) and "yes" in val.lower())
            (meds_taken if took_it else meds_missed).append(med["name"])

    vitals_record = {
        "day": state["recovery_day"],
        "date": datetime.now().date().isoformat(),
        "weight_lbs": check_in_responses.get("weight"),
        "bp_systolic": None,
        "bp_diastolic": None,
        "energy_score": check_in_responses.get("general_feeling"),
        "meds_taken": meds_taken,
        "meds_missed": meds_missed,
    }

    if "daily_vitals_log" not in state:
        state["daily_vitals_log"] = []
    # Replace any existing entry for this day, then append the fresh one
    state["daily_vitals_log"] = [
        v for v in state["daily_vitals_log"] if v["day"] != state["recovery_day"]
    ]
    state["daily_vitals_log"].append(vitals_record)

    # Update state
    state["check_in_history"].append(check_in_record)
    state["last_check_in_date"] = datetime.now().isoformat()

    # Route based on classification
    if result["classification"] == "RED":
        state["current_agent"] = "escalation_agent"
        state["active_flags"].append(f"RED_FLAG_DAY_{state['recovery_day']}: {result.get('escalation_reason', '')}")
    elif result["classification"] == "YELLOW":
        state["current_agent"] = "admin_agent"
        state["active_flags"].append(f"YELLOW_FLAG_DAY_{state['recovery_day']}")
    else:
        state["current_agent"] = "admin_agent"

    state["last_monitoring_result"] = result
    print(f"[Monitoring Agent] Classification: {result['classification']}")
    return state