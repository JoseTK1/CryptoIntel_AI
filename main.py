from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import stripe
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from fpdf import FPDF
import openai
import requests

app = FastAPI()

# ✅ Enable CORS for Frontend Communication
origins = [
    "http://localhost:3000",  # Local development
    "https://your-frontend.vercel.app",  # Deployed frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load environment variables
load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = 'cryptointelai@gmail.com'
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# ✅ Stripe Product IDs (Replace with correct IDs)
PRODUCT_IDS = {
    "deep": "prod_Rv4UrWt9lFcXxz",  # Deep Research
    "basic": "prod_Rv4SPDlhX6Ccbu",  # Advanced Research
}

# ✅ Get Price IDs dynamically from Stripe
def get_price_id(product_id):
    try:
        prices = stripe.Price.list(product=product_id)
        if prices and prices["data"]:
            return prices["data"][0]["id"]  # Get first price ID
    except Exception as e:
        print(f"❌ Stripe Error: {e}")
    return None  # Return None if no price found

# ✅ Email Sending Function
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

# ✅ AI Research Report Generation
def generate_research_report(query: str, report_type: str) -> str:
    """Generate an AI-powered research report based on user query."""
    
    prompt = f"Provide a {'deep' if report_type == 'deep' else 'brief'} research report on {query}. Include market trends, expert insights, technical analysis, investment risks, and future forecasts."

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=2500 if report_type == "deep" else 1000,
    )

    return response["choices"][0]["message"]["content"]

# ✅ Save Report as PDF
def save_report_as_pdf(content: str, filename: str):
    """Convert text content into a PDF report."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(190, 10, content)
    pdf.output(filename)

# ✅ Homepage Route (Health Check)
@app.get("/")
async def home():
    """Homepage"""
    return {"message": "CryptoIntel AI is live! Use the API to generate research reports."}

# ✅ Process User Query & Redirect to Stripe (Updated for JSON Data)
@app.post("/submit-query")
async def submit_query(request: Request):
    """Process user's research request and redirect to Stripe Checkout."""
    try:
        data = await request.json()
        research_query = data.get("research_query")
        report_type = data.get("report_type", "basic")

        if not research_query:
            raise HTTPException(status_code=400, detail="No research query submitted")

        return RedirectResponse(url=f"/buy-report?query={research_query}&report_type={report_type}", status_code=303)
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ✅ Stripe Payment Checkout (Updated with Dynamic Price IDs)
@app.get("/buy-report")
async def buy_report(query: str, report_type: str):
    """Initiate Stripe checkout session."""
    try:
        # Get the correct price ID dynamically
        product_id = PRODUCT_IDS.get(report_type, "basic")  # Default to basic if invalid type
        price_id = get_price_id(product_id)

        if not price_id:
            raise HTTPException(status_code=500, detail="Stripe Price ID not found")

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='payment',
            success_url="https://your-frontend.vercel.app/success",
            cancel_url="https://your-frontend.vercel.app/cancel",
            metadata={"query": query, "report_type": report_type}
        )
        return JSONResponse(content={"url": checkout_session.url})

    except Exception as e:
        print("❌ ERROR in /buy-report:", str(e))  # ✅ Log error
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ✅ Success Page
@app.get("/success")
async def success():
    """Show success message after payment."""
    return {"message": "Payment successful! Your research report will be emailed shortly."}

# ✅ Stripe Webhook Handler
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

# ✅ Run the FastAPI App
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
