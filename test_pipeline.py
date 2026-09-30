from packages.data_pipeline import DataPipeline

def test_pipeline():
    pipeline = DataPipeline()
    quotes = [
        {"flight_number": "6E-123", "departure_time": "10:00", "price": "$100.50"},
        {"flight_number": "6E 123", "departure_time": "10:00", "price": "€90"}
    ]
    # We expect normalize and validate_schema to fail since we haven't implemented them here.
    # Let's mock them or check if they exist.
