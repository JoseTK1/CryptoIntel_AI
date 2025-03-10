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

# Load environment variables (if running locally, not needed on Render)
load_dotenv()

# Securely fetch API keys from environment variables
stripe.api_key = os.getenv("STRIPE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")  # ✅ NewsAPI key added

# Email Configuration
EMAIL_ADDRESS = 'cryptointelai@gmail.com'
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


### **🔹 Email Sending Function (Fixed)**
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


### **🔹 Fetching Market Data & News**
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
    """Fetch the latest cryptocurrency news using NewsAPI."""
    if not news_api_key:
        return "⚠️ No NewsAPI key found. Please add it to the environment variables."

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "cryptocurrency OR bitcoin OR ethereum",
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": news_api_key  # ✅ Uses secure API key
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


### **🔹 AI Research Customization & Token Increase**
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


### **🔹 Generate & Deliver Reports**
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


### **🔹 Run the Flask App**
if __name__ == '__main__':
    app.run(debug=True)
