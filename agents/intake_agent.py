from anthropic import Anthropic
from tools.pdf_parser import parse_discharge_pdf
from tools.pinecone_store import store_discharge_summary
import json
import os
import uuid
from datetime import datetime

client = Anthropic()

INTAKE_SYSTEM_PROMPT = """You are a medical document intake specialist. 
Your job is to extract structured information from hospital discharge summaries.
Your audience will be patients and caregivers — but you output structured JSON only.

Extract the following fields with exact precision:
- primary_diagnosis (string)
- icd10_code (string or null)
- hospital_name (string or null — name of the hospital/facility)
- admit_date (string or null — date patient was admitted)
- attending_physician (string or null — primary physician name)
- primary_specialty (string or null — e.g. Cardiology, Pulmonology)
- medications (array of objects with: name, dose, frequency, duration, food_interactions)
- appointments (array of objects with: provider, specialty, timeframe_required)
- warning_signs_er (array of strings: symptoms requiring immediate ER visit)
- warning_signs_call (array of strings: symptoms requiring doctor call within 24hrs)
- dietary_restrictions (array of strings)
- activity_restrictions (array of strings)
- needs_clarification (array of strings: fields that were unclear or missing)

Return ONLY valid JSON. No preamble. No explanation. No markdown.
If a field is not mentioned in the document, set it to null or empty array.
Never invent information not present in the document."""

def run_intake_agent(state: dict) -> dict:
    """
    Intake Agent: Parse discharge PDF, extract structured data, store in Pinecone.
    Returns updated state.
    """
    print("[Intake Agent] Starting...")

    # Step 1: Parse PDF
    pdf_result = parse_discharge_pdf(state.get("pdf_path"))

    if not pdf_result["success"]:
        state["active_flags"].append(f"PDF_PARSE_FAILED: {pdf_result['error']}")
        state["needs_clarification"].append("discharge_pdf_unreadable")
        print(f"[Intake Agent] PDF parse failed: {pdf_result['error']}")
        return state

    raw_text = pdf_result["text"]
    print(f"[Intake Agent] PDF parsed. {pdf_result['page_count']} pages, {len(raw_text)} chars.")

    # Step 2: Extract structured data via Claude
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=INTAKE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Extract structured data from this discharge summary:\n\n{raw_text}"
            }]
        )

        extracted_text = response.content[0].text.strip()
        # Strip markdown code fences if Claude wrapped the JSON
        if extracted_text.startswith("```"):
            extracted_text = extracted_text.split("```")[1]
            if extracted_text.startswith("json"):
                extracted_text = extracted_text[4:]
        extracted_text = extracted_text.strip()
        extracted = json.loads(extracted_text)

    except json.JSONDecodeError as e:
        raw = response.content[0].text if response else "no response"
        state["active_flags"].append(f"INTAKE_JSON_PARSE_FAILED: {str(e)} | RAW: {raw[:300]}")
        return state
    except Exception as e:
        state["active_flags"].append(f"INTAKE_CLAUDE_CALL_FAILED: {str(e)}")
        print(f"[Intake Agent] Claude call failed: {e}")
        return state

    # Step 3: Update state with extracted data
    state["diagnosis"] = extracted.get("primary_diagnosis", "Unknown")
    state["icd10_code"] = extracted.get("icd10_code")
    state["medications"] = extracted.get("medications", [])
    state["appointments"] = extracted.get("appointments", [])
    state["warning_signs_er"] = extracted.get("warning_signs_er", [])
    state["warning_signs_call"] = extracted.get("warning_signs_call", [])
    state["dietary_restrictions"] = extracted.get("dietary_restrictions", [])
    state["activity_restrictions"] = extracted.get("activity_restrictions", [])
    state["needs_clarification"].extend(extracted.get("needs_clarification", []))

    # Step 4: Store in Pinecone
    stored = store_discharge_summary(
        patient_id=state["patient_id"],
        text=raw_text,
        metadata={
            "patient_id": state["patient_id"],
            "diagnosis": state["diagnosis"],
            "discharge_date": state["discharge_date"]
        }
    )

    if not stored:
        state["active_flags"].append("PINECONE_STORE_FAILED_USING_LOCAL_FALLBACK")
        # Write to local JSON as fallback
        with open(f"data/{state['patient_id']}_discharge.json", "w") as f:
            json.dump(extracted, f, indent=2)

    state["intake_complete"] = True
    state["current_agent"] = "care_plan_agent"

    # Auto-populate hospitalization history from this discharge
    hosp_record = {
        "id": str(uuid.uuid4()),
        "admit_date": extracted.get("admit_date", "Unknown"),
        "discharge_date": state["discharge_date"],
        "hospital_name": extracted.get("hospital_name", "Unknown hospital"),
        "diagnosis": state["diagnosis"],
        "icd10_code": state.get("icd10_code"),
        "treating_physician": extracted.get("attending_physician"),
        "specialty": extracted.get("primary_specialty"),
        "notes": None,
        "source": "auto_imported",
        "created_at": datetime.now().isoformat()
    }
    if "hospitalization_history" not in state:
        state["hospitalization_history"] = []
    state["hospitalization_history"].append(hosp_record)

    print(f"[Intake Agent] Complete. Diagnosis: {state['diagnosis']}")
    return state