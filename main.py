from flask import Flask, render_template, request, jsonify, redirect, url_for
import stripe
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from fpdf import FPDF
import openai  # Ensure you have access to OpenAI API

app = Flask(__name__)

# Load environment variables from .env
load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Email Configuration
EMAIL_ADDRESS = 'cryptointelai@gmail.com'
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")


def send_email(to_email, report_file):
    """Send the research report via email."""
    if not os.path.exists(report_file):
        print(f"ERROR: Report file '{report_file}' not found. Email not sent.")
        return
    
    msg = EmailMessage()
    msg['Subject'] = 'Your Custom Crypto Research Report'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content('Thank you for your purchase! Attached is your custom research report.')
    
    with open(report_file, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename='Crypto_Research_Report.pdf')
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


def generate_research_report(query, report_type):
    """Generate an AI-powered research report based on user query."""
    
    if report_type == "deep":
        prompt = f"Provide a deep research report on {query}. Include market trends, expert insights, technical analysis, investment risks, and future forecasts."
    else:
        prompt = f"Provide a brief summary of {query} including key trends, risks, and opportunities in crypto."

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=2500 if report_type == "deep" else 1000,
    )

    return response["choices"][0]["message"]["content"]


def save_report_as_pdf(content, filename):
    """Convert text content into a PDF report."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(190, 10, content)
    pdf.output(filename)


@app.route('/')
def home():
    """Render the homepage with research query form."""
    return render_template('index.html')


@app.route('/submit-query', methods=['POST'])
def submit_query():
    """Process user's research request and redirect to Stripe Checkout."""
    research_query = request.form.get("research_query")
    report_type = request.form.get("report_type", "basic")  # Default to basic

    if not research_query:
        return "Error: No research query submitted", 400

    # Redirect to payment
    return redirect(url_for('buy_report', query=research_query, report_type=report_type))


@app.route('/buy-report', methods=['GET'])
def buy_report():
    """Initiate Stripe checkout based on report type selection."""
    research_query = request.args.get("query", "General Crypto Research")
    report_type = request.args.get("report_type", "basic")

    # Set price based on report type
    if report_type == "deep":
        price_id = "price_1R0swNBi8IpwzM1aDEEPRESEARCH99"  # Replace with actual Stripe price ID
    else:
        price_id = "price_1R0swNBi8IpwzM1aBASICREPORT29"  # Replace with actual Stripe price ID

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://yourwebsite.com/success',
            cancel_url='https://yourwebsite.com/cancel',
            metadata={"query": research_query, "report_type": report_type}
        )
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/success')
def success():
    """Show success message after payment."""
    return 'Payment successful! Your custom research report will be emailed shortly.'


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events and generate the research report after payment."""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_email', None)
        if not customer_email:
            customer_email = session.get('customer_details', {}).get('email', None)

        research_query = session.get('metadata', {}).get('query', "General Crypto Research")
        report_type = session.get('metadata', {}).get('report_type', "basic")

        if customer_email:
            # Generate AI Research Report
            research_content = generate_research_report(research_query, report_type)

            # Convert to PDF
            report_filename = f"reports/{research_query.replace(' ', '_')}.pdf"
            save_report_as_pdf(research_content, report_filename)

            # Send Report via Email
            send_email(customer_email, report_filename)

    return '', 200  # Return 200 OK so Stripe knows the webhook was received


if __name__ == '__main__':
    app.run(debug=True)
