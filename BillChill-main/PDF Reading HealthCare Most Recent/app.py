from flask import Flask, render_template, request
import pdfplumber
import os
from openai import OpenAI

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_CODE"))

# Preloaded provider rules PDFs
PROVIDER_RULES = {
    "United": "C:/Users/ximud/OneDrive/Desktop/PDF Reading HealthCare/United Healthcare Charge Policy.pdf",
    "Providence": "C:/Users/ximud/OneDrive/Desktop/PDF Reading HealthCare/Providence HealthCare Charge.pdf",
    "Molina": "C:/Users/ximud/OneDrive/Desktop/PDF Reading HealthCare/Molina HealthCare Charge.pdf",
    "CMS": "C:/Users/ximud/OneDrive/Desktop/PDF Reading HealthCare/CMS Charge.pdf"
}

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def ai_check_overcharges_and_discount(rules_text, bill_text, household_size, annual_income, zip_code):
    """
    Ask GPT to:
    1. Detect overcharges in the bill based on hospital rules.
    2. Determine the patient's state from the ZIP code.
    3. Estimate the patient's total eligible discount (state + provider + federal).
    """
    prompt = f"""
You are a hospital billing auditor AI.

Hospital Rules:
{rules_text}

Patient Bill:
{bill_text}

Patient Info:
Household Size: {household_size}
Annual Income: {annual_income}
ZIP Code: {zip_code}

Tasks:
1. Identify overcharges in the patient bill based on hospital rules.
   - For each, provide line number, service, amount, and reason.
   - If none, say "No overcharges detected".
2. Determine the patient's state based on the ZIP code.
3. Estimate the patient's total eligible discount based on:
   - State law / state assistance programs
   - Provider financial assistance policies
   - Federal or CMS programs if applicable
   - Household size and annual income

Output format:
- Overcharges:
[Line info, service, amount, reason or "No overcharges detected"]
- State: [State abbreviation]
- Total Eligible Discount: [percentage]
"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

def draft_dispute_letter(patient_name, provider_name, bill_text, ai_overcharge_report):
    prompt = f"""
Draft a professional dispute letter for {patient_name} at {provider_name}.
Include the overcharges and the total eligible discount from the AI analysis:
{ai_overcharge_report}

Keep it formal, polite, and concise.
"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

@app.route('/')
def home():
    return render_template('index.html', providers=list(PROVIDER_RULES.keys()))

@app.route('/analyze', methods=['POST'])
def analyze():
    provider = request.form.get('provider')
    uploaded_rules = request.files.get('rules_pdf')
    bill_file = request.files.get('bill_pdf')
    household_size = int(request.form.get('household_size', 1))
    annual_income = float(request.form.get('annual_income', 0))
    zip_code = request.form.get('zip_code', "")

    if not bill_file:
        return "Please upload a patient bill PDF.", 400

    # Save uploaded bill
    bill_path = os.path.join(UPLOAD_FOLDER, bill_file.filename)
    bill_file.save(bill_path)
    bill_text = extract_text_from_pdf(bill_path)

    # Determine rules PDF
    if uploaded_rules:
        rules_path = os.path.join(UPLOAD_FOLDER, uploaded_rules.filename)
        uploaded_rules.save(rules_path)
    elif provider in PROVIDER_RULES:
        rules_path = PROVIDER_RULES[provider]
    else:
        return "No rules PDF selected or provider invalid.", 400

    rules_text = extract_text_from_pdf(rules_path)

    # AI overcharge + total discount analysis
    ai_result = ai_check_overcharges_and_discount(
        rules_text, bill_text, household_size, annual_income, zip_code
    )

    # Draft dispute letter including AI analysis
    dispute_letter = draft_dispute_letter(
        "John Doe",
        provider if provider else "Custom Provider",
        bill_text,
        ai_result
    )

    return render_template('index.html',
                           providers=list(PROVIDER_RULES.keys()),
                           ai_result=ai_result,
                           dispute_letter=dispute_letter)

if __name__ == '__main__':
    app.run(debug=True)
