import os
import json
import re
import math
from functools import lru_cache

from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
import requests
import pdfplumber
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI


# Load env early (supports .env in repo root)
load_dotenv(find_dotenv())

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL")  # optional but recommended

app = Flask(__name__)

# CORS: allow Next.js dev server(s) by default; can extend via CORS_ALLOW_ORIGIN
origins = {"http://localhost:3000", "http://127.0.0.1:3000"}
extra_origin = os.getenv("CORS_ALLOW_ORIGIN")
if extra_origin:
    origins.add(extra_origin)
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": list(origins)}})


# ---------- Shared helpers (Hospitals) ----------
def extract_json(text: str):
    """Try to pull a JSON object/array out of a model response."""
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None
    return None


def verify_url(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=3)
        return r.status_code < 400
    except Exception:
        return False


def haversine_miles(lat1, lon1, lat2, lon2):
    """Compute distance in miles between two lat/lon points."""
    R_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    dist_km = 2 * R_km * math.asin(math.sqrt(a))
    return dist_km * 0.621371  # km -> miles


@lru_cache(maxsize=256)
def reverse_geocode(lat: float, lon: float):
    """
    Reverse geocode to (city, state/region, country). Uses OpenStreetMap Nominatim.
    Returns dict with {city, state, country, label}. Falls back sensibly.
    """
    try:
        params = {
            "format": "jsonv2",
            "lat": str(lat),
            "lon": str(lon),
            "zoom": "10",
            "addressdetails": "1",
        }
        headers = {
            "User-Agent": f"hospital-price-finder/1.0 ({NOMINATIM_EMAIL or 'no-email-provided'})"
        }
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params=params,
            headers=headers,
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        addr = data.get("address", {})
        city = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("suburb")
            or addr.get("county")
        )
        state = addr.get("state") or addr.get("region") or addr.get("state_district")
        country = addr.get("country")
        label_parts = [p for p in [city, state, country] if p]
        label = ", ".join(label_parts) if label_parts else data.get("display_name", "Unknown location")
        return {"city": city, "state": state, "country": country, "label": label}
    except Exception:
        return {"city": None, "state": None, "country": None, "label": "this area"}


@lru_cache(maxsize=512)
def forward_geocode(address: str):
    """Resolve a free-form address/place name to (lat, lon) using Nominatim."""
    if not address:
        return (None, None)
    try:
        params = {"format": "jsonv2", "q": address, "limit": 1}
        headers = {"User-Agent": f"hospital-price-finder/1.0 ({NOMINATIM_EMAIL or 'no-email-provided'})"}
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=8
        )
        resp.raise_for_status()
        arr = resp.json() or []
        if not arr:
            return (None, None)
        item = arr[0]
        lat = item.get("lat")
        lon = item.get("lon")
        try:
            return (float(lat), float(lon))
        except Exception:
            return (None, None)
    except Exception:
        return (None, None)


# ---------- Hospitals Blueprint ----------
hospitals_bp = Blueprint("hospitals", __name__)


@hospitals_bp.route("/api/hospitals", methods=["OPTIONS"])  # Preflight if called directly
def hospitals_options():
    return ("", 204)


@hospitals_bp.route("/api/hospitals", methods=["POST"])
def hospitals():
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "Missing OPENROUTER_API_KEY"}), 500

    data = request.get_json(force=True) or {}
    lat = data.get("lat")
    lon = data.get("lon")
    location_query = data.get("location") # NEW: Accept location string
    condition = (data.get("condition") or "").strip()

    if not condition:
        return jsonify({"error": "condition required"}), 400

    # NEW: If location_query is provided, geocode it.
    if location_query and (lat is None or lon is None):
        geocoded_lat, geocoded_lon = forward_geocode(location_query)
        if geocoded_lat is None or geocoded_lon is None:
             return jsonify({"error": f"Could not find location: '{location_query}'"}), 400
        lat, lon = geocoded_lat, geocoded_lon

    if lat is None or lon is None:
        return jsonify({"error": "Location required (enable GPS or enter city/zip)"}), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return jsonify({"error": "lat/lon must be numbers"}), 400

    place = reverse_geocode(lat, lon)
    city_label = place.get("label") or "this area"

    system_msg = (
        "You are a web-connected data model that must return only structured JSON. "
        "Given a city/region and a medical condition, find and summarize hospitals in that locality "
        "(target within ~30 miles of the city center) with publicly available or estimated cash/self-pay prices "
        "for the given condition. Each object should include: name, address, phone, url, latitude, longitude, "
        "price_usd, price_is_estimate, and notes. Output strictly a JSON array."
    )

    user_msg = (
        f"locality: {city_label}\n"
        f"condition: {condition}\n\n"
        "Constraints:\n"
        "- Prefer hospitals in the named locality and adjacent municipalities (≈30 miles).\n"
        "- If exact cash/self-pay prices are unavailable, estimate sensibly and mark price_is_estimate=true with notes.\n"
        "- Include latitude/longitude if available (helps with distance checks).\n"
        "- Output strictly a JSON array of hospital objects with the requested fields—no extra commentary."
    )

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Nearby Hospitals Price Finder",
            },
            json={
                "model": "perplexity/sonar",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.2,
                "max_tokens": 1200,
                "web_search": True,
            },
            timeout=45,
        )
    except requests.RequestException as e:
        return jsonify({"error": f"OpenRouter request failed: {e}"}), 502

    if resp.status_code >= 400:
        return jsonify({"error": f"OpenRouter error {resp.status_code}: {resp.text[:600]}"}), 502

    payload = resp.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except Exception:
        return jsonify({"error": "Malformed response from model"}), 502

    items = extract_json(content)
    if not isinstance(items, list):
        return jsonify({"error": "Model did not return a JSON array"}), 502

    cleaned = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name")
        if not name:
            continue

        site_url = it.get("url")
        if site_url and not verify_url(site_url):
            continue

        addr = it.get("address")
        lat2 = it.get("latitude")
        lon2 = it.get("longitude")

        dist_miles = None
        if isinstance(lat2, (int, float)) and isinstance(lon2, (int, float)):
            try:
                dist_miles = round(haversine_miles(lat, lon, float(lat2), float(lon2)), 2)
                if dist_miles is not None and dist_miles > 37.3:
                    continue
            except Exception:
                pass

        if (not isinstance(lat2, (int, float)) or not isinstance(lon2, (int, float))) and addr:
            fg_lat, fg_lon = forward_geocode(addr)
            if isinstance(fg_lat, (int, float)) and isinstance(fg_lon, (int, float)):
                lat2, lon2 = fg_lat, fg_lon

        maps_url = None
        if addr:
            maps_url = (
                f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={requests.utils.quote(addr)}&travelmode=driving"
            )
        elif isinstance(lat2, (int, float)) and isinstance(lon2, (int, float)):
            maps_url = (
                f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={lat2},{lon2}&travelmode=driving"
            )

        price_raw = it.get("price_usd")
        try:
            price_val = float(price_raw) if price_raw is not None else None
        except Exception:
            price_val = None

        cleaned.append(
            {
                "name": name,
                "address": addr,
                "phone": it.get("phone"),
                "url": site_url,
                "latitude": lat2,
                "longitude": lon2,
                "distance_miles": dist_miles,
                "price_usd": price_val,
                "price_is_estimate": bool(it.get("price_is_estimate", True)),
                "notes": it.get("notes"),
                "maps_url": maps_url,
                "source_locality": city_label,
            }
        )

    cleaned.sort(
        key=lambda r: (
            float("inf") if r["price_usd"] is None else r["price_usd"],
            float("inf") if r.get("distance_miles") is None else r["distance_miles"],
        )
    )

    return jsonify({"results": cleaned})


# ---------- Dispute Blueprint ----------
dispute_bp = Blueprint("dispute", __name__)

# Folders for dispute assets (relative to repo structure)
SERVER_DIR = os.path.dirname(__file__)
DISPUTE_DIR = os.path.abspath(os.path.join(SERVER_DIR, "..", "dispute"))
UPLOAD_FOLDER = os.path.join(DISPUTE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
POLICY_DOCS_DIR = os.path.join(DISPUTE_DIR, "policy_docs")
PROVIDER_RULES = {
    "United": os.path.join(POLICY_DOCS_DIR, "United Healthcare Charge Policy.pdf"),
    "Providence": os.path.join(POLICY_DOCS_DIR, "Providence HealthCare Charge.pdf"),
    "Molina": os.path.join(POLICY_DOCS_DIR, "Molina HealthCare Charge.pdf"),
    "CMS": os.path.join(POLICY_DOCS_DIR, "CMS Charge.pdf"),
}

# OpenAI client (if key provided)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def ai_check_overcharges(rules_text, bill_text):
    if client is None:
        raise RuntimeError("Missing OPENAI_API_KEY")
    prompt = f"""
    You are a hospital billing auditor AI.

    Hospital Rules:
    {rules_text}

    Patient Bill:
    {bill_text}

    Instructions:
    - Identify overcharges in the patient bill based on hospital rules.
    - For each, provide line number, service, amount, and reason.
    - If none, say "No overcharges detected".
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


def ai_check_overcharges_and_discount(rules_text, bill_text, household_size, annual_income, zip_code):
    """Structured AI analysis returning a dict.

    Returns a dictionary with keys:
    - state_abbr: two-letter state code or None
    - total_eligible_discount_percent: numeric percentage (e.g., 45 for 45%) or None
    - discount_explanation: free-form string explanation
    - overcharges: list of {line_number, service, amount, reason}
    - raw_model_text: original model output (for legacy or debugging)

    We instruct the model to emit strict JSON to reduce fragile downstream parsing.
    """
    if client is None:
        raise RuntimeError("Missing OPENAI_API_KEY")

    # Strengthen system instructions & embed strict mini-schema to maximize structured reliability
    system_instructions = (
        "You are a hospital billing auditor AI. OUTPUT ONLY VALID JSON. No commentary outside JSON. "
        "Return an object with keys: state_abbr (string|null), total_eligible_discount_percent (number|null), "
        "discount_explanation (string), overcharges (array). Each overcharge is an object with: line_number (string|number|null), "
        "service (string), amount (number|null), reason (string). Amount MUST be numeric (no $ or commas) if possible. "
        "Do not include percent signs in total_eligible_discount_percent. Empty lists are allowed."
    )

    # Compact schema example (shown to model). Kept minimal to reduce hallucination chance.
    json_schema_description = {
        "state_abbr": "CA",
        "total_eligible_discount_percent": 45,
        "discount_explanation": "Applied state charity care 30% + provider financial aid 15%.",
        "overcharges": [
            {
                "line_number": 12,
                "service": "MRI Scan",
                "amount": 1800.00,
                "reason": "Exceeds contract allowed amount per Section 4.A"
            }
        ]
    }

    user_prompt = f"""
Hospital Rules Document (extract):\n{rules_text}\n\nPatient Bill (extract):\n{bill_text}\n\nContext:\nHousehold Size: {household_size}\nAnnual Income: {annual_income}\nZIP Code: {zip_code}\n\nTasks:\n1. Identify any overcharges referencing rule rationale precisely (section/page if available).\n2. Infer two-letter state from ZIP (or null if unsure).\n3. Estimate total eligible discount considering state programs, provider policy, and federal (CMS) where applicable. Use numeric percent without % symbol.\n4. Provide concise multi-line discount_explanation summarizing derivation components.\n5. Ensure overcharges array is empty when none found.\n\nReturn ONLY JSON with exactly these keys. Example structure: {json.dumps(json_schema_description, separators=(',',':'))}\n"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    raw_text = response.choices[0].message.content.strip()

    # Attempt to extract JSON robustly
    data = extract_json(raw_text)
    if not isinstance(data, dict):
        # Fallback structure
        data = {
            "state_abbr": None,
            "total_eligible_discount_percent": None,
            "discount_explanation": "Model returned unexpected format.",
            "overcharges": [],
        }

    # Normalize and coerce types
    state_abbr = data.get("state_abbr")
    if isinstance(state_abbr, str):
        state_abbr = state_abbr.strip().upper()[:2] if len(state_abbr.strip()) >= 2 else None
    else:
        state_abbr = None

    discount_percent = data.get("total_eligible_discount_percent")
    try:
        if isinstance(discount_percent, str):
            discount_percent = discount_percent.strip().replace("%", "")
        discount_percent = float(discount_percent) if discount_percent not in (None, "") else None
    except Exception:
        discount_percent = None

    discount_explanation = data.get("discount_explanation") or ""
    if not isinstance(discount_explanation, str):
        discount_explanation = str(discount_explanation)

    overcharges_list = []
    for oc in data.get("overcharges", []) or []:
        if not isinstance(oc, dict):
            continue
        line_number = oc.get("line_number")
        service = oc.get("service")
        reason = oc.get("reason")
        amount_val = oc.get("amount")
        try:
            if isinstance(amount_val, str):
                amount_val = amount_val.replace("$", "").replace(",", "").strip()
            amount_val = float(amount_val)
        except Exception:
            amount_val = None
        # Only include if there's at least service & reason
        if service and reason:
            overcharges_list.append(
                {
                    "line_number": line_number,
                    "service": service,
                    "amount": amount_val,
                    "reason": reason,
                }
            )

    return {
        "state_abbr": state_abbr,
        "total_eligible_discount_percent": discount_percent,
        "discount_explanation": discount_explanation.strip(),
        "overcharges": overcharges_list,
        "raw_model_text": raw_text,
    }


def _format_overcharge_report_for_letter(structured):
    """Create a readable text summary from the structured AI output for the letter prompt."""
    if not structured:
        return "No analysis available."
    lines = []
    if structured.get("state_abbr"):
        lines.append(f"State: {structured['state_abbr']}")
    if structured.get("total_eligible_discount_percent") is not None:
        lines.append(
            f"Total Eligible Discount: {int(structured['total_eligible_discount_percent'])}%" if structured['total_eligible_discount_percent'] is not None else "Total Eligible Discount: N/A"
        )
    if structured.get("discount_explanation"):
        lines.append("Discount Explanation:\n" + structured["discount_explanation"].strip())
    ocs = structured.get("overcharges", [])
    if not ocs:
        lines.append("Overcharges: None detected")
    else:
        lines.append("Overcharges:")
        for oc in ocs:
            ln = oc.get("line_number")
            svc = oc.get("service")
            amt = oc.get("amount")
            reason = oc.get("reason")
            amt_str = f"${amt:,.2f}" if isinstance(amt, (int, float)) else "(amount n/a)"
            lines.append(f"- Line {ln}: {svc} {amt_str} | Reason: {reason}")
    return "\n".join(lines)


def draft_dispute_letter(patient_name, hospital_name, bill_text, structured_report):
    if client is None:
        raise RuntimeError("Missing OPENAI_API_KEY")
    readable_summary = _format_overcharge_report_for_letter(structured_report)
    prompt = f"""
Draft a formal, concise yet firm letter to dispute identified overcharges for patient {patient_name} at {hospital_name}.
Include citation to financial assistance and discount eligibility if relevant. Maintain professional tone.

Structured Analysis Summary:
{readable_summary}
"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


def overcharges_found(ai_result) -> bool:
    """Return True if overcharges were found.

    Accepts either legacy raw text (string) or structured dict.
    """
    if not ai_result:
        return False
    # Structured path
    if isinstance(ai_result, dict):
        ocs = ai_result.get("overcharges", [])
        return bool(ocs)
    # Legacy text path
    if re.search(r"\bNo overcharges? detected\b", str(ai_result), re.IGNORECASE):
        return False
    return True


@dispute_bp.route("/api/dispute", methods=["GET"])
def dispute_home():
    return jsonify({"status": "ok", "providers": list(PROVIDER_RULES.keys())})


@dispute_bp.route("/api/dispute/analyze", methods=["POST"])  # multipart/form-data expected
def analyze():
    provider = request.form.get('provider')
    uploaded_rules = request.files.get('rules_pdf')
    bill_file = request.files.get('bill_pdf')
    # Optional patient context (backward compatible defaults)
    try:
        household_size = int(request.form.get('household_size', 1))
    except Exception:
        household_size = 1
    try:
        annual_income = float(request.form.get('annual_income', 0))
    except Exception:
        annual_income = 0.0
    zip_code = request.form.get('zip_code', '')

    if not bill_file:
        return jsonify({"error": "Please upload a patient bill PDF."}), 400

    if not bill_file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported for now."}), 415

    bill_path = os.path.join(UPLOAD_FOLDER, bill_file.filename)
    bill_file.save(bill_path)
    try:
        bill_text = extract_text_from_pdf(bill_path)
    except Exception as e:
        return jsonify({"error": f"Failed to read bill PDF: {e}"}), 400

    rules_path = None
    if uploaded_rules and uploaded_rules.filename:
        if not uploaded_rules.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Rules file must be a PDF."}), 415
        rules_path = os.path.join(UPLOAD_FOLDER, uploaded_rules.filename)
        uploaded_rules.save(rules_path)
    elif provider in PROVIDER_RULES:
        rules_path = PROVIDER_RULES[provider]
    else:
        return jsonify({"error": "No rules PDF selected or provider invalid."}), 400

    try:
        rules_text = extract_text_from_pdf(rules_path)
    except Exception as e:
        return jsonify({"error": f"Failed to read rules PDF: {e}"}), 400

    try:
        # Structured analysis
        ai_structured = ai_check_overcharges_and_discount(
            rules_text, bill_text, household_size, annual_income, zip_code
        )
        # For backward compatibility, keep a simple legacy summary text similar to old format
        legacy_lines = []
        if ai_structured.get("overcharges"):
            legacy_lines.append("Overcharges:")
            for oc in ai_structured["overcharges"]:
                ln = oc.get("line_number")
                svc = oc.get("service")
                amt = oc.get("amount")
                amt_str = f"${amt:,.2f}" if isinstance(amt, (int, float)) else "(n/a)"
                legacy_lines.append(f"- Line {ln}: {svc} {amt_str} | Reason: {oc.get('reason')}")
        else:
            legacy_lines.append("Overcharges: No overcharges detected")
        if ai_structured.get("state_abbr"):
            legacy_lines.append(f"State: {ai_structured['state_abbr']}")
        if ai_structured.get("total_eligible_discount_percent") is not None:
            legacy_lines.append(
                f"Total Eligible Discount: {int(ai_structured['total_eligible_discount_percent'])}%"
            )
        if ai_structured.get("discount_explanation"):
            legacy_lines.append(ai_structured["discount_explanation"].strip())
        ai_result_legacy = "\n".join(legacy_lines)

        # Draft letter only if overcharges found
        dispute_letter = ""
        if overcharges_found(ai_structured):
            dispute_letter = draft_dispute_letter(
                request.form.get('patient_name', 'John Doe'),
                provider if provider else 'Custom Provider',
                bill_text,
                ai_structured,
            )
    except Exception as e:
        return jsonify({"error": f"AI processing failed: {e}"}), 500

    return jsonify({
        "providers": list(PROVIDER_RULES.keys()),
        "ai_result": ai_result_legacy,  # legacy combined text
        "ai_structured": {
            "state_abbr": ai_structured.get("state_abbr"),
            "total_eligible_discount_percent": ai_structured.get("total_eligible_discount_percent"),
            "discount_explanation": ai_structured.get("discount_explanation"),
            "overcharges": ai_structured.get("overcharges"),
        },
        "dispute_letter": dispute_letter,
    })


# ---------- Health route ----------
@app.get("/health")
def health():
    return jsonify({"ok": True})


# Register blueprints
app.register_blueprint(hospitals_bp)
app.register_blueprint(dispute_bp)


if __name__ == "__main__":
    # Default to port 5000 to match references
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)