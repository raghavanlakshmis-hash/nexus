import streamlit as st
import sys
import os
import json
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from agents.orchestrator import intake_graph, monitoring_graph, build_monitoring_graph
from agents.monitoring_agent import generate_checkin_questions

st.set_page_config(
    page_title="Nexus",
    page_icon="💜",
    layout="wide"
)

# ── Purple theme CSS override for Streamlit elements ──────────────────────────
# The .streamlit/config.toml handles global theming.
# This block adds fine-grained overrides for elements config.toml can't reach.
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #F4F3FE; }
[data-testid="stSidebar"] hr { border-color: #CECBF6; }
.stButton > button { border-color: #534AB7; color: #534AB7; }
.stButton > button:hover { background-color: #EEEDFE; }
.stMetric label { color: #7F77DD; font-size: 12px; }
.stMetric [data-testid="stMetricValue"] { color: #3C3489; }
div[data-testid="stAlert"][data-baseweb="notification"] { border-left-color: #534AB7; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "recovery_state" not in st.session_state:
    st.session_state.recovery_state = None
if "page" not in st.session_state:
    st.session_state.page = "onboarding"
if "show_typed_form" not in st.session_state:
    st.session_state.show_typed_form = False

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💜 Nexus")
    if st.session_state.recovery_state:
        state = st.session_state.recovery_state
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Day", f"{state.get('recovery_day', 0)} of 30")
        with col2:
            checkin_history = state.get("check_in_history", [])
            if checkin_history:
                last = checkin_history[-1]
                icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(
                    last["classification"], "⚪"
                )
                st.metric("Last check-in", f"{icon} {last['classification']}")

        pending = [i for i in state.get("human_approval_queue", [])
                   if i["status"] == "pending"]
        if pending:
            st.warning(f"⚠️ {len(pending)} item(s) need your review")

        st.caption(state.get("diagnosis", "")[:30])

    st.divider()
    if st.button("📋 Care plan", use_container_width=True):
        st.session_state.page = "care_plan"
    if st.button("🎤 Daily check-in", use_container_width=True):
        st.session_state.page = "checkin"
    if st.button("📬 Approvals", use_container_width=True):
        st.session_state.page = "approvals"
    if st.button("📊 Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
    if st.button("📄 Provider summary", use_container_width=True):
        st.session_state.page = "provider_summary"
    if st.button("🏥 Hospital history", use_container_width=True):
        st.session_state.page = "hospital_history"

# ─── PAGE: ONBOARDING ────────────────────────────────────────────────────────
if st.session_state.page == "onboarding" and not st.session_state.recovery_state:
    st.title("Welcome to Nexus")
    st.write("Let's get you set up. This takes about 3 minutes.")

    with st.form("onboarding_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Patient name *")
            discharge_date = st.date_input("Discharge date *")
        with col2:
            caregiver_name = st.text_input("Caregiver name (optional)")
            caregiver_email = st.text_input("Caregiver email (optional)")

        st.subheader("Emergency Contact")
        ec_name = st.text_input("Emergency contact name")
        ec_phone = st.text_input("Emergency contact phone")
        ec_consent = st.checkbox(
            "I consent to automatic emergency contact notification if a life-threatening "
            "symptom is detected during a check-in"
        )

        uploaded_file = st.file_uploader(
            "Upload your discharge summary PDF *",
            type=["pdf"]
        )

        submitted = st.form_submit_button("Start My Recovery Plan →")

    if submitted:
        if not patient_name or not uploaded_file:
            st.error("Please provide your name and discharge summary PDF.")
        else:
            # Save PDF temporarily
            patient_id = str(uuid.uuid4())[:8]
            pdf_path = f"data/{patient_id}_discharge.pdf"
            os.makedirs("data", exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Initialize state
            initial_state = {
                "patient_id": patient_id,
                "patient_name": patient_name,
                "caregiver_name": caregiver_name,
                "caregiver_email": caregiver_email,
                "emergency_contact_name": ec_name,
                "emergency_contact_phone": ec_phone,
                "emergency_contact_consented": ec_consent,
                "discharge_date": str(discharge_date),
                "recovery_day": 0,
                "diagnosis": "",
                "icd10_code": None,
                "medications": [],
                "appointments": [],
                "warning_signs_er": [],
                "warning_signs_call": [],
                "dietary_restrictions": [],
                "activity_restrictions": [],
                "current_agent": "intake_agent",
                "needs_clarification": [],
                "active_flags": [],
                "human_approval_queue": [],
                "check_in_history": [],
                "messages": [],
                "intake_complete": False,
                "care_plan_complete": False,
                "last_check_in_date": None,
                "pinecone_namespace": f"patient_{patient_id}",
                "pdf_path": pdf_path
            }

            with st.spinner("Reading your discharge summary... (this takes ~30 seconds)"):
                result_state = intake_graph.invoke(initial_state)

            st.session_state.recovery_state = result_state

            if result_state.get("intake_complete"):
                st.success(f"✅ Recovery plan created for {patient_name}!")
                st.session_state.page = "care_plan"
                st.rerun()
            else:
                st.error("We had trouble reading your PDF. Please try uploading again.")
                for flag in result_state.get("active_flags", []):
                    st.warning(flag)

# ─── PAGE: CARE PLAN ─────────────────────────────────────────────────────────
elif st.session_state.page == "care_plan":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        st.title(f"Your Recovery Plan — {state.get('diagnosis')}")

        # Show medication flags first if any
        pending_med_flags = [i for i in state.get("human_approval_queue", [])
                             if i["type"] == "medication_conflict" and i["status"] == "pending"]

        if pending_med_flags:
            st.error("⚠️ MEDICATION FLAGS REQUIRE YOUR ATTENTION")
            for flag in pending_med_flags:
                with st.expander("View medication flag"):
                    st.write(flag["content"])
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("I've reviewed with my pharmacist", key=f"approve_{flag['id']}"):
                            flag["status"] = "approved"
                            st.rerun()
                    with col2:
                        if st.button("I need more help", key=f"help_{flag['id']}"):
                            st.write("Please call your pharmacy or 1-800-PHARMACY")

        # Display care plan
        care_plan = state.get("care_plan", {})
        if care_plan:
            tab1, tab2, tab3, tab4 = st.tabs([
                "📅 First 7 Days", "💊 Medications", "⚠️ Warning Signs", "📋 Appointments"
            ])

            with tab1:
                st.subheader("Your first week, day by day")
                for day_plan in care_plan.get("first_7_days", []):
                    with st.expander(f"Day {day_plan.get('day', '?')}"):
                        for task in day_plan.get("tasks", []):
                            st.checkbox(task, key=f"task_{day_plan.get('day')}_{task[:20]}")

            with tab2:
                st.subheader("Your medications")
                for med in care_plan.get("medication_schedule", []):
                    st.info(f"💊 {med}")

            with tab3:
                st.subheader("Go to the ER immediately if:")
                for sign in state.get("warning_signs_er", []):
                    st.error(f"🔴 {sign}")
                st.subheader("Call your doctor within 24 hours if:")
                for sign in state.get("warning_signs_call", []):
                    st.warning(f"🟡 {sign}")

            with tab4:
                st.subheader("Follow-up appointments")
                for appt in state.get("appointments", []):
                    st.write(f"📅 {appt.get('provider')} ({appt.get('specialty')}) — "
                             f"Required within: {appt.get('timeframe_required')}")

        if st.button("Start Today's Check-in →"):
            state["recovery_day"] = max(1, state.get("recovery_day", 0))
            st.session_state.page = "checkin"
            st.rerun()

# ─── PAGE: DAILY CHECK-IN ────────────────────────────────────────────────────
elif st.session_state.page == "checkin":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        st.title(f"Day {state.get('recovery_day', 1)} Check-in")
        st.write("Speak your check-in or type your answers below.")

        questions = generate_checkin_questions(state)
        responses = {}

        # ── VOICE INPUT ──────────────────────────────────────────────────────
        st.subheader("🎤 Speak Your Check-in (Recommended)")
        st.caption("Click record, speak naturally about how you're feeling, then click stop.")

        # streamlit-audiorecorder gives a simple record/stop button
        # Install: pip install streamlit-audiorecorder
        try:
            from audiorecorder import audiorecorder
            audio = audiorecorder("🎤 Start Recording", "⏹ Stop Recording")

            if len(audio) > 0:
                # Audio was recorded — convert to bytes and send to ElevenLabs
                import io
                audio_buffer = io.BytesIO()
                audio.export(audio_buffer, format="wav")
                audio_bytes = audio_buffer.getvalue()

                with st.spinner("Transcribing your voice check-in..."):
                    from tools.elevenlabs_stt import transcribe_audio, parse_transcript_to_responses
                    stt_result = transcribe_audio(audio_bytes, mime_type="audio/wav")

                if stt_result["success"]:
                    transcript = stt_result["transcript"]
                    st.success("✅ Voice check-in received")
                    st.info(f"**What we heard:** {transcript}")

                    # Parse transcript into structured responses
                    with st.spinner("Understanding your responses..."):
                        responses = parse_transcript_to_responses(transcript, questions, state)

                    # Show parsed responses for patient to confirm
                    st.subheader("We understood the following — please confirm:")
                    for q in questions:
                        val = responses.get(q["id"])
                        if val is not None:
                            st.write(f"**{q['question']}** → {val}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ That's correct — submit"):
                            state["todays_checkin_responses"] = responses
                            state["checkin_method"] = "voice"
                            _run_monitoring(state)
                    with col2:
                        if st.button("✏️ Edit my answers instead"):
                            st.session_state.show_typed_form = True
                            st.rerun()

                else:
                    # STT failed — show error and fall through to typed form
                    st.warning(f"⚠️ Voice transcription issue: {stt_result['error']}")
                    st.info("No problem — please type your responses below.")
                    st.session_state.show_typed_form = True

        except ImportError:
            # audiorecorder not installed — fall through to typed form
            st.session_state.show_typed_form = True

        # ── TYPED FALLBACK ───────────────────────────────────────────────────
        show_typed = st.session_state.get("show_typed_form", False)
        with st.expander("📝 Type your responses instead", expanded=show_typed):
            with st.form("checkin_form"):
                for q in questions:
                    if q["type"] == "yes_no_detail":
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            responses[q["id"]] = st.radio(
                                q["question"], ["Yes", "No"],
                                key=f"q_{q['id']}"
                            )
                        with col2:
                            responses[f"{q['id']}_detail"] = st.text_input(
                                "Any details?", key=f"d_{q['id']}"
                            )
                    elif q["type"] == "scale_1_10":
                        responses[q["id"]] = st.slider(
                            q["question"], 1, 10, 5, key=f"q_{q['id']}"
                        )
                    elif q["type"] == "number_lbs":
                        responses[q["id"]] = st.number_input(
                            q["question"], min_value=50.0, max_value=500.0,
                            key=f"q_{q['id']}"
                        )
                    elif q["type"] == "multi_select":
                        responses[q["id"]] = st.multiselect(
                            q["question"], q.get("options", []),
                            key=f"q_{q['id']}"
                        )
                    elif q["type"] == "free_text":
                        responses[q["id"]] = st.text_area(
                            q["question"], key=f"q_{q['id']}"
                        )

                submitted = st.form_submit_button("Submit Check-in")

            if submitted:
                state["todays_checkin_responses"] = responses
                state["checkin_method"] = "typed"
                _run_monitoring(state)

# ── Helper to avoid duplicating monitoring logic ──────────────────────────────
def _run_monitoring(state):
    with st.spinner("Analyzing your check-in..."):
        monitoring_graph = build_monitoring_graph()
        result_state = monitoring_graph.invoke(state)

    st.session_state.recovery_state = result_state
    last_checkin = result_state["check_in_history"][-1]
    classification = last_checkin["classification"]

    if classification == "RED":
        if result_state.get("show_911_screen"):
            st.error("🚨 CALL 911 NOW")
            st.title("EMERGENCY — CALL 911 IMMEDIATELY")
        elif result_state.get("show_er_guidance"):
            st.error("⚠️ You should go to the ER")
            if result_state.get("er_handoff_summary"):
                st.text_area("Show this to ER staff:", result_state["er_handoff_summary"])
        else:
            st.warning("We've flagged some concerns and drafted a message to your care team.")
            st.session_state.page = "approvals"
            st.rerun()
    elif classification == "YELLOW":
        st.warning(f"⚠️ We noticed some things today: {last_checkin.get('summary')}")
        st.write(last_checkin.get("recommended_action", ""))
    else:
        st.success(f"✅ Great — {last_checkin.get('summary')}")

    result_state["recovery_day"] = result_state.get("recovery_day", 1) + 1

# ─── PAGE: APPROVAL QUEUE ────────────────────────────────────────────────────
elif st.session_state.page == "approvals":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        st.title("📬 Items Awaiting Your Review")
        pending = [i for i in state.get("human_approval_queue", [])
                   if i["status"] == "pending"]

        if not pending:
            st.success("Nothing pending — you're all caught up.")
        else:
            for item in pending:
                with st.expander(
                    f"{'⚠️ Medication Flag' if item['type'] == 'medication_conflict' else '📨 Message Draft'}"
                    f" — {item['created_at'][:10]}"
                ):
                    st.write(item["content"])

                    if item["type"] in ["escalation_message", "provider_message"]:
                        edited = st.text_area(
                            "Edit before sending:", item["content"],
                            key=f"edit_{item['id']}"
                        )
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✅ Send Now", key=f"send_{item['id']}"):
                                item["status"] = "approved"
                                item["content"] = edited
                                st.success("Message queued for sending.")
                                st.rerun()
                        with col2:
                            if st.button("❌ Don't Send", key=f"reject_{item['id']}"):
                                item["status"] = "rejected"
                                st.rerun()
                        with col3:
                            if st.button("📞 I'll Call Instead", key=f"call_{item['id']}"):
                                item["status"] = "rejected"
                                st.info("Good idea. Call your doctor's office directly.")
                                st.rerun()

# ─── PAGE: DASHBOARD ─────────────────────────────────────────────────────────
elif st.session_state.page == "dashboard":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        st.title("📊 Recovery Dashboard")
        history = state.get("check_in_history", [])

        if not history:
            st.info("Complete your first check-in to see your dashboard.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                green = sum(1 for c in history if c["classification"] == "GREEN")
                st.metric("Green days", green)
            with col2:
                yellow = sum(1 for c in history if c["classification"] == "YELLOW")
                st.metric("Yellow days", yellow)
            with col3:
                red = sum(1 for c in history if c["classification"] == "RED")
                st.metric("Red days", red)

            st.subheader("Daily vitals & check-in log")
            for checkin in reversed(history):
                icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(
                    checkin["classification"], "⚪"
                )
                vitals = state.get("daily_vitals_log", [])
                day_vitals = next(
                    (v for v in vitals if v.get("day") == checkin["day"]), {}
                )
                weight_str = f"Weight {day_vitals['weight_lbs']} lbs · " if day_vitals.get("weight_lbs") else ""
                bp_str = f"BP {day_vitals['bp_systolic']}/{day_vitals['bp_diastolic']} · " if day_vitals.get("bp_systolic") else ""
                energy_str = f"Energy {day_vitals['energy_score']}/10 · " if day_vitals.get("energy_score") else ""
                st.write(
                    f"Day {checkin['day']} {icon} — {weight_str}{bp_str}{energy_str}"
                    f"{checkin.get('summary', '')}"
                )

            if state.get("daily_vitals_log"):
                st.subheader("Medication adherence")
                meds = [m["name"] for m in state.get("medications", [])]
                vitals_log = state.get("daily_vitals_log", [])
                for med in meds:
                    taken_days = sum(
                        1 for v in vitals_log if med in v.get("meds_taken", [])
                    )
                    total_days = len(vitals_log)
                    pct = int((taken_days / total_days * 100)) if total_days > 0 else 0
                    st.progress(pct / 100, text=f"{med}: {taken_days}/{total_days} days")

# ─── PAGE: PROVIDER SUMMARY ───────────────────────────────────────────────────
elif st.session_state.page == "provider_summary":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        st.title("Provider summary")
        st.caption(
            "Auto-generated from your check-in history. "
            "Share this at your next appointment."
        )

        history = state.get("check_in_history", [])
        vitals_log = state.get("daily_vitals_log", [])

        if not history:
            st.info("Complete at least one check-in to generate your provider summary.")
        else:
            # Header card
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Patient:** {state.get('patient_name')}")
                st.markdown(f"**Diagnosis:** {state.get('diagnosis')}")
                st.markdown(
                    f"**Discharged:** {state.get('discharge_date')} · "
                    f"Day {state.get('recovery_day', 0)} of recovery"
                )
            with col2:
                st.download_button(
                    label="⬇️ Export summary",
                    data=generate_provider_summary_text(state),
                    file_name=f"recovery_summary_{state.get('patient_name', 'patient').replace(' ','_')}.txt",
                    mime="text/plain"
                )

            st.divider()

            # Vitals trend
            st.subheader("Vitals trend")
            if vitals_log:
                weights = [v["weight_lbs"] for v in vitals_log if v.get("weight_lbs")]
                if weights:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Weight at discharge",
                            f"{weights[0]} lbs"
                        )
                    with col2:
                        st.metric(
                            "Weight today",
                            f"{weights[-1]} lbs",
                            delta=f"{round(weights[-1] - weights[0], 1)} lbs"
                        )
                    with col3:
                        energy_scores = [v["energy_score"] for v in vitals_log if v.get("energy_score")]
                        if energy_scores:
                            avg_e = round(sum(energy_scores) / len(energy_scores), 1)
                            st.metric("Avg energy", f"{avg_e} / 10")

            # Medication adherence
            st.subheader("Medication adherence")
            meds = [m["name"] for m in state.get("medications", [])]
            for med in meds:
                taken = sum(1 for v in vitals_log if med in v.get("meds_taken", []))
                total = len(vitals_log)
                missed = total - taken
                if missed == 0:
                    st.success(f"✅ {med} — {taken}/{total} days (perfect)")
                else:
                    st.warning(f"⚠️ {med} — {taken}/{total} days ({missed} missed)")

            # Flagged anomalies
            st.subheader("Flagged anomalies")
            flagged = [c for c in history if c["classification"] in ["YELLOW", "RED"]]
            if not flagged:
                st.success("No anomalies flagged in this period.")
            else:
                for item in flagged:
                    icon = "🔴" if item["classification"] == "RED" else "🟡"
                    st.write(
                        f"{icon} **Day {item['day']}** — {item.get('summary', '')} "
                        f"({', '.join(item.get('flags', [])[:2])})"
                    )

            # Patient-reported symptoms summary
            st.subheader("Patient-reported summary")
            st.caption(
                "Agent-generated summary of what the patient reported across all check-ins. "
                "Review before sharing with your provider."
            )
            all_flags = []
            for c in history:
                all_flags.extend(c.get("flags", []))
            if all_flags:
                from collections import Counter
                common = Counter(all_flags).most_common(5)
                for symptom, count in common:
                    st.write(f"- {symptom} (mentioned {count} time{'s' if count > 1 else ''})")


def generate_provider_summary_text(state: dict) -> str:
    """Generate plain text export of provider summary."""
    history = state.get("check_in_history", [])
    vitals = state.get("daily_vitals_log", [])
    meds = [m["name"] for m in state.get("medications", [])]

    lines = [
        "NEXUS — PROVIDER SUMMARY",
        "=" * 40,
        f"Patient: {state.get('patient_name')}",
        f"Diagnosis: {state.get('diagnosis')}",
        f"Discharged: {state.get('discharge_date')}",
        f"Summary generated: Day {state.get('recovery_day', 0)} of recovery",
        "",
        "VITALS TREND",
        "-" * 20,
    ]
    for v in vitals:
        weight_str = f"Weight: {v['weight_lbs']} lbs" if v.get("weight_lbs") else ""
        bp_str = f"BP: {v['bp_systolic']}/{v['bp_diastolic']}" if v.get("bp_systolic") else ""
        lines.append(f"Day {v['day']}: {weight_str} {bp_str} Energy: {v.get('energy_score', '?')}/10")

    lines += ["", "MEDICATION ADHERENCE", "-" * 20]
    for med in meds:
        taken = sum(1 for v in vitals if med in v.get("meds_taken", []))
        lines.append(f"{med}: {taken}/{len(vitals)} days")

    lines += ["", "FLAGGED ANOMALIES", "-" * 20]
    for c in history:
        if c["classification"] in ["YELLOW", "RED"]:
            lines.append(f"Day {c['day']} [{c['classification']}]: {c.get('summary', '')}")

    lines += ["", "— Generated by Nexus (synthetic demo data) —"]
    return "\n".join(lines)


# ─── PAGE: HOSPITAL HISTORY ───────────────────────────────────────────────────
elif st.session_state.page == "hospital_history":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        st.title("Hospital history")
        st.caption(
            "Your hospitalization record. The current stay was auto-imported "
            "from your discharge summary. Add past stays manually."
        )

        hosp_history = state.get("hospitalization_history", [])

        if not hosp_history:
            st.info("No hospitalization records yet. Upload your discharge summary to auto-import the current stay.")
        else:
            for hosp in reversed(hosp_history):
                is_current = hosp.get("source") == "auto_imported"
                with st.container():
                    col1, col2 = st.columns([1, 6])
                    with col1:
                        year = hosp.get("admit_date", "")[:4] or hosp.get("discharge_date", "")[:4]
                        label = "Current" if is_current else year
                        st.markdown(
                            f"<div style='background:{'#EEEDFE' if is_current else '#F4F3FE'};"
                            f"border-radius:8px;padding:10px;text-align:center;"
                            f"color:#534AB7;font-size:12px;font-weight:500'>{label}</div>",
                            unsafe_allow_html=True
                        )
                    with col2:
                        st.markdown(f"**{hosp.get('diagnosis', 'Unknown diagnosis')}**")
                        meta_parts = []
                        if hosp.get("hospital_name"):
                            meta_parts.append(hosp["hospital_name"])
                        if hosp.get("admit_date") and hosp.get("discharge_date"):
                            meta_parts.append(f"{hosp['admit_date']} → {hosp['discharge_date']}")
                        if hosp.get("treating_physician"):
                            meta_parts.append(f"Dr. {hosp['treating_physician']}")
                        st.caption(" · ".join(meta_parts))

                        tags = []
                        if hosp.get("specialty"):
                            tags.append(hosp["specialty"])
                        if hosp.get("icd10_code"):
                            tags.append(f"ICD-10: {hosp['icd10_code']}")
                        if tags:
                            st.caption(" · ".join(tags))

                        source_label = "Auto-imported from discharge PDF" if is_current else "Added manually"
                        st.caption(f"_{source_label}_")

                    st.divider()

        # Manual entry form
        st.subheader("Add a past hospitalization")
        with st.form("add_hospitalization"):
            col1, col2 = st.columns(2)
            with col1:
                admit = st.text_input("Admission date (YYYY-MM-DD)")
                hospital = st.text_input("Hospital name")
                diagnosis = st.text_input("Main diagnosis")
            with col2:
                discharge = st.text_input("Discharge date (YYYY-MM-DD)")
                physician = st.text_input("Treating physician (optional)")
                icd10 = st.text_input("ICD-10 code (optional)")

            notes = st.text_area("Any notes (procedures, reason for admission, etc.)", height=80)
            submitted = st.form_submit_button("Add hospitalization")

        if submitted and admit and discharge and diagnosis:
            import uuid as uuid_lib
            new_record = {
                "id": str(uuid_lib.uuid4()),
                "admit_date": admit,
                "discharge_date": discharge,
                "hospital_name": hospital,
                "diagnosis": diagnosis,
                "icd10_code": icd10 or None,
                "treating_physician": physician or None,
                "specialty": None,
                "notes": notes or None,
                "source": "manual_entry",
                "created_at": datetime.now().isoformat()
            }
            if "hospitalization_history" not in state:
                state["hospitalization_history"] = []
            state["hospitalization_history"].append(new_record)
            st.session_state.recovery_state = state
            st.success("Hospitalization record added.")
            st.rerun()
        elif submitted:
            st.error("Please fill in admission date, discharge date, and diagnosis at minimum.")