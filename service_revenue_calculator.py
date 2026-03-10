import re

def extract_items(text):
    
    items = []
    
    lines = text.split("\n")
    
    for line in lines:
        
        # Example pattern: Item 2 x 5.99
        match = re.search(r'(.+?)\s+(\d+)\s*x\s*(\d+\.\d+)', line)
        
        if match:
            
            name = match.group(1)
            quantity = int(match.group(2))
            price = float(match.group(3))
            
            total = quantity * price
            
            items.append({
                "name": name,
                "quantity": quantity,
                "price": price,
                "total": total
            })
    
    return items

def calculate_revenue(items):

    total_revenue = 0

    for item in items:
        total_revenue += item["total"]

    return total_revenue
