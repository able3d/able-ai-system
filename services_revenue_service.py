import re

def extract_items(text):

    items = []

    pattern = r"([A-Za-z ]+)\s+(\d+)\s+([\d\.]+)"

    matches = re.findall(pattern, text)

    for match in matches:

        item = {
            "item_name": match[0].strip(),
            "quantity": int(match[1]),
            "price": float(match[2])
        }

        items.append(item)

    return items

def calculate_revenue(items):

    total_revenue = 0

    for item in items:
        total_revenue += item["quantity"] * item["price"]

    return total_revenue
