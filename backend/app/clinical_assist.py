from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Advisory:
    key: str
    severity: str
    title_en: str
    title_sw: str
    message_en: str
    message_sw: str
    source: str


_NOTE_HEADINGS_EN = {
    "PROGRESS_NOTE": ("Interval history / subjective", "Objective findings", "Assessment", "Plan"),
    "HISTORY_AND_PHYSICAL": ("Chief concern and history", "Examination and objective findings", "Assessment", "Plan"),
    "ED_PROVIDER_NOTE": ("Emergency history", "Examination / investigations", "Clinical impression", "Disposition and plan"),
    "NURSING_SHIFT_NOTE": ("Shift narrative", "Assessments and interventions", "Response / safety concerns", "Handoff plan"),
    "PROCEDURE_NOTE": ("Indication and consent", "Procedure narrative", "Findings / complications", "Post-procedure plan"),
    "CONSULT_NOTE": ("Reason for consultation", "Pertinent findings", "Consultant assessment", "Recommendations"),
    "DISCHARGE_SUMMARY": ("Hospital course", "Condition at discharge", "Discharge diagnoses and medicines", "Follow-up and return precautions"),
    "DEATH_PRONOUNCEMENT_NOTE": ("Circumstances and examination", "Pronouncement", "Notifications", "Post-mortem disposition"),
}

_NOTE_HEADINGS_SW = {
    "PROGRESS_NOTE": ("Historia ya sasa / maelezo ya mgonjwa", "Matokeo ya uchunguzi", "Tathmini", "Mpango"),
    "HISTORY_AND_PHYSICAL": ("Tatizo kuu na historia", "Uchunguzi na matokeo", "Tathmini", "Mpango"),
    "ED_PROVIDER_NOTE": ("Historia ya dharura", "Uchunguzi / vipimo", "Hitimisho la kliniki", "Uamuzi na mpango"),
    "NURSING_SHIFT_NOTE": ("Maelezo ya zamu", "Tathmini na hatua zilizochukuliwa", "Mwitikio / usalama", "Mpango wa makabidhiano"),
    "PROCEDURE_NOTE": ("Sababu na ridhaa", "Maelezo ya utaratibu", "Matokeo / matatizo", "Mpango baada ya utaratibu"),
    "CONSULT_NOTE": ("Sababu ya ushauri", "Matokeo muhimu", "Tathmini ya mshauri", "Mapendekezo"),
    "DISCHARGE_SUMMARY": ("Mwenendo wa matibabu", "Hali wakati wa kuruhusiwa", "Utambuzi na dawa", "Ufuatiliaji na tahadhari"),
    "DEATH_PRONOUNCEMENT_NOTE": ("Mazingira na uchunguzi", "Uthibitisho wa kifo", "Taarifa zilizotolewa", "Mpango baada ya kifo"),
}


def generate_note_draft(transcript: str, language: str = "en", note_type: str = "PROGRESS_NOTE") -> str:
    """Create a conservative note shell without inventing clinical facts.

    The verbatim normalized transcript is preserved as the source narrative. Empty
    sections are deliberately marked for clinician completion rather than filled by
    inference. This keeps speech-to-text assistance inside a clinician-controlled
    documentation workflow.
    """
    clean = " ".join(transcript.strip().split())
    if not clean:
        raise ValueError("Transcript is required")
    code = (note_type or "PROGRESS_NOTE").upper()
    if language == "sw":
        headings = _NOTE_HEADINGS_SW.get(code, _NOTE_HEADINGS_SW["PROGRESS_NOTE"])
        sections = "\n\n".join(f"{heading}:\n[Hariri na kuthibitisha]" for heading in headings)
        return (
            "RASIMU YA KUMBUKUMBU YA KLINIKI — LAZIMA IKAGULIWE NA KUSAINIWA NA MHUDUMU\n\n"
            f"Maelezo yaliyotafsiriwa kutoka sauti:\n{clean}\n\n"
            f"{sections}\n\n"
            "Uthibitisho wa chanzo: Imetengenezwa kutokana na sauti/maneno. Mfumo haujaongeza utambuzi, "
            "matokeo ya uchunguzi au mpango wa matibabu. Mtoa huduma lazima ahakiki mgonjwa, tukio, "
            "usahihi wa maandishi na kila sehemu kabla ya kusaini."
        )
    headings = _NOTE_HEADINGS_EN.get(code, _NOTE_HEADINGS_EN["PROGRESS_NOTE"])
    sections = "\n\n".join(f"{heading}:\n[Clinician to review and complete]" for heading in headings)
    return (
        "CLINICAL NOTE DRAFT — REQUIRES CLINICIAN REVIEW AND SIGNATURE\n\n"
        f"Transcribed clinician narrative:\n{clean}\n\n"
        f"{sections}\n\n"
        "Source attestation: Generated from audio/dictation. The system has not inferred diagnoses, "
        "examination findings or a treatment plan. The clinician must verify patient and encounter context, "
        "transcription accuracy and every section before signing."
    )
