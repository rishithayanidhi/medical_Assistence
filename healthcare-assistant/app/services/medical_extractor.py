"""
medical_extractor.py

Parses OCR'd prescription / lab-report text into structured data.

Design rule (strict): this module NEVER fabricates or falls back to a
plausible-looking clinical value (e.g. "6 Months", "After Food",
"As directed"). If a field cannot be confidently found in the source
text, it is returned as None / "Not stated in document". Detection is
done structurally (dose-code patterns, dosage-form keywords, table
shape) rather than hardcoded brand or molecule name lists, so it is not
tied to any specific sample image.
"""

import re
from typing import Dict, Any, List, Optional

# Accept hyphen, en-dash, em-dash, AND underscore — OCR engines commonly
# misread the thin em-dash used in "1 — 0 — 1" style dose codes as any
# of these depending on font/rendering/model (EasyOCR in particular
# frequently reads it as "_").
DASH = r'[-\u2010\u2011\u2012\u2013\u2014_]'

# Deliberately excludes bare "TAB"/"CAP" abbreviations: those also occur
# inside the *quantity* column, e.g. "0 — 0 — 1 (tab)", which caused
# leftover dose-code fragments (no medicine name at all) to be
# misclassified as medicine lines. Full-word forms only.
DOSAGE_FORM_WORDS = r'(?:TABLET|CAPSULE|SYRUP|INJECTION|DROPS|OINTMENT|CREAM|SOLUTION|SUSPENSION|SR|DT|XR|ER)'

LAB_NOISE_WORDS = {
    "conventional", "s.i.", "si", "serum", "test", "result", "results",
    "units", "status", "reference", "range", "method", "plasma", "urine"
}


def parse_schedule_details(text_block: str) -> Dict[str, Optional[str]]:
    """
    Extract dose-frequency code, timing, and duration from a text block.
    Any field not actually present in the text is returned as None —
    never guessed.
    """
    schedule = None
    timing = None
    duration = None

    # Dose-frequency code, e.g. "1-0-1", "0 — 0 — 1", "1 – 1 – 1", "0_0_1"
    sched_m = re.search(
        rf'\b([01])\s*{DASH}\s*([01])\s*{DASH}\s*([01])\b', text_block
    )
    if sched_m:
        a, b, c = sched_m.group(1), sched_m.group(2), sched_m.group(3)
        code = f"{a}-{b}-{c}"
        labels = ["Morning", "Afternoon", "Night"]
        taken = [labels[i] for i, v in enumerate((a, b, c)) if v == "1"]
        count = sum(int(v) for v in (a, b, c))
        if taken:
            schedule = (
                f"{count} tablet{'s' if count != 1 else ''} daily "
                f"({', '.join(taken)}) ({code})"
            )
        else:
            schedule = code

    # Timing — collect every "After/Before <meal>" phrase actually present.
    # Do not assume one if the text doesn't say it.
    timing_hits = re.findall(
        r'\b(After|Before)\s+(Breakfast|Lunch|Dinner|Food|Meals?)\b',
        text_block, re.IGNORECASE
    )
    if timing_hits:
        seen = []
        for prep, meal in timing_hits:
            phrase = f"{prep.title()} {meal.title()}"
            if phrase not in seen:
                seen.append(phrase)
        timing = " & ".join(seen)

    # Duration — a number plus a time unit, only if actually present.
    dur_m = re.search(r'\b(\d+)\s*(Months?|Days?|Weeks?|Years?)\b', text_block, re.IGNORECASE)
    if dur_m:
        duration = f"{dur_m.group(1)} {dur_m.group(2).title()}"

    return {"schedule": schedule, "timing": timing, "duration": duration}


def _is_lab_report(lower_text: str) -> bool:
    return any(kw in lower_text for kw in [
        "laboratory medicine", "biochemistry", "liver profile",
        "reference range", "g/dl", "mg/dl", "u/l", "iu/l", "lipid profile",
        "renal profile", "hemogram", "complete blood count", " cbc "
    ])


def _extract_diagnosis(full_text: str) -> List[str]:
    # [^\n]+ (not \s+) so we never swallow following lines into the match.
    dx_match = re.search(
        r'(?:diagnosis|dx|impression)\s*[:\-]?\s*([^\n]+)',
        full_text, re.IGNORECASE
    )
    if not dx_match:
        return []
    dx = dx_match.group(1).strip()
    if len(dx) > 2 and dx.lower() not in {"none", "nil", "no", "rx"}:
        return [dx]
    return []


def _extract_lab_results(raw_lines: List[str]) -> List[Dict[str, str]]:
    row_pattern = re.compile(
        rf'^(?P<name>[A-Za-z][A-Za-z\s\/\(\)]{{2,45}}?)\s+'
        rf'(?:Conventional\s+)?'
        rf'(?P<value>\d+\.?\d*)\s+'
        rf'(?P<unit>[a-zA-Z/%]+)?\s*'
        rf'(?P<flag>[HL])?\s*'
        rf'(?P<low>\d+\.?\d*)\s*{DASH}\s*(?P<high>\d+\.?\d*)'
    )

    results = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip secondary unit-conversion rows (e.g. "Serum Biuret S.I. 68.00 g/l ...")
        if "s.i." in stripped.lower():
            continue

        m = row_pattern.search(stripped)
        if not m:
            continue

        name = m.group("name").strip(" .:-")
        if name.lower() in LAB_NOISE_WORDS or len(name) < 3:
            continue

        flag = m.group("flag")
        status = "Normal"
        if flag == "H":
            status = "High (Above Normal)"
        elif flag == "L":
            status = "Low (Below Normal)"

        results.append({
            "test_name": name,
            "result_value": m.group("value"),
            "units": m.group("unit") or "",
            "status": status,
            "reference_range": f"{m.group('low')} - {m.group('high')}"
        })
    return results


def _is_medicine_line(line: str) -> bool:
    """Structural check — no hardcoded brand/molecule names."""
    has_dose_unit = bool(re.search(r'\b\d+\s*(?:MG|MCG|ML|GM|G)\b', line, re.IGNORECASE))
    has_dosage_form = bool(re.search(rf'\b{DOSAGE_FORM_WORDS}\b', line, re.IGNORECASE))
    return has_dose_unit or has_dosage_form


_SCHEDULE_CODE_RE = re.compile(rf'[01]\s*{DASH}\s*[01]\s*{DASH}\s*[01]')
_TRAILING_NOISE_RE = re.compile(r'\(tab\)|timing\s*:|qty', re.IGNORECASE)


def _medicine_title(clean_l: str) -> str:
    """
    Take only the medicine-name portion of a table row, cutting the
    string off before the dose-frequency code / timing / qty columns
    (whichever appears first) rather than keeping the whole row.
    """
    cut_points = []
    m = _SCHEDULE_CODE_RE.search(clean_l)
    if m:
        cut_points.append(m.start())
    m2 = _TRAILING_NOISE_RE.search(clean_l)
    if m2:
        cut_points.append(m2.start())
    title = clean_l[: min(cut_points)] if cut_points else clean_l
    title = re.sub(r'^\d+[\s.\-]+', '', title).strip()  # strip leading list number
    return title.strip(" -|")


def _extract_prescriptions(raw_lines: List[str]) -> List[Dict[str, Optional[str]]]:
    prescriptions = []

    for i, line in enumerate(raw_lines):
        clean_l = line.strip()
        lower_l = clean_l.lower()

        if not clean_l or "diagnosis" in lower_l or "complaint" in lower_l:
            continue
        if not _is_medicine_line(clean_l):
            continue

        clean_title = _medicine_title(clean_l)
        if len(clean_title) < 4:
            continue

        dose_m = re.search(r'\b(\d+\s*(?:MG|MCG|ML|GM|G))\b', clean_l, re.IGNORECASE)
        dosage = dose_m.group(1).upper().replace(" ", "") if dose_m else None

        # Look from this line up to (but not including) the next detected
        # medicine line, capped at a generous 10 lines. Heavily fragmented
        # OCR output (one cell per line) can push the row's own "Timing:"
        # sub-line several lines past this one, so a small fixed window
        # missed it — this instead reads until the next real row starts.
        end = min(len(raw_lines), i + 10)
        for j in range(i + 1, end):
            if _is_medicine_line(raw_lines[j].strip()):
                end = j
                break
        context = "\n".join(raw_lines[i:end])
        details = parse_schedule_details(context)

        prescriptions.append({
            "medicine_name": clean_title,
            "dosage": dosage,          # None if not found — not guessed
            "frequency": details["schedule"],
            "timing": details["timing"],
            "duration": details["duration"],
            "_line_index": i,
            "_has_dosage_form": bool(re.search(rf'\b{DOSAGE_FORM_WORDS}\b', clean_l, re.IGNORECASE)),
        })

    # Merge the specific two-line pattern of "generic name only" (no
    # dosage-form word, e.g. "Oxcarbazepine 300 MG") immediately followed
    # by "brand name + form" (e.g. "OLEPTAL DT 300MG TABLET") on the very
    # next line. This is a structural row-continuation pattern, not a
    # match on dosing coincidence, so it won't merge two different drugs
    # that happen to share the same schedule.
    merged: List[Dict[str, Optional[str]]] = []
    skip_next = False
    for idx, p in enumerate(prescriptions):
        if skip_next:
            skip_next = False
            continue
        nxt = prescriptions[idx + 1] if idx + 1 < len(prescriptions) else None
        is_generic_then_brand = (
            nxt is not None
            and not p["_has_dosage_form"]
            and nxt["_has_dosage_form"]
            and nxt["_line_index"] - p["_line_index"] == 1
        )
        if is_generic_then_brand:
            combined = dict(nxt)
            combined["medicine_name"] = f'{nxt["medicine_name"]} ({p["medicine_name"]})'
            combined["dosage"] = nxt["dosage"] or p["dosage"]
            combined["frequency"] = nxt["frequency"] or p["frequency"]
            combined["timing"] = nxt["timing"] or p["timing"]
            combined["duration"] = nxt["duration"] or p["duration"]
            merged.append(combined)
            skip_next = True
        else:
            merged.append(dict(p))

    for m in merged:
        m.pop("_line_index", None)
        m.pop("_has_dosage_form", None)

    return merged


def extract_structured_medical_data(raw_lines: List[str]) -> Dict[str, Any]:
    full_text = "\n".join(raw_lines)
    lower_text = full_text.lower()

    is_lab = _is_lab_report(lower_text)
    document_type = "Diagnostic Lab Report" if is_lab else "Patient Prescription Summary"
    health_problem = _extract_diagnosis(full_text)

    if is_lab:
        lab_panel_match = re.search(
            r'\b(Liver Profile|Kidney Profile|Renal Profile|Lipid Profile|'
            r'Thyroid Profile|Biochemistry|Complete Blood Count|CBC|Blood Test)\b',
            full_text, re.IGNORECASE
        )
        lab_panel = lab_panel_match.group(1).title() if lab_panel_match else None
        lab_results = _extract_lab_results(raw_lines)

        medical_lines = [f"Report Type: {lab_panel or 'Not stated in document'}"]
        for l in lab_results:
            medical_lines.append(
                f"Test: {l['test_name']} | Result: {l['result_value']} {l['units']} "
                f"({l['status']}) | Range: {l['reference_range']}"
            )

        return {
            "status": "success",
            "document_type": document_type,
            "medical_data": {
                "test_panel": lab_panel,
                "health_problem": [lab_panel] if lab_panel else [],
                "prescriptions": [],
                "total_medicines": 0,
                "lab_results": lab_results,
                "total_lab_tests": len(lab_results)
            },
            "pure_medical_text": "\n".join(medical_lines),
            "medical_lines": medical_lines
        }

    prescriptions = _extract_prescriptions(raw_lines)

    medical_lines = []
    medical_lines.append(
        f"Problem: {', '.join(health_problem)}" if health_problem
        else "Problem: Not stated in document"
    )
    for p in prescriptions:
        medical_lines.append(
            f"Medicine: {p['medicine_name']} | "
            f"Dosage: {p['dosage'] or 'Not stated in document'} | "
            f"Schedule: {p['frequency'] or 'Not stated in document'} | "
            f"Timing: {p['timing'] or 'Not stated in document'} | "
            f"Duration: {p['duration'] or 'Not stated in document'}"
        )

    return {
        "status": "success",
        "document_type": document_type,
        "medical_data": {
            "health_problem": health_problem,
            "prescriptions": prescriptions,
            "total_medicines": len(prescriptions)
        },
        "pure_medical_text": "\n".join(medical_lines),
        "medical_lines": medical_lines
    }