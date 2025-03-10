from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
import stripe
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from fpdf import FPDF
import openai
import requests

app = FastAPI()

# Load environment variables
load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = 'cryptointelai@gmail.com'
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

### **🔹 Email Sending Function (Fixed)**
def send_email(to_email: str, report_file: str):
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
        print(f"✅ Report sent successfully to {to_email}")


### **🔹 AI Research Report Generation**
def generate_research_report(query: str, report_type: str) -> str:
    """Generate an AI-powered research report based on user query."""
    
    prompt = f"Provide a {'deep' if report_type == 'deep' else 'brief'} research report on {query}. Include market trends, expert insights, technical analysis, investment risks, and future forecasts."

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=2500 if report_type == "deep" else 1000,
    )

    return response["choices"][0]["message"]["content"]


### **🔹 Save Report as PDF**
def save_report_as_pdf(content: str, filename: str):
    """Convert text content into a PDF report."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(190, 10, content)
    pdf.output(filename)


### **🔹 Homepage Route**
@app.get("/")
async def home():
    """Homepage"""
    return {"message": "CryptoIntel AI is live! Use the API to generate research reports."}


### **🔹 Process User Query & Redirect to Stripe**
@app.post("/submit-query")
async def submit_query(research_query: str = Form(...), report_type: str = Form("basic")):
    """Process user's research request and redirect to Stripe Checkout."""
    if not research_query:
        raise HTTPException(status_code=400, detail="No research query submitted")
    
    return RedirectResponse(url=f"/buy-report?query={research_query}&report_type={report_type}", status_code=303)


### **🔹 Stripe Payment Checkout**
@app.get("/buy-report")
async def buy_report(query: str, report_type: str):
    """Initiate Stripe checkout session."""
    price_id = "price_1R0swNBi8IpwzM1aDEEPRESEARCH99" if report_type == "deep" else "price_1R0swNBi8IpwzM1aBASICREPORT29"

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='payment',
            success_url='https://yourwebsite.com/success',
            cancel_url='https://yourwebsite.com/cancel',
            metadata={"query": query, "report_type": report_type}
        )
        return JSONResponse(content={"url": checkout_session.url})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


### **🔹 Success Page**
@app.get("/success")
async def success():
    """Show success message after payment."""
    return {"message": "Payment successful! Your research report will be emailed shortly."}


### **🔹 Stripe Webhook Handler**
@app.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events and generate the research report after payment."""
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid payload or signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email", session.get("customer_details", {}).get("email"))
        research_query = session["metadata"].get("query", "General Crypto Research")
        report_type = session["metadata"].get("report_type", "basic")

        if customer_email:
            # Generate AI Research Report
            research_content = generate_research_report(research_query, report_type)

            # Convert to PDF
            report_filename = f"reports/{research_query.replace(' ', '_')}.pdf"
            save_report_as_pdf(research_content, report_filename)

            # Send Report via Email
            send_email(customer_email, report_filename)

    return JSONResponse(content={}, status_code=200)  # Stripe requires 200 OK


### **🔹 Run the FastAPI App**
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
