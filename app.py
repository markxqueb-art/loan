from flask import Flask, render_template, request, redirect, session
import requests
import os

app = Flask(__name__)
app.secret_key = "super_secret_key_for_demo"

# Currency formatter
def format_currency(amount):
    return "₹{:,.0f}".format(amount)

app.jinja_env.filters['currency'] = format_currency


# ===============================
# HOME
# ===============================
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")


# ===============================
# LOGIN PAGE
# ===============================
@app.route("/login")
def login():
    return render_template("login.html")


# ===============================
# SEND OTP USING OTP.DEV
# ===============================
@app.route("/send-otp", methods=["POST"])
def send_otp():
    mobile = request.form.get("mobile")

    if not mobile or not mobile.isdigit() or len(mobile) != 10:
        return "Invalid mobile number"

    full_phone = "91" + mobile  # India country code

    url = "https://api.otp.dev/v1/verifications"

    headers = {
        "X-OTP-Key": os.environ.get("OTP_API_KEY"),
        "accept": "application/json",
        "content-type": "application/json"
    }

    payload = {
        "data": {
            "channel": "sms",
            "sender": "5e8368ab-b795-4adc-9088-4a5f21b58f99",
            "phone": full_phone,
            "template": "326dc91a-e63d-4828-9f25-1244ba3662d4",
            "code_length": 4
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        print("OTP API Response:", data)

        if response.status_code == 200:
            session["verification_id"] = data["data"]["id"]
            session["mobile"] = mobile
            return render_template("verify.html", mobile=mobile)
        else:
            return f"OTP sending failed: {data}"

    except Exception as e:
        return f"Error sending OTP: {str(e)}"


# ===============================
# VERIFY OTP
# ===============================
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    entered_otp = request.form.get("otp")
    verification_id = session.get("verification_id")

    if not verification_id:
        return "Verification session expired"

    url = f"https://api.otp.dev/v1/verifications/{verification_id}/check"

    headers = {
        "X-OTP-Key": os.environ.get("OTP_API_KEY"),
        "accept": "application/json",
        "content-type": "application/json"
    }

    payload = {
        "data": {
            "code": entered_otp
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        print("Verify API Response:", data)

        if response.status_code == 200 and data["data"]["verified"]:
            session["user"] = session.get("mobile")
            return redirect("/")
        else:
            return "Invalid OTP"

    except Exception as e:
        return f"Verification error: {str(e)}"


# ===============================
# LOGOUT
# ===============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ===============================
# LOAN CALCULATOR
# ===============================
@app.route('/calculate', methods=['POST'])
def calculate():
    if "user" not in session:
        return redirect("/login")

    try:
        income = float(request.form.get('income', 0))
        cibil_band = request.form.get('cibil_band')
        existing_emis = float(request.form.get('existing_emis', 0))
        loan_type = request.form.get('loan_type')

        cibil_map = {
            "<650": 600,
            "650–700": 675,
            "700–750": 725,
            "750+": 780
        }

        cibil_score = cibil_map.get(cibil_band, 700)

        results = []

        def get_interest_rate(bank, loan_type, cibil_band):
            if bank == 'HDFC':
                if loan_type == 'Home':
                    if cibil_band == '750+': return "8.00% - 8.50%"
                    if cibil_band == '700–750': return "8.30% - 9.00%"
                    if cibil_band == '650–700': return "9.00% - 9.50%"
                    return "≥ 9.50%"
                else:
                    if cibil_band == '750+': return "10.00% - 12.00%"
                    if cibil_band == '700–750': return "12.00% - 15.00%"
                    if cibil_band == '650–700': return "15.00% - 18.00%"
                    return "18.00% - 24.00%"
            elif bank == 'BoB':
                if loan_type == 'Home':
                    if cibil_band == '750+': return "8.50% - 8.90%"
                    if cibil_band == '700–750': return "8.90% - 9.30%"
                    if cibil_band == '650–700': return "9.30% - 9.80%"
                    return "≥ 9.80%"
                else:
                    if cibil_band == '750+': return "12.00% - 14.00%"
                    if cibil_band == '700–750': return "14.00% - 17.00%"
                    if cibil_band == '650–700': return "17.00% - 20.00%"
                    return "≥ 20.00%"
            return "N/A"

        # HDFC
        if cibil_score >= 700:
            eligible_emi_hdfc = (income * 0.55) - existing_emis
            loan_amount_hdfc = max(eligible_emi_hdfc, 0) * 20
            hdfc_reason = "Strong profile match"
        else:
            loan_amount_hdfc = 0
            hdfc_reason = "Credit score below 700"

        results.append({
            "bank_name": "HDFC Bank",
            "amount": loan_amount_hdfc,
            "interest_rate": get_interest_rate('HDFC', loan_type, cibil_band),
            "details": f"Based on 55% FOIR & 20x Multiplier. {hdfc_reason}."
        })

        # BoB
        if cibil_score >= 680:
            eligible_emi_bob = (income * 0.45) - existing_emis
            loan_amount_bob = max(eligible_emi_bob, 0) * 18
            bob_reason = "Standard eligibility criteria"
        else:
            loan_amount_bob = 0
            bob_reason = "Credit score below 680"

        results.append({
            "bank_name": "Bank of Baroda",
            "amount": loan_amount_bob,
            "interest_rate": get_interest_rate('BoB', loan_type, cibil_band),
            "details": f"Based on 45% FOIR & 18x Multiplier. {bob_reason}."
        })

        return render_template('results.html', results=results, income=income)

    except Exception as e:
        return f"Error: {str(e)}", 400
