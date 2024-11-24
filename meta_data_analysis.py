import json
from typing import Dict, Any
from collections import defaultdict
from pprint import pprint

def extract_fields(obj: Any, prefix: str = '') -> set:
    """Recursively extract all fields from nested JSON object"""
    fields = set()
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{prefix}.{key}" if prefix else key
            fields.add(current_path)
            fields.update(extract_fields(value, current_path))
    elif isinstance(obj, list) and obj:
        # Take first element as sample for list structures
        fields.update(extract_fields(obj[0], prefix + '[0]'))
    
    return fields

def analyze_response_structure(response_file: str, airline: str) -> Dict[str, Any]:
    """Analyze the structure and fields of an airline's response"""
    
    with open(response_file, 'r') as f:
        response = json.load(f)
    
    analysis = {
        "airline": airline,
        "all_fields": extract_fields(response),
        "critical_fields_present": defaultdict(bool),
        "response_metadata": {
            "total_offers": 0,
            "unique_field_count": 0
        }
    }
    
    # Define critical fields by airline
    critical_fields = {
        "LATAM": {
            "flight_number": "availabilityResponseSO.availabilityInfoList[0].segmentAvailabilityInfoList[0].fltInfoSO.carrierNumber",
            "departure_time": "availabilityResponseSO.availabilityInfoList[0].segmentAvailabilityInfoList[0].standardDeparturedTime",
            "arrival_time": "availabilityResponseSO.availabilityInfoList[0].segmentAvailabilityInfoList[0].standardTimeOfArrival",
            "rate": "availabilityResponseSO.availabilityInfoList[0].prdRateInfo.totalFreightCharge",
            "operation_type": "availabilityResponseSO.availabilityInfoList[0].segmentAvailabilityInfoList[0].fltInfoSO.operationType"
        },
        "Qatar": {
            "flight_number": "availabilityResponseSOs[0].availabilityResponseSOs[0].flightItineraries[0].carrierNumber",
            "departure_time": "availabilityResponseSOs[0].availabilityResponseSOs[0].flightItineraries[0].scheduledDepartureTime",
            "arrival_time": "availabilityResponseSOs[0].availabilityResponseSOs[0].flightItineraries[0].scheduledArrivalTime",
            "rate": "availabilityResponseSOs[0].availabilityResponseSOs[0].rateDetails.totalAmount",
            "operation_type": "availabilityResponseSOs[0].availabilityResponseSOs[0].flightItineraries[0].operationType"
        },
        "TK": {
            "flight_number": "flightList[0].flightNumber",
            "departure_time": "flightList[0].departureTime",
            "arrival_time": "flightList[0].arrivalTime",
            "rate": "rateInfo.totalAmount",
            "operation_type": "flightList[0].operationType"
        }
    }
    
    # Check presence of critical fields
    for field_name, field_path in critical_fields.get(airline, {}).items():
        analysis["critical_fields_present"][field_name] = any(
            field_path in field for field in analysis["all_fields"]
        )
    
    # Count offers based on airline-specific structure
    if airline == "LATAM":
        if "availabilityResponseSO" in response:
            analysis["response_metadata"]["total_offers"] = len(
                response["availabilityResponseSO"].get("availabilityInfoList", [])
            )
    elif airline == "Qatar":
        total = 0
        for date_group in response.get("availabilityResponseSOs", []):
            if "availabilityResponseSOs" in date_group:
                total += len(date_group["availabilityResponseSOs"])
        analysis["response_metadata"]["total_offers"] = total
    elif airline == "TK":
        analysis["response_metadata"]["total_offers"] = len(
            response.get("flightList", [])
        )
    
    analysis["response_metadata"]["unique_field_count"] = len(analysis["all_fields"])
    
    # Export fields to text file
    export_fields_to_file(analysis["all_fields"], airline)
    
    return analysis

def export_fields_to_file(fields: set, airline: str):
    """Export all fields to a text file organized by airline"""
    filename = f"fields_{airline}.txt"
    with open(filename, 'w') as f:
        f.write(f"All fields for {airline}:\n")
        f.write("=" * 50 + "\n\n")
        for field in sorted(fields):
            f.write(f"{field}\n")

def compare_airline_responses(analyses: list) -> Dict[str, Any]:
    """Compare response structures across airlines"""
    comparison = {
        "common_fields": set.intersection(*[set(a["all_fields"]) for a in analyses]),
        "unique_fields_by_airline": {},
        "field_coverage": defaultdict(list),
        "critical_fields_comparison": defaultdict(dict)
    }
    
    # Analyze unique fields per airline
    for analysis in analyses:
        airline = analysis["airline"]
        comparison["unique_fields_by_airline"][airline] = analysis["all_fields"]
        
        # Compare critical fields presence
        for field, present in analysis["critical_fields_present"].items():
            comparison["critical_fields_comparison"][field][airline] = present
    
    return comparison

# Run analyses
airlines_analysis = []
for airline, response_file in [
    ("LATAM", "cargo-offers/LATAM Offer Response Example.json"),
    ("Qatar", "cargo-offers/Qatar Offer Response Example.json"),
    ("TK", "cargo-offers/TK Offer Response Example.json")
]:
    try:
        analysis = analyze_response_structure(response_file, airline)
        airlines_analysis.append(analysis)
        
        print(f"\n{airline} Response Analysis:")
        print(f"Total number of offers: {analysis['response_metadata']['total_offers']}")
        print(f"Unique fields count: {analysis['response_metadata']['unique_field_count']}")
        print("\nCritical fields presence:")
        for field, present in analysis["critical_fields_present"].items():
            print(f"- {field}: {'✓' if present else '✗'}")
            
    except Exception as e:
        print(f"Error analyzing {airline} response: {e}")

# Compare responses across airlines
comparison = compare_airline_responses(airlines_analysis)

print("\nCross-Airline Comparison:")
print("\nCritical Fields Coverage:")
for field, coverage in comparison["critical_fields_comparison"].items():
    print(f"\n{field}:")
    for airline, present in coverage.items():
        print(f"  {airline}: {'✓' if present else '✗'}")

print("\nField Counts by Airline:")
for airline, fields in comparison["unique_fields_by_airline"].items():
    print(f"{airline}: {len(fields)} fields")