from packages.index_engine.engine import IndexEngine

def test_engine():
    engine = IndexEngine({"DEL-BOM": 5000, "BOM-BLR": 4000})
    weights = {"DEL-BOM": 0.6, "BOM-BLR": 0.4}
    
    current_data = {"DEL-BOM": 6000, "BOM-BLR": 4400}
    index = engine.calculate_laspeyres_index(current_data, weights)
    expected_index = (0.6 * (6000/5000) + 0.4 * (4400/4000)) * 100
    assert abs(index - expected_index) < 1e-6, f"Expected {expected_index}, got {index}"
    
    series = [100, None, 120, None, None, 130]
    imputed = engine.impute_locf(series)
    assert imputed == [100, 100, 120, 120, 120, 130], f"Got {imputed}"
    
    print("Engine tests passed!")

if __name__ == "__main__":
    test_engine()
