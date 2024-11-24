import json
from typing import Dict, Any
from pprint import pprint
from collections import defaultdict

def analyze_request_response_pair(request_file: str, response_file: str, airline: str) -> Dict[str, Any]:
    """Analyze a request-response pair and return key insights"""
    
    with open(request_file, 'r') as f:
        request = json.load(f)
    
    with open(response_file, 'r') as f:
        response = json.load(f)
        
    analysis = {
        "airline": airline,
        "request": {
            "key_fields": list(request.keys()),
            "shipment_details": {},
            "special_handling_codes": set(),
            "commodity_info": {}
        },
        "response": {
            "key_fields": list(response.keys()),
            "number_of_offers": 0,
            "booking_constraints": set(),
            "operation_types": set(),
            "rate_types": set()
        }
    }

    # Extract route information based on airline-specific request structure
    if airline == "LATAM":
        analysis["request"]["route"] = f"{request.get('origin', 'N/A')} -> {request.get('destination', 'N/A')}"
        if "productCommoditySO" in request:
            analysis["request"]["special_handling_codes"].update([
                request["productCommoditySO"].get("shc1"),
                request["productCommoditySO"].get("shc2"),
                request["productCommoditySO"].get("shc3")
            ])
    elif airline == "Qatar":
        analysis["request"]["route"] = f"{request.get('origin', 'N/A')} -> {request.get('destination', 'N/A')}"
        if "productDetails" in request:
            analysis["request"]["special_handling_codes"].update(
                request["productDetails"].get("specialHandlingCodes", [])
            )
    elif airline == "TK":
        flight_info = request.get("ListFlightInformationRequest", {}).get("flightAvailabilityFilterType", {})
        analysis["request"]["route"] = f"{flight_info.get('origin', 'N/A')} -> {flight_info.get('destination', 'N/A')}"
        analysis["request"]["special_handling_codes"].add(flight_info.get("sccDetails"))

    # Analyze responses based on airline-specific structure
    if airline == "LATAM":
        if "availabilityResponseSO" in response:
            offers = response["availabilityResponseSO"]["availabilityInfoList"]
            analysis["response"]["number_of_offers"] = len(offers)
            
            for offer in offers:
                if "segmentAvailabilityInfoList" in offer:
                    for segment in offer["segmentAvailabilityInfoList"]:
                        if "fltInfoSO" in segment:
                            analysis["response"]["operation_types"].add(
                                segment["fltInfoSO"].get("operationType")
                            )
                
                if offer.get("prdRateInfo"):
                    rate_info = offer["prdRateInfo"]
                    analysis["response"]["rate_types"].add(rate_info.get("rateType"))
                    analysis["response"]["booking_constraints"].add(
                        f"Rate Type: {rate_info.get('rateType')}, "
                        f"Profitability: {rate_info.get('profitability')}"
                    )
    
    elif airline == "Qatar":
        total_offers = 0
        for date_group in response.get("availabilityResponseSOs", []):
            if "availabilityResponseSOs" in date_group:
                offers = date_group["availabilityResponseSOs"]
                total_offers += len(offers)
                
                for offer in offers:
                    if "flightItineraries" in offer:
                        for flight in offer["flightItineraries"]:
                            analysis["response"]["operation_types"].add(
                                flight.get("operationType")
                            )
                    
                    if "rateDetails" in offer:
                        analysis["response"]["rate_types"].add(
                            offer["rateDetails"].get("rateType")
                        )
                    
                    if "businessErrorSOs" in offer:
                        for error in offer["businessErrorSOs"]:
                            analysis["response"]["booking_constraints"].add(
                                f"Validation: {error.get('validationName')}, "
                                f"Status: {error.get('status')}"
                            )
        
        analysis["response"]["number_of_offers"] = total_offers

    elif airline == "TK":
        if "ListFlightInformationResponse" in response:
            offers = response["ListFlightInformationResponse"].get("flightList", [])
            analysis["response"]["number_of_offers"] = len(offers)
            
            for offer in offers:
                if "operationType" in offer:
                    analysis["response"]["operation_types"].add(offer["operationType"])
                
                if "rateType" in offer:
                    analysis["response"]["rate_types"].add(offer["rateType"])
                
                if "bookingConstraints" in offer:
                    for constraint in offer["bookingConstraints"]:
                        analysis["response"]["booking_constraints"].add(
                            f"Constraint: {constraint.get('type')}, "
                            f"Status: {constraint.get('status')}"
                        )

    # Convert sets to lists for JSON serialization
    analysis["request"]["special_handling_codes"] = list(filter(None, analysis["request"]["special_handling_codes"]))
    analysis["response"]["booking_constraints"] = list(analysis["response"]["booking_constraints"])
    analysis["response"]["operation_types"] = list(analysis["response"]["operation_types"])
    analysis["response"]["rate_types"] = list(analysis["response"]["rate_types"])
    
    return analysis

def generate_bookability_guidelines(analyses):
    """Generate guidelines for checking bookability based on analyzed patterns"""
    guidelines = {
        "general_checks": [
            "Verify operation type matches request requirements",
            "Check rate type compatibility",
            "Validate special handling codes are supported"
        ],
        "airline_specific": defaultdict(list)
    }
    
    for analysis in analyses:
        airline = analysis["airline"]
        
        if airline == "LATAM":
            if "Pass" in str(analysis["response"]["booking_constraints"]):
                guidelines["airline_specific"][airline].append(
                    "Check profitability indicator - offers marked as 'Fail' may not be bookable"
                )
            if analysis["response"]["rate_types"]:
                guidelines["airline_specific"][airline].append(
                    f"Validate rate types: {', '.join(analysis['response']['rate_types'])}"
                )
                
        elif airline == "Qatar":
            if any("Embargo" in str(constraint) for constraint in analysis["response"]["booking_constraints"]):
                guidelines["airline_specific"][airline].append(
                    "Check for embargo restrictions in businessErrorSOs"
                )
            guidelines["airline_specific"][airline].append(
                "Verify all segments in multi-leg flights are bookable"
            )

        elif airline == "TK":
            if analysis["response"]["booking_constraints"]:
                guidelines["airline_specific"][airline].append(
                    "Review booking constraints for capacity and operational restrictions"
                )
            if analysis["response"]["rate_types"]:
                guidelines["airline_specific"][airline].append(
                    f"Verify rate types: {', '.join(analysis['response']['rate_types'])}"
                )

    return guidelines

# Run analyses
analyses = []
airline_files = {
    "LATAM": {
        "request": 'cargo-requests/LATAM Offer Request Example.json',
        "response": 'cargo-offers/LATAM Offer Response Example.json'
    },
    "Qatar": {
        "request": 'cargo-requests/Qatar Offer Request Example.json',
        "response": 'cargo-offers/Qatar Offer Response Example.json'
    },
    "TK": {
        "request": 'cargo-requests/TK Offer Request Example.json',
        "response": 'cargo-offers/TK Offer Response Example.json'
    }
}

for airline, files in airline_files.items():
    try:
        analysis = analyze_request_response_pair(
            files["request"],
            files["response"],
            airline
        )
        analyses.append(analysis)
    except Exception as e:
        print(f"Error analyzing {airline} files: {e}")

# Generate and print guidelines
guidelines = generate_bookability_guidelines(analyses)
print("\nBookability Guidelines:")
pprint(guidelines)

# Print detailed analysis
print("\nDetailed Analysis by Airline:")
for analysis in analyses:
    print(f"\n{analysis['airline']} Analysis:")
    pprint(analysis)