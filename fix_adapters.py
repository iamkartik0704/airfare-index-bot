import os
import glob
import re

base_dir = "/home/logan78/Desktop/airfare-index-bot/packages/scraping/sources"

adapters = glob.glob(os.path.join(base_dir, "**", "adapter.py"), recursive=True)

parse_method = """    def build_requests(self, context):
        return [Request(url=f"https://{self.metadata()['name']}.com/search")]

    def parse(self, response: Response):
        quotes = []
        if response.body:
            try:
                elements = response.css(".flight-card")
                for el in elements:
                    base_fare = el.css_first(".base-fare").text() if el.css_first(".base-fare") else "0"
                    total_fare = el.css_first(".total-fare").text() if el.css_first(".total-fare") else "0"
                    quotes.append({
                        "carrier": self.metadata()["name"],
                        "base_fare": float(base_fare.replace('₹', '').replace(',', '')),
                        "total_fare": float(total_fare.replace('₹', '').replace(',', '')),
                    })
            except ImportError:
                pass
        return quotes"""

for adapter in adapters:
    with open(adapter, "r") as f:
        content = f.read()
        
    # Fix the indentation
    content = re.sub(
        r'        def build_requests\(self, context\):.*?def health_check',
        parse_method + "\n\n    def health_check",
        content,
        flags=re.DOTALL
    )
    
    with open(adapter, "w") as f:
        f.write(content)

print("Fixed adapters.")
