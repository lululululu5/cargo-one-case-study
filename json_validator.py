import json

# Test Qatar files
def validate_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        print(f"✓ {filepath} is valid JSON")
    except json.JSONDecodeError as e:
        print(f"✗ {filepath} has invalid JSON at position {e.pos}")
        print(f"  Error: {str(e)}")

# Test both Qatar files
validate_json_file('cargo-requests/Qatar Offer Request Example.json')
validate_json_file('cargo-offers/Qatar Offer Response Example.json')