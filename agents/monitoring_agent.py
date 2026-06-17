from anthropic import Anthropic
from tools.pinecone_store import store_check_in, retrieve_patient_history
import json
from datetime import datetime

client = Anthropic()

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

    # Universal questions
    questions.append({
        "id": "medications",
        "question": f"Did you take all your medications today? ({', '.join(meds[:3])}{'...' if len(meds) > 3 else ''})",
        "type": "yes_no_detail"
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
            "question": f"Are you experiencing any of the following? (Select all that apply): {', '.join(warning_signs[:4])}",
            "type": "multi_select",
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
    print(f"[Monitoring Agent] Processing Day {state['recovery_day']} check-in...")

    # Retrieve recent history for trend analysis
    history = state.get("check_in_history", [])
    recent_history = history[-7:] if len(history) > 7 else history

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
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

        result = json.loads(response.content[0].text)

    except Exception as e:
        # Safe fallback — treat as YELLOW on classification error
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
        "flags": result["flags"],
        "summary": result["summary"]
    }

    # Store in Pinecone
    stored = store_check_in(state["patient_id"], check_in_record)
    if not stored:
        state["active_flags"].append("CHECKIN_STORAGE_FAILED")

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