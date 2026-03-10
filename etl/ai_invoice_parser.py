from openai import OpenAI
import json

client = OpenAI()

def parse_invoice_with_ai(text):

    prompt = f"""
Extract structured invoice data from the text below.

Return ONLY valid JSON in this format:

{{
  "invoice_number": "",
  "vendor_name": "",
  "date": "",
  "total_amount": "",
  "items": [
    {{
      "name": "",
      "quantity": "",
      "price": ""
    }}
  ]
}}

Invoice text:
{text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    output = response.output_text

    try:
        data = json.loads(output)
    except:
        data = {}

    return data
