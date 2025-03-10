from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import stripe
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from fpdf import FPDF
import openai
import requests

app = Flask(__name__)

# Load environment variables from .env
load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Email Configuration
EMAIL_ADDRESS = 'cryptointelai@gmail.com'
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


### **🔹 STEP 1: Email Sending Function (Fixed)**
def send_email(to_email, report_file, report_type):
    """Send the research report via email."""
    if not os.path.exists(report_file):
        print(f"ERROR: Report file '{report_file}' not found. Email not sent.")
        return
    
    msg = EmailMessage()
    subject_type = "Free" if report_type == "free" else "Paid"
    msg['Subject'] = f'Your {subject_type} Crypto Research Report'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content(f'Thank you for requesting a {subject_type} research report! Attached is your report.')

    with open(report_file, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename='Crypto_Research_Report.pdf')
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"✅ Report sent successfully to {to_email}")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")


### **🔹 STEP 2: Fetching Market Data & News**
def fetch_crypto_data():
    """Fetch real-time market data for Bitcoin & Ethereum."""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum",
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_change": "true"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None


def fetch_crypto_news():
    """Fetch the latest cryptocurrency news."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "cryptocurrency OR bitcoin OR ethereum",
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": "your_newsapi_key_here"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        articles = response.json().get("articles", [])[:5]  # Top 5 news articles
        return "\n".join([f"- {a['title']} ({a['source']['name']}) - {a['url']}" for a in articles])
    return "No recent news found."


def fetch_expert_opinions():
    """Fetch expert insights from crypto analysts."""
    return """
    - 'Ethereum ETFs could reshape DeFi' - Vitalik Buterin
    - 'Bitcoin will surpass $100K by 2026' - Michael Saylor
    - 'Altcoins are in for a major correction' - Raoul Pal
    """  # Placeholder (Replace with API integration)


### **🔹 STEP 3: AI Research Customization & Token Increase**
def generate_research_report(query, report_type, custom_options=[]):
    """Generate an AI-powered research report with real-time news & user customization."""
    
    crypto_data = fetch_crypto_data()
    latest_news = fetch_crypto_news() if report_type in ["basic", "deep"] else "No news for free reports."
    expert_opinions = fetch_expert_opinions() if report_type == "deep" else "No expert insights in this tier."

    # Market update
    market_update = ""
    if crypto_data:
        market_update = f"""
        As of today:
        - Bitcoin (BTC) is priced at ${crypto_data['bitcoin']['usd']} with a 24h change of {crypto_data['bitcoin']['usd_24h_change']:.2f}%.
        - Ethereum (ETH) is priced at ${crypto_data['ethereum']['usd']} with a 24h change of {crypto_data['ethereum']['usd_24h_change']:.2f}%.
        """

    # Customization based on user selection
    extra_insights = ""
    if "technical_analysis" in custom_options:
        extra_insights += "\n- Provide detailed technical indicators such as RSI, MACD, and moving averages."
    if "investment_risks" in custom_options:
        extra_insights += "\n- Analyze the risks associated with investing in this crypto asset."
    if "long_term_forecast" in custom_options:
        extra_insights += "\n- Provide a long-term forecast for the next 3-5 years."

    # Adjust token usage for deep research
    token_limit = 8000 if report_type == "deep" else 3000 if report_type == "basic" else 500

    prompt = f"""
    Provide a comprehensive research report on: {query}.
    
    - Include market trends, risks, and expert insights.
    - Analyze real-time crypto market data.
    - Summarize key developments in the space.
    
    {market_update}

    **Latest Crypto News:**
    {latest_news}

    **Expert Opinions:**
    {expert_opinions}

    {extra_insights}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=token_limit,
    )

    return response["choices"][0]["message"]["content"]


### **🔹 STEP 4: Handling User Requests & Payments**
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/submit-query', methods=['POST'])
def submit_query():
    """Process user research request & determine if free or paid."""
    research_query = request.form.get("research_query")
    report_type = request.form.get("report_type", "basic")
    user_email = request.form.get("email")
    custom_options = request.form.getlist("custom_options")  # Capture selected options

    if not research_query:
        return "Error: No research query submitted", 400

    if report_type == "free":
        research_content = generate_research_report(research_query, "free", custom_options)
        report_filename = f"reports/{research_query.replace(' ', '_')}_free.pdf"
        save_report_as_pdf(research_content, report_filename)

        if user_email:
            send_email(user_email, report_filename, "free")

        return send_file(report_filename, as_attachment=True)

    return redirect(url_for('buy_report', query=research_query, report_type=report_type, custom_options=",".join(custom_options)))


@app.route('/buy-report', methods=['GET'])
def buy_report():
    research_query = request.args.get("query", "General Crypto Research")
    report_type = request.args.get("report_type", "basic")
    custom_options = request.args.get("custom_options", "").split(",")

    price_id = "price_1R0swNBi8IpwzM1aDEEPRESEARCH99" if report_type == "deep" else "price_1R0swNBi8IpwzM1aBASICREPORT29"

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='payment',
            success_url='https://yourwebsite.com/success',
            cancel_url='https://yourwebsite.com/cancel',
            metadata={"query": research_query, "report_type": report_type, "custom_options": ",".join(custom_options)}
        )
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        return jsonify(error=str(e)), 500


### **🔹 STEP 5: Generating the PDF Reports**
def save_report_as_pdf(content, filename):
    """Convert text content into a PDF report and ensure directory exists."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    safe_content = content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(190, 10, safe_content)
    pdf.output(filename, 'F')


if __name__ == '__main__':
    app.run(debug=True)
