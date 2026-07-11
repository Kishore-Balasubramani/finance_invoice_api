from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
import os
import json

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    invoice_text: str


@app.post("/extract")
async def extract(req: InvoiceRequest):

    prompt = f"""
You are an invoice extraction engine.

Extract the invoice into EXACTLY this JSON schema.

{{
  "invoice_no": null,
  "date": null,
  "vendor": null,
  "amount": null,
  "tax": null,
  "currency": null
}}

Rules:

1. Return ONLY JSON.
2. No markdown.
3. No explanation.
4. date must be YYYY-MM-DD.
5. amount is ALWAYS the amount BEFORE TAX.

If the invoice uses ANY of these labels:

Subtotal
Sub Total
Amount Before Tax
Taxable Amount
Taxable Value
Assessable Value
Net Amount
Net Value
Base Amount
Pre Tax Amount

use that value as amount.

If only Total and Tax are available then compute

amount = total - tax

Tax may be called:

GST
CGST
SGST
IGST
VAT
Sales Tax

Currency should be one of:

INR
USD
EUR
GBP

Invoice text:

{req.invoice_text}
"""

    response = model.generate_content(prompt)

    text = response.text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)