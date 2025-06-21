"""
Normalized Alert Categories for NYC Monitor System.
Based on analysis of NYC 311 complaint types and monitor alert patterns.
"""
from typing import Dict, List, Set
from enum import Enum


class AlertCategory(Enum):
    """Normalized alert categories"""
    INFRASTRUCTURE = "infrastructure"
    EMERGENCY = "emergency"
    TRANSPORTATION = "transportation"
    EVENTS = "events"
    SAFETY = "safety"
    ENVIRONMENT = "environment"
    HOUSING = "housing"
    GENERAL = "general"


class AlertType:
    """Alert type definition with metadata"""

    def __init__(self, category: AlertCategory, name: str, description: str,
                 default_severity: int = 5):
        self.category = category
        self.name = name
        self.description = description
        self.default_severity = default_severity


# Comprehensive alert type definitions based on data analysis
ALERT_TYPES = {
    # INFRASTRUCTURE
    "water_system": AlertType(
        AlertCategory.INFRASTRUCTURE, "Water System",
        "Water infrastructure issues including hydrants, leaks, and outages",
        7
    ),
    "power_outage": AlertType(
        AlertCategory.INFRASTRUCTURE, "Power Outage",
        "Electrical infrastructure and power-related issues",
        8
    ),
    "elevator": AlertType(
        AlertCategory.INFRASTRUCTURE, "Elevator",
        "Elevator breakdowns and accessibility issues",
        6
    ),
    "gas_leak": AlertType(
        AlertCategory.INFRASTRUCTURE, "Gas Leak",
        "Gas system issues and potential leaks",
        9
    ),
    "plumbing": AlertType(
        AlertCategory.INFRASTRUCTURE, "Plumbing",
        "Plumbing and sewage system issues",
        6
    ),

    # EMERGENCY
    "fire": AlertType(
        AlertCategory.EMERGENCY, "Fire",
        "Fire incidents and fire safety emergencies",
        10
    ),
    "medical_emergency": AlertType(
        AlertCategory.EMERGENCY, "Medical Emergency",
        "Medical emergencies and health crises",
        9
    ),
    "structural_emergency": AlertType(
        AlertCategory.EMERGENCY, "Structural Emergency",
        "Building collapses, structural damage, scaffold safety",
        8
    ),
    "hazmat": AlertType(
        AlertCategory.EMERGENCY, "Hazardous Materials",
        "Chemical spills, lead exposure, toxic material incidents",
        9
    ),

    # TRANSPORTATION
    "traffic_incident": AlertType(
        AlertCategory.TRANSPORTATION, "Traffic Incident",
        "Traffic accidents, road closures, signal outages",
        6
    ),
    "transit_disruption": AlertType(
        AlertCategory.TRANSPORTATION, "Transit Disruption",
        "Subway delays, bus route changes, transportation issues",
        5
    ),
    "parking_violation": AlertType(
        AlertCategory.TRANSPORTATION, "Parking Issue",
        "Illegal parking, blocked driveways, parking violations",
        3
    ),
    "street_closure": AlertType(
        AlertCategory.TRANSPORTATION, "Street Closure",
        "Road closures for construction, events, or emergencies",
        6
    ),

    # EVENTS
    "parade": AlertType(
        AlertCategory.EVENTS, "Parade",
        "Parades and processions affecting traffic and crowds",
        5
    ),
    "festival": AlertType(
        AlertCategory.EVENTS, "Festival",
        "Street festivals, block parties, public celebrations",
        4
    ),
    "concert": AlertType(
        AlertCategory.EVENTS, "Concert",
        "Concerts and musical performances in public spaces",
        4
    ),
    "protest": AlertType(
        AlertCategory.EVENTS, "Protest",
        "Protests, demonstrations, and public assemblies",
        6
    ),
    "filming": AlertType(
        AlertCategory.EVENTS, "Film Permit",
        "Movie/TV filming affecting streets and traffic",
        3
    ),

    # SAFETY
    "crime": AlertType(
        AlertCategory.SAFETY, "Crime",
        "Criminal activity, drug activity, safety concerns",
        7
    ),
    "building_safety": AlertType(
        AlertCategory.SAFETY, "Building Safety",
        "Building code violations, construction safety issues",
        6
    ),
    "public_safety": AlertType(
        AlertCategory.SAFETY, "Public Safety",
        "General public safety concerns and incidents",
        6
    ),

    # ENVIRONMENT
    "noise_complaint": AlertType(
        AlertCategory.ENVIRONMENT, "Noise Complaint",
        "Noise violations from residential, commercial, or street sources",
        4
    ),
    "air_quality": AlertType(
        AlertCategory.ENVIRONMENT, "Air Quality",
        "Air pollution, smoke, environmental health concerns",
        6
    ),
    "sanitation": AlertType(
        AlertCategory.ENVIRONMENT, "Sanitation",
        "Dirty conditions, waste management, rodent issues",
        4
    ),
    "water_quality": AlertType(
        AlertCategory.ENVIRONMENT, "Water Quality",
        "Water contamination, quality issues, environmental concerns",
        7
    ),

    # HOUSING
    "heat_hot_water": AlertType(
        AlertCategory.HOUSING, "Heat/Hot Water",
        "Heating system failures, hot water outages in buildings",
        7
    ),
    "housing_violation": AlertType(
        AlertCategory.HOUSING, "Housing Violation",
        "Building violations, habitability issues, tenant concerns",
        6
    ),

    # GENERAL
    "general_inquiry": AlertType(
        AlertCategory.GENERAL, "General",
        "General inquiries and uncategorized issues",
        3
    )
}

# Mapping dictionaries for categorization
NYC_311_COMPLAINT_TYPE_MAPPING = {
    # Infrastructure
    "Water System": "water_system",
    "Electrical": "power_outage",
    "Elevator": "elevator",
    "Gas": "gas_leak",
    "Plumbing": "plumbing",
    "Street Light Condition": "power_outage",
    "Traffic Signal Condition": "power_outage",
    "Sewer": "plumbing",

    # Emergency
    "Emergency Response Team (ERT)": "medical_emergency",
    "Fire Safety Director - F58": "fire",
    "Lead": "hazmat",
    "Structural": "structural_emergency",
    "Scaffold Safety": "structural_emergency",
    "Emergency": "medical_emergency",

    # Transportation
    "Traffic Signal Condition": "traffic_incident",
    "Street Condition": "traffic_incident",
    "Illegal Parking": "parking_violation",
    "Blocked Driveway": "parking_violation",
    "Highway Condition": "traffic_incident",
    "Street Sign - Missing": "traffic_incident",
    "Street Sign - Damaged": "traffic_incident",

    # Events
    "Special Event": "festival",
    "Parade Permit": "parade",
    "Block Party": "festival",
    "Film Permit": "filming",
    "Street Fair Permit": "festival",
    "Public Assembly": "protest",
    "Street Festival": "festival",

    # Safety
    "Building/Use": "building_safety",
    "Drug Activity": "crime",
    "Police Department": "public_safety",
    "Fire/EMS": "medical_emergency",
    "Construction": "building_safety",

    # Environment
    "Noise - Residential": "noise_complaint",
    "Noise - Commercial": "noise_complaint",
    "Noise - Street/Sidewalk": "noise_complaint",
    "Noise - Vehicle": "noise_complaint",
    "Air Quality": "air_quality",
    "Indoor Air Quality": "air_quality",
    "Sanitation Condition": "sanitation",
    "Dirty Condition": "sanitation",
    "Rodent": "sanitation",

    # Housing
    "Heat/Hot Water": "heat_hot_water",
    "HEAT/HOT WATER": "heat_hot_water",
    "PLUMBING": "plumbing",

    # General fallback
    "Request Large Bulky Item Collection": "general_inquiry"
}

# Event type keywords for monitor alerts
MONITOR_EVENT_KEYWORDS = {
    # Infrastructure
    "infrastructure": "power_outage",
    "utilities": "water_system",
    "outage": "power_outage",
    "blackout": "power_outage",
    "water main": "water_system",
    "gas leak": "gas_leak",

    # Emergency
    "emergency": "medical_emergency",
    "fire": "fire",
    "accident": "traffic_incident",
    "crisis": "medical_emergency",
    "explosion": "structural_emergency",
    "collapse": "structural_emergency",

    # Transportation
    "traffic": "traffic_incident",
    "transit": "transit_disruption",
    "transportation": "traffic_incident",
    "subway": "transit_disruption",
    "closure": "street_closure",
    "road closed": "street_closure",

    # Events
    "parade": "parade",
    "festival": "festival",
    "concert": "concert",
    "protest": "protest",
    "demonstration": "protest",
    "gathering": "festival",
    "event": "festival",
    "filming": "filming",

    # Safety
    "crime": "crime",
    "safety": "public_safety",
    "security": "public_safety",
    "police": "public_safety",

    # Environment
    "noise": "noise_complaint",
    "pollution": "air_quality",
    "environmental": "air_quality",
    "sanitation": "sanitation"
}


def categorize_311_complaint(complaint_type: str) -> str:
    """
    Categorize a NYC 311 complaint type into normalized alert type

    Args:
        complaint_type: The 311 complaint type string

    Returns:
        Alert type key from ALERT_TYPES
    """
    if not complaint_type:
        return "general_inquiry"

    # Direct mapping first
    if complaint_type in NYC_311_COMPLAINT_TYPE_MAPPING:
        return NYC_311_COMPLAINT_TYPE_MAPPING[complaint_type]

    # Fuzzy matching
    complaint_lower = complaint_type.lower()

    for complaint_pattern, alert_type in NYC_311_COMPLAINT_TYPE_MAPPING.items():
        if complaint_pattern.lower() in complaint_lower or complaint_lower in complaint_pattern.lower():
            return alert_type

    return "general_inquiry"


def categorize_monitor_event(event_type: str, title: str = "", description: str = "") -> str:
    """
    Categorize a monitor alert based on event type, title, and description

    Args:
        event_type: The event type from the alert
        title: Alert title for additional context
        description: Alert description for additional context

    Returns:
        Alert type key from ALERT_TYPES
    """
    if not event_type and not title and not description:
        return "general_inquiry"

    # Combine all text for analysis
    combined_text = f"{event_type or ''} {title or ''} {description or ''}".lower()

    # Check for keyword matches
    for keyword, alert_type in MONITOR_EVENT_KEYWORDS.items():
        if keyword in combined_text:
            return alert_type

    return "general_inquiry"


def get_alert_type_info(alert_type_key: str) -> AlertType:
    """
    Get alert type information

    Args:
        alert_type_key: Key from ALERT_TYPES

    Returns:
        AlertType object with metadata
    """
    return ALERT_TYPES.get(alert_type_key, ALERT_TYPES["general_inquiry"])


def get_categories_summary() -> Dict:
    """
    Get a summary of all alert categories for frontend use

    Returns:
        Dictionary with category information
    """
    categories = {}

    for category in AlertCategory:
        category_types = [
            {
                "key": key,
                "name": alert_type.name,
                "description": alert_type.description,
                "default_severity": alert_type.default_severity
            }
            for key, alert_type in ALERT_TYPES.items()
            if alert_type.category == category
        ]

        categories[category.value] = {
            "name": category.value.title(),
            "types": category_types
        }

    return categories


def normalize_category(category: str) -> str:
    """
    Normalize any category value to one of our predefined main categories

    Args:
        category: Any category string

    Returns:
        One of the main AlertCategory values: infrastructure, emergency, transportation, 
        events, safety, environment, housing, general
    """
    if not category:
        return "general"

    category_lower = category.lower().strip()

    # Direct mapping to main categories
    valid_categories = {cat.value for cat in AlertCategory}
    if category_lower in valid_categories:
        return category_lower

    # Fuzzy matching for variations
    category_mappings = {
        # Infrastructure variations
        "infrastructure": "infrastructure",
        "utility": "infrastructure",
        "utilities": "infrastructure",
        "power": "infrastructure",
        "water": "infrastructure",
        "gas": "infrastructure",
        "electrical": "infrastructure",

        # Emergency variations
        "emergency": "emergency",
        "urgent": "emergency",
        "critical": "emergency",
        "fire": "emergency",
        "medical": "emergency",
        "hazmat": "emergency",
        "structural": "emergency",

        # Transportation variations
        "transportation": "transportation",
        "transport": "transportation",
        "traffic": "transportation",
        "transit": "transportation",
        "parking": "transportation",
        "road": "transportation",
        "street": "transportation",

        # Events variations
        "events": "events",
        "event": "events",
        "parade": "events",
        "festival": "events",
        "concert": "events",
        "protest": "events",
        "filming": "events",

        # Safety variations
        "safety": "safety",
        "security": "safety",
        "crime": "safety",
        "police": "safety",
        "building": "safety",

        # Environment variations
        "environment": "environment",
        "environmental": "environment",
        "noise": "environment",
        "air": "environment",
        "pollution": "environment",
        "sanitation": "environment",

        # Housing variations
        "housing": "housing",
        "residential": "housing",
        "building": "housing",
        "heat": "housing",
        "apartment": "housing",
    }

    return category_mappings.get(category_lower, "general")


def get_main_categories() -> List[str]:
    """
    Get list of main category values for frontend use

    Returns:
        List of main category strings
    """
    return [cat.value for cat in AlertCategory]
