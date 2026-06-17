from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", "B", 16)
pdf.cell(0, 10, "DISCHARGE SUMMARY - SYNTHETIC PATIENT DATA (NOT REAL)", ln=True, align="C")
pdf.ln(5)

pdf.set_font("Helvetica", size=11)

content = """
Patient: John Demo Patient
Date of Birth: 01/15/1955
Discharge Date: 2025-06-01
Admit Date: 2025-05-27
Hospital: City General Hospital
Attending Physician: Dr. Michael Torres
Primary Specialty: Cardiology

DIAGNOSIS
Primary Diagnosis: Congestive Heart Failure (CHF) Exacerbation
ICD-10 Code: I50.9

MEDICATIONS AT DISCHARGE
1. Furosemide (Lasix) 40mg - Take once daily in the morning with water
2. Lisinopril 10mg - Take once daily with breakfast
3. Metoprolol Succinate 25mg - Take once daily
4. Potassium Chloride 20mEq - Take once daily with food

FOLLOW-UP APPOINTMENTS
- Cardiologist: Dr. Sarah Chen - within 7 days of discharge
- Primary Care: Dr. James Park - within 14 days of discharge

ACTIVITY RESTRICTIONS
- No lifting more than 10 pounds for 4 weeks
- No driving for 1 week
- Walk 5-10 minutes twice daily, increase gradually as tolerated

DIETARY RESTRICTIONS
- Sodium restriction: less than 2000mg per day
- Fluid restriction: less than 2 liters per day
- Weigh yourself every morning before eating or drinking

GO TO THE EMERGENCY ROOM IMMEDIATELY IF YOU EXPERIENCE
- Chest pain or pressure
- Difficulty breathing at rest
- Weight gain of more than 2 pounds in one day or 5 pounds in one week
- Severe swelling in legs, ankles, or feet
- Fainting or loss of consciousness

CALL YOUR DOCTOR WITHIN 24 HOURS IF YOU NOTICE
- Weight gain of 1-2 pounds in one day
- Increased shortness of breath with activity
- Increased swelling in feet or ankles
- Dizziness or lightheadedness
- Fever above 101 degrees F

NOTES
Patient was admitted for acute exacerbation of known CHF. Responded well to IV
diuresis. Fluid overload resolved. Discharged in stable condition with close
outpatient follow-up arranged. Patient and caregiver educated on daily weight
monitoring and fluid/sodium restrictions.
"""

for line in content.strip().split("\n"):
    if line.strip() == line.strip().upper() and len(line.strip()) > 3:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, line.strip(), ln=True)
        pdf.set_font("Helvetica", size=11)
    else:
        pdf.cell(0, 7, line, ln=True)

pdf.output("test_discharge.pdf")
print("Created test_discharge.pdf successfully")
