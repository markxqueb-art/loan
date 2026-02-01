from flask import Flask, render_template, request, redirect, session
import random
import time

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

# In-memory OTP store
otp_store = {}

def generate_otp():
    return random.randint(1000, 9999)

# Currency filter
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
        "expiry": expiry
    }

    # ONLY print to console (Vercel logs)
    print(f"SIMULATED OTP for {mobile}: {otp}")

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
        return redirect("/")
    else:
        return "Invalid OTP"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route('/calculate', methods=['POST'])
def calculate():
    if "user" not in session:
        return redirect("/login")

    try:
        income = float(request.form.get('income'))
        cibil_band = request.form.get('cibil_band')
        existing_emis = float(request.form.get('existing_emis'))
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
                    return "8.00% - 9.50%"
                else:
                    return "10.00% - 18.00%"
            elif bank == 'BoB':
                if loan_type == 'Home':
                    return "8.50% - 9.80%"
                else:
                    return "12.00% - 20.00%"
            return "N/A"

        # HDFC
        if cibil_score >= 700:
            eligible_emi = (income * 0.55) - existing_emis
            loan_amount = max(eligible_emi, 0) * 20
        else:
            loan_amount = 0

        results.append({
            "bank_name": "HDFC Bank",
            "amount": loan_amount,
            "interest_rate": get_interest_rate('HDFC', loan_type, cibil_band)
        })

        # BoB
        if cibil_score >= 680:
            eligible_emi = (income * 0.45) - existing_emis
            loan_amount = max(eligible_emi, 0) * 18
        else:
            loan_amount = 0

        results.append({
            "bank_name": "Bank of Baroda",
            "amount": loan_amount,
            "interest_rate": get_interest_rate('BoB', loan_type, cibil_band)
        })

        return render_template('results.html', results=results)

    except Exception as e:
        return f"Error: {str(e)}", 400
