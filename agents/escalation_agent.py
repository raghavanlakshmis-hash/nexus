from anthropic import Anthropic
from tools.notification_tool import send_email_notification, send_sms_notification
import json
import uuid
from datetime import datetime

client = Anthropic()

def determine_escalation_tier(flags: list, responses: dict, state: dict) -> str:
    """
    TIER_1: Urgent but not life-threatening — draft message for human approval
    TIER_2: Potentially life-threatening — auto-notify emergency contact (with consent)
    TIER_3: Actively life-threatening — display 911 immediately
    """
    flag_text = " ".join(flags).lower()
    responses_text = json.dumps(responses).lower()

    tier_3_keywords = ["can't breathe", "cannot breathe", "chest pain", "unconscious",
                       "not breathing", "stroke", "seizure", "911"]
    tier_2_keywords = ["difficulty breathing", "severe pain", "confusion", "disoriented",
                       "won't wake", "unresponsive", "er warning"]

    for keyword in tier_3_keywords:
        if keyword in flag_text or keyword in responses_text:
            return "TIER_3"

    for keyword in tier_2_keywords:
        if keyword in flag_text or keyword in responses_text:
            return "TIER_2"

    return "TIER_1"

def run_escalation_agent(state: dict) -> dict:
    """
    Escalation Agent: Handle RED flags. Tier-based response.
    """
    print("[Escalation Agent] RED flag detected. Determining tier...")

    recent_checkin = state["check_in_history"][-1] if state["check_in_history"] else {}
    flags = state.get("active_flags", [])
    responses = recent_checkin.get("responses", {})

    tier = determine_escalation_tier(flags, responses, state)
    print(f"[Escalation Agent] Tier: {tier}")

    state["escalation_tier"] = tier
    state["escalation_timestamp"] = datetime.now().isoformat()

    if tier == "TIER_3":
        # Immediate 911 display — no agent actions, just surface to UI
        state["show_911_screen"] = True
        state["911_message"] = "CALL 911 NOW. Do not wait."

        # Auto-notify emergency contact if consented
        if state.get("emergency_contact_consented") and state.get("emergency_contact_phone"):
            send_sms_notification(
                to_phone=state["emergency_contact_phone"],
                message=f"URGENT: {state['patient_name']} may need emergency help. "
                        f"Please check on them immediately or call 911."
            )
        state["current_agent"] = "complete"

    elif tier == "TIER_2":
        # Auto-notify emergency contact (with consent) + draft ER handoff summary
        if state.get("emergency_contact_consented") and state.get("emergency_contact_phone"):
            send_sms_notification(
                to_phone=state["emergency_contact_phone"],
                message=f"URGENT: {state['patient_name']} has reported concerning symptoms "
                        f"(Day {state['recovery_day']} of recovery from {state['diagnosis']}). "
                        f"Please check on them."
            )

        # Draft ER handoff summary patient can show on arrival
        er_summary = generate_er_summary(state)
        state["er_handoff_summary"] = er_summary
        state["show_er_guidance"] = True
        state["current_agent"] = "admin_agent"

    elif tier == "TIER_1":
        # Draft provider message for human approval
        draft = generate_provider_message_draft(state, recent_checkin)

        approval_item = {
            "id": str(uuid.uuid4()),
            "type": "escalation_message",
            "content": draft,
            "recipient": "primary_care_physician",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        state["human_approval_queue"].append(approval_item)
        state["show_yellow_guidance"] = True
        state["current_agent"] = "admin_agent"

    return state

def generate_er_summary(state: dict) -> str:
    """Generate a plain-language ER handoff summary."""
    meds = [f"{m['name']} {m['dose']} {m['frequency']}"
            for m in state.get("medications", [])
            if not m.get("interaction_flag")]

    return f"""PATIENT INFORMATION FOR ER STAFF
Name: {state.get('patient_name', 'Unknown')}
Recent discharge: {state.get('discharge_date', 'Unknown')}
Diagnosis: {state.get('diagnosis', 'Unknown')}

Current medications:
{chr(10).join(f'- {m}' for m in meds)}

Allergies: Please ask patient

Recovery day: {state.get('recovery_day', 'Unknown')}
Flagged symptoms today: {', '.join(state.get('active_flags', [])[:3])}"""

def generate_provider_message_draft(state: dict, recent_checkin: dict) -> str:
    """Draft a provider message for human approval."""
    return f"""Draft message to your care team (please review before sending):

Subject: Recovery update — Day {state.get('recovery_day')} concern

I was discharged on {state.get('discharge_date')} following treatment for {state.get('diagnosis')}.
During my Day {state.get('recovery_day')} check-in, I noticed the following:

{recent_checkin.get('summary', 'See flags below')}

Specific concerns: {', '.join(recent_checkin.get('flags', []))}

Could you please advise on next steps?

[REVIEW AND APPROVE BEFORE SENDING]"""