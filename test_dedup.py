from packages.data_pipeline.deduplication.dedup import fuzzy_dedup, exact_match_dedup

def test_exact():
    flights = [{"flight_number": "6E-123", "departure_time": "10:00"}, {"flight_number": "6E-123", "departure_time": "10:00"}]
    assert len(exact_match_dedup(flights)) == 1

def test_fuzzy():
    flights = [{"flight_number": "6E-123", "departure_time": "10:00"}, {"flight_number": "6E 123", "departure_time": "10:00"}]
    assert len(fuzzy_dedup(flights)) == 1

if __name__ == "__main__":
    test_exact()
    test_fuzzy()
    print("All tests passed")
