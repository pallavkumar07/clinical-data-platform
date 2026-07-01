"""Enrich the test patients with rich, realistic clinical data.

For every seeded test patient (identified by an ``@example.com`` email) this:
  * fills in demographics — US Core race / ethnicity / birth sex, marital
    status, preferred language, and an emergency contact;
  * assigns providers — a random primary-care ``generalPractitioner`` plus a
    ``CareTeam`` containing all of the test providers (selected by their test
    NPIs, which automatically EXCLUDES your own Practitioner profile);
  * adds Conditions, vital-sign + lab Observations, MedicationRequests,
    AllergyIntolerances, Immunizations, and an Encounter.

Design notes:
  * Resources are discovered from Medplum, not hard-coded, so re-seeding the
    patients/providers and re-running this still works.
  * Every generated resource carries a stable sample identifier and is created
    with ``If-None-Exist``, so the script is **idempotent** — safe to re-run.
  * Randomness is seeded per-patient, so re-runs produce the same data.

Usage:
    python scripts/seed_clinical_data.py
"""

from __future__ import annotations

import asyncio
import base64
import random
from datetime import datetime, timedelta, timezone

from clinical_data_platform.services.medplum import MedplumClient

SAMPLE_SYS = "https://clinical-data-platform.example/sample-data"
# The 5 test providers created by scripts/seed_providers.py. Selecting by these
# NPIs is how we associate patients to providers WITHOUT ever including you.
TEST_NPIS = {f"100000000{i}" for i in range(1, 6)}

NOW = datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


# --- Reference data pools --------------------------------------------------

RACES = [
    ("2106-3", "White"),
    ("2054-5", "Black or African American"),
    ("2028-9", "Asian"),
    ("1002-5", "American Indian or Alaska Native"),
]
ETHNICITIES = [("2135-2", "Hispanic or Latino"), ("2186-5", "Not Hispanic or Latino")]
LANGUAGES = [("en", "English"), ("en", "English"), ("es", "Spanish"), ("hi", "Hindi")]
MARITAL = [("M", "Married"), ("S", "Never Married"), ("D", "Divorced"), ("W", "Widowed")]

# condition -> aligned medication, so problems and meds are coherent.
CONDITIONS = [
    {"slug": "htn", "code": "38341003", "display": "Hypertension",
     "med": ("314076", "Lisinopril 10 MG Oral Tablet", "1 tablet by mouth once daily")},
    {"slug": "dm2", "code": "44054006", "display": "Type 2 diabetes mellitus",
     "med": ("861007", "Metformin hydrochloride 500 MG Oral Tablet", "1 tablet twice daily with meals")},
    {"slug": "hld", "code": "55822004", "display": "Hyperlipidemia",
     "med": ("617312", "Atorvastatin 20 MG Oral Tablet", "1 tablet at bedtime")},
    {"slug": "asthma", "code": "195967001", "display": "Asthma",
     "med": ("745679", "Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler", "2 puffs every 4-6 hours as needed")},
    {"slug": "hypothyroid", "code": "40930008", "display": "Hypothyroidism",
     "med": ("966224", "Levothyroxine Sodium 0.05 MG Oral Tablet", "1 tablet every morning")},
    {"slug": "gerd", "code": "235595009", "display": "Gastroesophageal reflux disease",
     "med": ("402014", "Omeprazole 20 MG Delayed Release Oral Capsule", "1 capsule daily before breakfast")},
    {"slug": "depression", "code": "370143000", "display": "Major depressive disorder",
     "med": ("312940", "Sertraline 50 MG Oral Tablet", "1 tablet daily")},
    {"slug": "osteoarthritis", "code": "396275006", "display": "Osteoarthritis",
     "med": ("197805", "Ibuprofen 600 MG Oral Tablet", "1 tablet every 8 hours as needed")},
]

ALLERGIES = [
    {"slug": "penicillin", "code": "91936005", "display": "Allergy to penicillin",
     "category": "medication", "crit": "high", "reaction": ("247472004", "Hives")},
    {"slug": "peanut", "code": "91935009", "display": "Allergy to peanuts",
     "category": "food", "crit": "high", "reaction": ("271807003", "Skin rash")},
    {"slug": "shellfish", "code": "300913006", "display": "Shellfish allergy",
     "category": "food", "crit": "low", "reaction": ("267036007", "Dyspnea")},
    {"slug": "nka", "code": "716186003", "display": "No known allergy",
     "category": None, "crit": "low", "reaction": None},
]

IMMUNIZATIONS = [
    ("140", "Influenza, seasonal, injectable"),
    ("213", "SARS-COV-2 (COVID-19) vaccine, unspecified"),
    ("115", "Tdap"),
    ("133", "Pneumococcal conjugate PCV 13"),
    ("187", "Zoster recombinant"),
]

PAYERS = [
    ("bcbs", "Blue Cross Blue Shield"),
    ("aetna", "Aetna"),
    ("uhc", "UnitedHealthcare"),
    ("cigna", "Cigna"),
    ("medicare", "Medicare"),
]
PLAN_TYPES = [("HMO", "health maintenance organization policy"),
              ("PPO", "preferred provider organization policy"),
              ("POS", "point of service policy")]


# --- Builders --------------------------------------------------------------

def sample_id(pid: str, slug: str) -> list[dict]:
    return [{"system": SAMPLE_SYS, "value": f"{pid}-{slug}"}]


def vital(pid: str, slug: str, loinc: str, name: str, value: float, unit: str,
          ucum: str, when: datetime) -> dict:
    return {
        "resourceType": "Observation", "status": "final",
        "identifier": sample_id(pid, slug),
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                   "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": name}], "text": name},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": iso(when),
        "valueQuantity": {"value": round(value, 1), "unit": unit,
                          "system": "http://unitsofmeasure.org", "code": ucum},
    }


def lab(pid: str, slug: str, loinc: str, name: str, value: float, unit: str,
        ucum: str, when: datetime) -> dict:
    o = vital(pid, slug, loinc, name, value, unit, ucum, when)
    o["category"] = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                  "code": "laboratory", "display": "Laboratory"}]}]
    return o


# --- Demographics update ---------------------------------------------------

def build_demographics(patient: dict, rng: random.Random, providers: list[dict]) -> dict:
    race = rng.choice(RACES)
    eth = rng.choice(ETHNICITIES)
    lang = rng.choice(LANGUAGES)
    mar = rng.choice(MARITAL)
    sex = "F" if patient.get("gender") == "female" else "M"

    extensions = [
        {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
         "extension": [
             {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238",
                                                    "code": race[0], "display": race[1]}},
             {"url": "text", "valueString": race[1]}]},
        {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
         "extension": [
             {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238",
                                                    "code": eth[0], "display": eth[1]}},
             {"url": "text", "valueString": eth[1]}]},
        {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex", "valueCode": sex},
    ]

    patient["extension"] = extensions
    patient["maritalStatus"] = {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                                            "code": mar[0], "display": mar[1]}], "text": mar[1]}
    patient["communication"] = [{"language": {"coding": [{"system": "urn:ietf:bcp:47",
                                                          "code": lang[0], "display": lang[1]}]},
                                 "preferred": True}]
    patient["contact"] = [{
        "relationship": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0131",
                                      "code": "C", "display": "Emergency Contact"}]}],
        "name": {"family": rng.choice(["Brooks", "Nguyen", "Patel", "Garcia", "Davis"]),
                 "given": [rng.choice(["Jordan", "Sam", "Alex", "Riley", "Casey"])]},
        "telecom": [{"system": "phone", "value": f"555-0{rng.randint(300, 399)}", "use": "mobile"}],
    }]
    # Primary care provider = one random test provider (never you).
    primary = rng.choice(providers)
    patient["generalPractitioner"] = [{"reference": f"Practitioner/{primary['id']}",
                                       "display": display_name(primary)}]
    return patient, primary


def display_name(practitioner: dict) -> str:
    n = practitioner.get("name", [{}])[0]
    parts = (n.get("prefix") or []) + n.get("given", []) + [n.get("family", "")] + (n.get("suffix") or [])
    return " ".join(p for p in parts if p).strip()


# --- Main ------------------------------------------------------------------

async def main() -> None:
    c = MedplumClient()
    if not c.is_configured:
        raise SystemExit("Medplum not configured — set CDP_MEDPLUM_* in .env")

    # Discover providers (test NPIs only → excludes your profile).
    pr_bundle = await c.search("Practitioner", _count="100")
    providers = []
    for e in pr_bundle.get("entry", []):
        res = e["resource"]
        npis = {i.get("value") for i in res.get("identifier", [])}
        if npis & TEST_NPIS:
            providers.append(res)
    if not providers:
        raise SystemExit("No test providers found — run scripts/seed_providers.py first.")
    print(f"Found {len(providers)} test providers (your profile excluded):")
    for p in providers:
        print(f"    - {display_name(p)}")

    # Discover test patients (@example.com email).
    pt_bundle = await c.search("Patient", _count="100")
    patients = []
    for e in pt_bundle.get("entry", []):
        res = e["resource"]
        emails = [t.get("value", "") for t in res.get("telecom", []) if t.get("system") == "email"]
        if any(em.endswith("@example.com") for em in emails):
            patients.append(res)
    if not patients:
        raise SystemExit("No test patients found — run scripts/seed_patients.py first.")

    # Create payer Organizations once (idempotent); Coverage.payor references them.
    payers = []
    for slug, name in PAYERS:
        org = await c.create("Organization", {
            "resourceType": "Organization", "identifier": [{"system": SAMPLE_SYS, "value": f"payer-{slug}"}],
            "active": True, "name": name,
            "type": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/organization-type",
                                  "code": "pay", "display": "Payer"}]}],
        }, if_none_exist=f"identifier={SAMPLE_SYS}|payer-{slug}")
        payers.append(org)
    print(f"\nPayer organizations ready: {', '.join(p['name'] for p in payers)}")

    print(f"\nEnriching {len(patients)} test patients...\n")

    for patient in patients:
        pid = patient["id"]
        pname = display_name(patient) or pid
        rng = random.Random(pid)  # deterministic per patient

        # 1) Demographics + primary provider.
        updated, primary = build_demographics(dict(patient), rng, providers)
        await c.update("Patient", pid, updated)

        # 2) CareTeam = all test providers (this is the "associate to providers" link).
        care_participants = []
        for prov in providers:
            role = "Primary care provider" if prov["id"] == primary["id"] else \
                display_name(prov)
            care_participants.append({
                "member": {"reference": f"Practitioner/{prov['id']}", "display": display_name(prov)},
                "role": [{"text": role}],
            })
        await c.create("CareTeam", {
            "resourceType": "CareTeam", "status": "active",
            "identifier": sample_id(pid, "careteam"),
            "name": f"Care team for {pname}",
            "subject": {"reference": f"Patient/{pid}"},
            "participant": care_participants,
        }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-careteam")

        # 3) Conditions (1-2) + aligned medications.
        conds = rng.sample(CONDITIONS, rng.randint(1, 2))
        for cond in conds:
            onset = NOW - timedelta(days=rng.randint(180, 1500))
            await c.create("Condition", {
                "resourceType": "Condition", "identifier": sample_id(pid, f"cond-{cond['slug']}"),
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                               "code": "active"}]},
                "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                                    "code": "confirmed"}]},
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                          "code": "problem-list-item", "display": "Problem List Item"}]}],
                "code": {"coding": [{"system": "http://snomed.info/sct", "code": cond["code"],
                                     "display": cond["display"]}], "text": cond["display"]},
                "subject": {"reference": f"Patient/{pid}"},
                "onsetDateTime": iso(onset), "recordedDate": iso(onset),
            }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-cond-{cond['slug']}")

            rx, rx_name, sig = cond["med"]
            await c.create("MedicationRequest", {
                "resourceType": "MedicationRequest", "identifier": sample_id(pid, f"med-{cond['slug']}"),
                "status": "active", "intent": "order",
                "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                                          "code": rx, "display": rx_name}], "text": rx_name},
                "subject": {"reference": f"Patient/{pid}"},
                "authoredOn": iso(NOW - timedelta(days=rng.randint(1, 120))),
                "requester": {"reference": f"Practitioner/{primary['id']}", "display": display_name(primary)},
                "dosageInstruction": [{"text": sig}],
            }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-med-{cond['slug']}")

        # 4) Vitals (most recent visit).
        when = NOW - timedelta(days=rng.randint(3, 40))
        height = rng.uniform(150, 190)
        weight = rng.uniform(55, 100)
        bmi = weight / ((height / 100) ** 2)
        sys_bp, dia_bp = rng.randint(108, 145), rng.randint(68, 95)
        await c.create("Observation", {
            "resourceType": "Observation", "status": "final", "identifier": sample_id(pid, "vital-bp"),
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                      "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9",
                                 "display": "Blood pressure panel"}], "text": "Blood pressure"},
            "subject": {"reference": f"Patient/{pid}"}, "effectiveDateTime": iso(when),
            "component": [
                {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic BP"}]},
                 "valueQuantity": {"value": sys_bp, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
                {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic BP"}]},
                 "valueQuantity": {"value": dia_bp, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
            ],
        }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-vital-bp")

        for slug, loinc, name, val, unit, ucum in [
            ("vital-hr", "8867-4", "Heart rate", rng.uniform(58, 92), "/min", "/min"),
            ("vital-temp", "8310-5", "Body temperature", rng.uniform(36.4, 37.2), "Cel", "Cel"),
            ("vital-rr", "9279-1", "Respiratory rate", rng.uniform(12, 18), "/min", "/min"),
            ("vital-spo2", "59408-5", "Oxygen saturation", rng.uniform(95, 100), "%", "%"),
            ("vital-height", "8302-2", "Body height", height, "cm", "cm"),
            ("vital-weight", "29463-7", "Body weight", weight, "kg", "kg"),
            ("vital-bmi", "39156-5", "Body mass index", bmi, "kg/m2", "kg/m2"),
        ]:
            await c.create("Observation", vital(pid, slug, loinc, name, val, unit, ucum, when),
                           if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-{slug}")

        # 5) Labs.
        lwhen = NOW - timedelta(days=rng.randint(10, 90))
        lab_refs = []
        for slug, loinc, name, val, unit, ucum in [
            ("lab-glucose", "2339-0", "Glucose", rng.uniform(80, 130), "mg/dL", "mg/dL"),
            ("lab-a1c", "4548-4", "Hemoglobin A1c", rng.uniform(5.0, 7.5), "%", "%"),
            ("lab-chol", "2093-3", "Total cholesterol", rng.uniform(150, 240), "mg/dL", "mg/dL"),
            ("lab-ldl", "18262-6", "LDL cholesterol", rng.uniform(80, 160), "mg/dL", "mg/dL"),
            ("lab-hdl", "2085-9", "HDL cholesterol", rng.uniform(40, 70), "mg/dL", "mg/dL"),
            ("lab-creat", "2160-0", "Creatinine", rng.uniform(0.7, 1.2), "mg/dL", "mg/dL"),
        ]:
            obs = await c.create("Observation", lab(pid, slug, loinc, name, val, unit, ucum, lwhen),
                                 if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-{slug}")
            lab_refs.append({"reference": f"Observation/{obs['id']}", "display": name})

        # 6) Allergy.
        al = rng.choice(ALLERGIES)
        allergy = {
            "resourceType": "AllergyIntolerance", "identifier": sample_id(pid, f"allergy-{al['slug']}"),
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                           "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                                               "code": "confirmed"}]},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": al["code"],
                                 "display": al["display"]}], "text": al["display"]},
            "patient": {"reference": f"Patient/{pid}"},
        }
        if al["category"]:
            allergy["category"] = [al["category"]]
            allergy["criticality"] = al["crit"]
            allergy["type"] = "allergy"
        if al["reaction"]:
            allergy["reaction"] = [{"manifestation": [{"coding": [{"system": "http://snomed.info/sct",
                                    "code": al["reaction"][0], "display": al["reaction"][1]}],
                                    "text": al["reaction"][1]}]}]
        await c.create("AllergyIntolerance", allergy,
                       if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-allergy-{al['slug']}")

        # 7) Immunizations (2-3).
        for cvx, vname in rng.sample(IMMUNIZATIONS, rng.randint(2, 3)):
            await c.create("Immunization", {
                "resourceType": "Immunization", "identifier": sample_id(pid, f"imm-{cvx}"),
                "status": "completed",
                "vaccineCode": {"coding": [{"system": "http://hl7.org/fhir/sid/cvx", "code": cvx,
                                            "display": vname}], "text": vname},
                "patient": {"reference": f"Patient/{pid}"},
                "occurrenceDateTime": iso(NOW - timedelta(days=rng.randint(30, 700))),
            }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-imm-{cvx}")

        # 8) Encounter (the recent visit, with a random provider).
        enc_prov = rng.choice(providers)
        estart = when
        enc = await c.create("Encounter", {
            "resourceType": "Encounter", "identifier": sample_id(pid, "encounter"),
            "status": "finished",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                      "code": "AMB", "display": "ambulatory"},
            "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "162673000",
                                  "display": "General examination of patient"}], "text": "Office visit"}],
            "subject": {"reference": f"Patient/{pid}"},
            "participant": [{"individual": {"reference": f"Practitioner/{enc_prov['id']}",
                                            "display": display_name(enc_prov)}}],
            "period": {"start": iso(estart), "end": iso(estart + timedelta(minutes=30))},
        }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-encounter")
        enc_ref = f"Encounter/{enc['id']}"

        # 9) DiagnosticReport — groups this patient's lab Observations.
        await c.create("DiagnosticReport", {
            "resourceType": "DiagnosticReport", "identifier": sample_id(pid, "labreport"),
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                                      "code": "LAB", "display": "Laboratory"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "24323-8",
                                 "display": "Comprehensive metabolic + lipid panel"}], "text": "Laboratory panel"},
            "subject": {"reference": f"Patient/{pid}"},
            "encounter": {"reference": enc_ref},
            "effectiveDateTime": iso(lwhen), "issued": iso(lwhen),
            "performer": [{"reference": f"Practitioner/{primary['id']}", "display": display_name(primary)}],
            "result": lab_refs,
        }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-labreport")

        # 10) Coverage — insurance with a payer Organization.
        payer = rng.choice(payers)
        plan = rng.choice(PLAN_TYPES)
        await c.create("Coverage", {
            "resourceType": "Coverage", "identifier": sample_id(pid, "coverage"),
            "status": "active",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                                 "code": plan[0], "display": plan[1]}], "text": plan[1]},
            "subscriberId": f"SUB{rng.randint(10**8, 10**9 - 1)}",
            "beneficiary": {"reference": f"Patient/{pid}", "display": pname},
            "relationship": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/subscriber-relationship",
                                         "code": "self", "display": "Self"}]},
            "payor": [{"reference": f"Organization/{payer['id']}", "display": payer["name"]}],
            "class": [
                {"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class",
                                      "code": "group"}]}, "value": f"GRP{rng.randint(1000, 9999)}",
                 "name": f"{payer['name']} Group"},
                {"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class",
                                      "code": "plan"}]}, "value": plan[0], "name": f"{payer['name']} {plan[0]}"},
            ],
        }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-coverage")

        # 11) Clinical note — a progress note as a DocumentReference (US Core clinical note).
        cond_names = ", ".join(x["display"] for x in conds)
        note_text = (
            f"PROGRESS NOTE\n"
            f"Patient: {pname}   Date: {estart.date()}   Provider: {display_name(primary)}\n\n"
            f"Subjective: Patient presents for routine follow-up and reports feeling well "
            f"with no acute complaints.\n"
            f"Objective: Vitals reviewed and within expected ranges for this visit. "
            f"Laboratory panel obtained.\n"
            f"Assessment: {cond_names}.\n"
            f"Plan: Continue current medications, reinforce lifestyle measures, and follow up "
            f"in 3 months or sooner as needed.\n"
        )
        note_b64 = base64.b64encode(note_text.encode()).decode()
        await c.create("DocumentReference", {
            "resourceType": "DocumentReference", "identifier": sample_id(pid, "note"),
            "status": "current", "docStatus": "final",
            "type": {"coding": [{"system": "http://loinc.org", "code": "11506-3",
                                 "display": "Progress note"}], "text": "Progress note"},
            "category": [{"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                                      "code": "clinical-note", "display": "Clinical Note"}]}],
            "subject": {"reference": f"Patient/{pid}", "display": pname},
            "date": iso(estart),
            "author": [{"reference": f"Practitioner/{primary['id']}", "display": display_name(primary)}],
            "content": [{"attachment": {"contentType": "text/plain", "data": note_b64,
                                        "title": "Progress Note"}}],
            "context": {"encounter": [{"reference": enc_ref}],
                        "period": {"start": iso(estart), "end": iso(estart + timedelta(minutes=30))}},
        }, if_none_exist=f"identifier={SAMPLE_SYS}|{pid}-note")

        print(f"  ✓ {pname:<26} PCP={display_name(primary):<22} dx: {cond_names}"
              f" | ins: {payer['name']}")

    print("\nDone. Explore in Medplum:")
    print("    Patients:    https://app.medplum.com/Patient")
    print("    Care teams:  https://app.medplum.com/CareTeam")
    print("    Lab reports: https://app.medplum.com/DiagnosticReport")
    print("    Coverage:    https://app.medplum.com/Coverage")
    print("    Notes:       https://app.medplum.com/DocumentReference")


if __name__ == "__main__":
    asyncio.run(main())
