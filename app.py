from flask import Flask, render_template, request, redirect, url_for, session
import locale
import sqlite3
import datetime
import os
import random
import time

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

# In-memory store for OTPs (as per user request)
otp_store = {}

def generate_otp():
    return random.randint(1000, 9999)

# Set locale for currency formatting (Indian Rupee)
def format_currency(amount):
    return "₹{:,.0f}".format(amount)

app.jinja_env.filters['currency'] = format_currency

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/send-otp", methods=["POST"])
def send_otp():
    mobile = request.form["mobile"]

    if not mobile.isdigit() or len(mobile) != 10:
        return "Invalid mobile number"

    otp = generate_otp()
    expiry = time.time() + 300

    otp_store[mobile] = {
        "otp": otp,
        "expiry": expiry,
        "attempts": 0
    }

    # SIMULATION: Print OTP to console AND write to file
    print(f"\n{'='*30}\nSIMULATED SMS to {mobile}: Your OTP is {otp}\n{'='*30}\n")
   

    return render_template("verify.html", mobile=mobile)

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    mobile = request.form["mobile"]
    entered_otp = request.form["otp"]

    data = otp_store.get(mobile)

    if not data:
        return "OTP not found"

    if time.time() > data["expiry"]:
        del otp_store[mobile]
        return "OTP expired"

    if str(data["otp"]) == entered_otp:
        session["user"] = mobile
        del otp_store[mobile]
        
        # Also log to DB if needed, but user didn't explicitly ask for it in this snippet. 
        # Keeping existing DB logging for good measure if possible, but simplest is to stick to snippet.
        # I'll stick to the snippet for flow control.
        
        return redirect("/")   
    else:
        return "Invalid OTP"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# Previous calculator route needs to remain available for the form submission from index.html
# The index.html form points to /calculate. 
# We should protect it as well.
@app.route('/calculate', methods=['POST'])
def calculate():
    if "user" not in session:
         return redirect("/login")
        
    try:
        # Get inputs
        income = float(request.form.get('income'))
        employment_type = request.form.get('employment_type') 
        cibil_band = request.form.get('cibil_band') 
        
        cibil_map = {
            "<650": 600,
            "650–700": 675,
            "700–750": 725,
            "750+": 780
        }
        cibil_score = cibil_map.get(cibil_band, 700)

        existing_emis = float(request.form.get('existing_emis'))
        loan_tenure = float(request.form.get('loan_tenure'))
        loan_type = request.form.get('loan_type')

        results = []


        # --- Interest Rate Logic ---
        def get_interest_rate(bank, loan_type, cibil_band):
            # HDFC Rules
            if bank == 'HDFC':
                if loan_type == 'Home':
                    if cibil_band == '750+': return "8.00% - 8.50%"
                    if cibil_band == '700–750': return "8.30% - 9.00%"
                    if cibil_band == '650–700': return "9.00% - 9.50%"
                    return "≥ 9.50%"
                else: # Personal
                    if cibil_band == '750+': return "10.00% - 12.00%"
                    if cibil_band == '700–750': return "12.00% - 15.00%"
                    if cibil_band == '650–700': return "15.00% - 18.00%"
                    return "18.00% - 24.00%"
            
            # BoB Rules
            elif bank == 'BoB':
                if loan_type == 'Home':
                    if cibil_band == '750+': return "8.50% - 8.90%"
                    if cibil_band == '700–750': return "8.90% - 9.30%"
                    if cibil_band == '650–700': return "9.30% - 9.80%"
                    return "≥ 9.80%"
                else: # Personal
                    if cibil_band == '750+': return "12.00% - 14.00%"
                    if cibil_band == '700–750': return "14.00% - 17.00%"
                    if cibil_band == '650–700': return "17.00% - 20.00%"
                    return "≥ 20.00%"
            return "N/A"

        # --- HDFC Bank Rules ---
        hdfc_eligible = True
        if cibil_score < 700:
            hdfc_eligible = False
            hdfc_reason = "Credit score below 700"
        else:
            hdfc_reason = "Strong profile match"
        
        if hdfc_eligible:
            eligible_emi_hdfc = (income * 0.55) - existing_emis
            if eligible_emi_hdfc < 0: eligible_emi_hdfc = 0
            
            loan_amount_hdfc = eligible_emi_hdfc * 20
            if loan_amount_hdfc < 0: loan_amount_hdfc = 0
        else:
            loan_amount_hdfc = 0

        hdfc_rate = get_interest_rate('HDFC', loan_type, cibil_band)

        results.append({
            "bank_name": "HDFC Bank",
            "amount": loan_amount_hdfc,
            "interest_rate": hdfc_rate,
            "color_theme": "#004c8f", # HDFC Blue
            "logo_text": "HDFC", 
            "details": f"Based on 55% FOIR & 20x Multiplier. {hdfc_reason}."
        })

        # --- Bank of Baroda Rules ---
        bob_eligible = True
        if cibil_score < 680:
            bob_eligible = False
            bob_reason = "Credit score below 680"
        else:
            bob_reason = "Standard eligibility criteria"

        if bob_eligible:
            eligible_emi_bob = (income * 0.45) - existing_emis
            if eligible_emi_bob < 0: eligible_emi_bob = 0
            
            loan_amount_bob = eligible_emi_bob * 18
            if loan_amount_bob < 0: loan_amount_bob = 0
        else:
            loan_amount_bob = 0

        bob_rate = get_interest_rate('BoB', loan_type, cibil_band)

        results.append({
            "bank_name": "Bank of Baroda",
            "amount": loan_amount_bob,
            "interest_rate": bob_rate,
            "color_theme": "#f26522", # BoB Orange
            "logo_text": "BoB",
            "details": f"Based on 45% FOIR & 18x Multiplier. {bob_reason}."
        })

        return render_template('results.html', results=results, income=income)

    except Exception as e:
        return f"Error: {str(e)}", 400


