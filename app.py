from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

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


def parse_amount(x):
    if not x:
        return None
    x = x.replace(",", "")
    return float(x)


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    invoice_no = None
    date = None
    vendor = None
    amount = None
    tax = None
    currency = None

    # Invoice Number
    patterns = [
        r"Invoice\s*No[:\s]*([A-Za-z0-9\-\/]+)",
        r"Invoice\s*#[:\s]*([A-Za-z0-9\-\/]+)",
        r"Ref[:\s]*([A-Za-z0-9\-\/]+)"
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            invoice_no = m.group(1).strip()
            break

    # Vendor
    patterns = [
        r"Vendor[:\s]*(.+)",
        r"Supplier[:\s]*(.+)",
        r"From[:\s]*(.+)"
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            vendor = m.group(1).strip()
            break

    # Date
    patterns = [
        r"Date[:\s]*(.+)",
        r"Issued[:\s]*(.+)"
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                date = parser.parse(m.group(1)).date().isoformat()
                break
            except:
                pass

    # Amount (Subtotal)
    m = re.search(
        r"Subtotal.*?([0-9,]+\.[0-9]{2})",
        text,
        re.I
    )

    if m:
        amount = parse_amount(m.group(1))

    # Tax
    m = re.search(
        r"(GST|CGST|SGST|IGST).*?([0-9,]+\.[0-9]{2})",
        text,
        re.I
    )

    if m:
        tax = parse_amount(m.group(2))

    # Currency
    m = re.search(r"Currency[:\s]*([A-Z]{3})", text)

    if m:
        currency = m.group(1)
    elif "Rs" in text or "₹" in text:
        currency = "INR"

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency
    }