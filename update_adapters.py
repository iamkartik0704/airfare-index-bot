import os
import glob
import re

base_dir = "/home/logan78/Desktop/airfare-index-bot/packages/scraping/sources"

adapters = glob.glob(os.path.join(base_dir, "**", "adapter.py"), recursive=True)

import_stmt = """from packages.data_pipeline.models.db import NormalizedQuote
from packages.scraping.core.fetchers.base import Request, Response
from datetime import datetime, timedelta

"""

parse_method = """    def build_requests(self, context):
        return [Request(url=f"https://{self.metadata()['name']}.com/search")]

    def parse(self, response: Response):
        quotes = []
        if response.body:
            elements = response.css(".flight-card")
            for el in elements:
                base_fare = el.css_first(".base-fare").text() if el.css_first(".base-fare") else "0"
                total_fare = el.css_first(".total-fare").text() if el.css_first(".total-fare") else "0"
                quotes.append({
                    "carrier": self.metadata()["name"],
                    "base_fare": float(base_fare.replace('₹', '').replace(',', '')),
                    "total_fare": float(total_fare.replace('₹', '').replace(',', '')),
                })
        return quotes"""

for adapter in adapters:
    with open(adapter, "r") as f:
        content = f.read()
        
    if "from packages.data_pipeline.models.db import NormalizedQuote" not in content:
        content = import_stmt + content
        
    # Replace build_requests and parse
    content = re.sub(
        r'def build_requests\(self, context\):.*?def health_check',
        parse_method + "\n\n    def health_check",
        content,
        flags=re.DOTALL
    )
    
    with open(adapter, "w") as f:
        f.write(content)

print("Updated adapters.")
