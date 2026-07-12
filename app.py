from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
import os
import json
import re

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-3-flash-preview")

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
Extract invoice information.

Return ONLY valid JSON.

Return exactly:

{{
"invoice_no": null,
"date": null,
"vendor": null,
"amount": null,
"tax": null,
"currency": null
}}

Rules:

- amount = subtotal BEFORE tax.
- If only Total and Tax exist, compute amount = Total - Tax.
- Convert date to YYYY-MM-DD.
- Currency must be INR/USD/EUR/GBP.
- No markdown.
- No explanation.

Invoice:

{req.invoice_text}
"""

    response = model.generate_content(prompt)

    text = response.text.strip()

    text = text.replace("```json", "").replace("```", "").strip()

    data = json.loads(text)

    invoice = req.invoice_text

    # -----------------------------
    # Fallback amount
    # -----------------------------

    if data.get("amount") is None:

        labels = [
            "Subtotal",
            "Sub Total",
            "Amount Before Tax",
            "Taxable Amount",
            "Taxable Value",
            "Assessable Value",
            "Net Amount",
            "Net Value",
            "Base Amount",
            "Pre Tax Amount",
            "Basic Amount",
            "Invoice Amount"
        ]

        for label in labels:

            m = re.search(
                rf"{label}\s*[:\-]?\s*(?:Rs\.?|₹|USD|EUR|GBP|INR)?\s*([0-9,]+(?:\.\d+)?)",
                invoice,
                re.IGNORECASE,
            )

            if m:
                data["amount"] = float(m.group(1).replace(",", ""))
                break

    # -----------------------------
    # Fallback tax
    # -----------------------------

    if data.get("tax") is None:

        m = re.search(
            r"(GST|CGST|SGST|IGST|VAT|Sales Tax).*?([0-9,]+(?:\.\d+)?)",
            invoice,
            re.IGNORECASE,
        )

        if m:
            data["tax"] = float(m.group(2).replace(",", ""))

    # -----------------------------
    # Compute amount = total - tax
    # -----------------------------

    if data.get("amount") is None and data.get("tax") is not None:

        m = re.search(
            r"(Grand Total|Invoice Total|Total)\s*[:\-]?\s*(?:Rs\.?|₹|USD|EUR|GBP|INR)?\s*([0-9,]+(?:\.\d+)?)",
            invoice,
            re.IGNORECASE,
        )

        if m:

            total = float(m.group(2).replace(",", ""))

            data["amount"] = round(total - float(data["tax"]), 2)

    return data