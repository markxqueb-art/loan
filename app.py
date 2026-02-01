from flask import Flask, render_template, request

app = Flask(__name__)

# Currency formatter
def format_currency(amount):
    return "₹{:,.0f}".format(amount)

app.jinja_env.filters['currency'] = format_currency


@app.route("/")
def home():
    return render_template("index.html")


@app.route('/calculate', methods=['POST'])
def calculate():
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

        def get_interest_rate(bank, loan_type):
            if bank == 'HDFC':
                return "8.00% - 9.50%" if loan_type == "Home" else "10.00% - 18.00%"
            elif bank == 'BoB':
                return "8.50% - 9.80%" if loan_type == "Home" else "12.00% - 20.00%"
            return "N/A"

        # HDFC Calculation
        if cibil_score >= 700:
            eligible_emi = (income * 0.55) - existing_emis
            loan_amount_hdfc = max(eligible_emi, 0) * 20
        else:
            loan_amount_hdfc = 0

        results.append({
            "bank_name": "HDFC Bank",
            "amount": loan_amount_hdfc,
            "interest_rate": get_interest_rate('HDFC', loan_type)
        })

        # Bank of Baroda Calculation
        if cibil_score >= 680:
            eligible_emi = (income * 0.45) - existing_emis
            loan_amount_bob = max(eligible_emi, 0) * 18
        else:
            loan_amount_bob = 0

        results.append({
            "bank_name": "Bank of Baroda",
            "amount": loan_amount_bob,
            "interest_rate": get_interest_rate('BoB', loan_type)
        })

        return render_template('results.html', results=results)

    except Exception as e:
        return f"Error: {str(e)}", 400


# IMPORTANT: No app.run()
