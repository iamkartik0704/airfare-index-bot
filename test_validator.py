from packages.data_pipeline.validation.validator import Validator
v = Validator()
quotes = [{'total_fare': 100}, {'total_fare': 100}, {'total_fare': 100}, {'total_fare': 100}, {'total_fare': 1000}]
valid, out = v.detect_outliers(quotes)
print(valid)
print(out)
