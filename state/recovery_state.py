from typing import TypedDict, List, Optional, Literal
from datetime import datetime

class Medication(TypedDict):
    name: str
    dose: str
    frequency: str
    duration: str
    food_interactions: Optional[str]
    interaction_flag: bool  # True = flagged by OpenFDA, needs human review

class Appointment(TypedDict):
    provider: str
    specialty: str
    timeframe_required: str
    scheduled_date: Optional[str]
    confirmed: bool

class CheckIn(TypedDict):
    day: int
    timestamp: str
    responses: dict
    classification: Literal["GREEN", "YELLOW", "RED"]
    flags: List[str]

class HumanApprovalItem(TypedDict):
    id: str
    type: Literal["medication_conflict", "provider_message", "escalation_message"]
    content: str
    recipient: Optional[str]
    status: Literal["pending", "approved", "rejected", "edited"]
    created_at: str

class HospitalizationRecord(TypedDict):
    id: str
    admit_date: str
    discharge_date: str
    hospital_name: str
    diagnosis: str
    icd10_code: Optional[str]
    treating_physician: Optional[str]
    specialty: Optional[str]
    notes: Optional[str]
    source: Literal["auto_imported", "manual_entry"]
    created_at: str

class DailyVitals(TypedDict):
    day: int
    date: str
    weight_lbs: Optional[float]
    bp_systolic: Optional[int]
    bp_diastolic: Optional[int]
    energy_score: Optional[int]
    meds_taken: list
    meds_missed: list

class RecoveryState(TypedDict):
    # Identity
    patient_id: str
    patient_name: str
    caregiver_name: Optional[str]
    caregiver_email: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    emergency_contact_consented: bool  # Must be True before auto-notify

    # Clinical
    discharge_date: str
    recovery_day: int
    diagnosis: str
    icd10_code: Optional[str]
    medications: List[Medication]
    appointments: List[Appointment]
    warning_signs_er: List[str]      # Go to ER immediately
    warning_signs_call: List[str]    # Call doctor within 24hrs
    dietary_restrictions: List[str]
    activity_restrictions: List[str]

    # Agent state
    current_agent: str
    needs_clarification: List[str]   # Fields Intake Agent couldn't extract
    active_flags: List[str]
    human_approval_queue: List[HumanApprovalItem]

    # History
    check_in_history: List[CheckIn]
    daily_vitals_log: List[DailyVitals]          # structured vitals per day for dashboard + provider summary
    hospitalization_history: List[HospitalizationRecord]  # auto + manual hospital stays
    messages: List[dict]             # LangGraph message history

    # Meta
    intake_complete: bool
    care_plan_complete: bool
    last_check_in_date: Optional[str]
    pinecone_namespace: str