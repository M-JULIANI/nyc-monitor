"""
NYC Location Extraction Utility

Extracts geographic information from text content, specifically designed for NYC-related posts.
Since social media platforms like Reddit don't provide native lat/lon coordinates,
this module identifies NYC locations from post content and assigns approximate coordinates.
"""
import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class NYCLocationExtractor:
    """Extract NYC location information from text content"""

    def __init__(self):
        """Initialize the location extractor with NYC location database"""

        # NYC location database with approximate coordinates
        # Format: location_name: (latitude, longitude, borough, type)
        self.nyc_locations = {
            # Manhattan landmarks & neighborhoods
            'times square': (40.7580, -73.9855, 'manhattan', 'landmark'),
            'central park': (40.7829, -73.9654, 'manhattan', 'park'),
            'union square': (40.7359, -73.9911, 'manhattan', 'landmark'),
            'washington square': (40.7308, -73.9973, 'manhattan', 'park'),
            'battery park': (40.7033, -74.0170, 'manhattan', 'park'),
            'world trade center': (40.7115, -74.0134, 'manhattan', 'landmark'),
            'empire state building': (40.7484, -73.9857, 'manhattan', 'landmark'),
            'grand central': (40.7527, -73.9772, 'manhattan', 'transit'),
            'penn station': (40.7505, -73.9934, 'manhattan', 'transit'),
            'port authority': (40.7589, -73.9896, 'manhattan', 'transit'),

            # Manhattan neighborhoods
            'soho': (40.7233, -74.0030, 'manhattan', 'neighborhood'),
            'tribeca': (40.7195, -74.0089, 'manhattan', 'neighborhood'),
            'chinatown': (40.7158, -73.9970, 'manhattan', 'neighborhood'),
            'little italy': (40.7196, -73.9977, 'manhattan', 'neighborhood'),
            'east village': (40.7264, -73.9818, 'manhattan', 'neighborhood'),
            'west village': (40.7358, -74.0036, 'manhattan', 'neighborhood'),
            'greenwich village': (40.7336, -74.0027, 'manhattan', 'neighborhood'),
            'lower east side': (40.7180, -73.9858, 'manhattan', 'neighborhood'),
            'upper east side': (40.7736, -73.9566, 'manhattan', 'neighborhood'),
            'upper west side': (40.7870, -73.9754, 'manhattan', 'neighborhood'),
            'harlem': (40.8176, -73.9482, 'manhattan', 'neighborhood'),
            'washington heights': (40.8518, -73.9351, 'manhattan', 'neighborhood'),
            'inwood': (40.8676, -73.9212, 'manhattan', 'neighborhood'),
            'chelsea': (40.7465, -73.9973, 'manhattan', 'neighborhood'),
            'gramercy': (40.7368, -73.9830, 'manhattan', 'neighborhood'),
            'murray hill': (40.7505, -73.9733, 'manhattan', 'neighborhood'),
            'midtown': (40.7549, -73.9840, 'manhattan', 'neighborhood'),
            'downtown': (40.7074, -74.0113, 'manhattan', 'neighborhood'),
            'uptown': (40.7829, -73.9654, 'manhattan', 'neighborhood'),
            'financial district': (40.7074, -74.0113, 'manhattan', 'neighborhood'),
            "hell's kitchen": (40.7648, -73.9896, 'manhattan', 'neighborhood'),
            'morningside heights': (40.8076, -73.9626, 'manhattan', 'neighborhood'),

            # Brooklyn landmarks & neighborhoods
            'brooklyn bridge': (40.7061, -73.9969, 'brooklyn', 'landmark'),
            'prospect park': (40.6602, -73.9690, 'brooklyn', 'park'),
            'coney island': (40.5755, -73.9707, 'brooklyn', 'neighborhood'),
            'williamsburg': (40.7081, -73.9571, 'brooklyn', 'neighborhood'),
            'park slope': (40.6782, -73.9776, 'brooklyn', 'neighborhood'),
            'bushwick': (40.6942, -73.9222, 'brooklyn', 'neighborhood'),
            'bed-stuy': (40.6895, -73.9308, 'brooklyn', 'neighborhood'),
            'bedford-stuyvesant': (40.6895, -73.9308, 'brooklyn', 'neighborhood'),
            'crown heights': (40.6782, -73.9442, 'brooklyn', 'neighborhood'),
            'sunset park': (40.6527, -74.0134, 'brooklyn', 'neighborhood'),
            'red hook': (40.6751, -74.0088, 'brooklyn', 'neighborhood'),
            'dumbo': (40.7033, -73.9899, 'brooklyn', 'neighborhood'),
            'brooklyn heights': (40.6962, -73.9926, 'brooklyn', 'neighborhood'),
            'bay ridge': (40.6233, -74.0273, 'brooklyn', 'neighborhood'),
            'bensonhurst': (40.6018, -73.9962, 'brooklyn', 'neighborhood'),
            'sheepshead bay': (40.5941, -73.9442, 'brooklyn', 'neighborhood'),

            # Queens landmarks & neighborhoods
            'long island city': (40.7505, -73.9350, 'queens', 'neighborhood'),
            'lic': (40.7505, -73.9350, 'queens', 'neighborhood'),
            'astoria': (40.7614, -73.9246, 'queens', 'neighborhood'),
            'flushing': (40.7674, -73.8330, 'queens', 'neighborhood'),
            'forest hills': (40.7209, -73.8448, 'queens', 'neighborhood'),
            'jackson heights': (40.7505, -73.8803, 'queens', 'neighborhood'),
            'elmhurst': (40.7362, -73.8827, 'queens', 'neighborhood'),
            'woodside': (40.7456, -73.9062, 'queens', 'neighborhood'),
            'sunnyside': (40.7434, -73.9249, 'queens', 'neighborhood'),
            'corona': (40.7498, -73.8621, 'queens', 'neighborhood'),

            # Bronx
            'yankee stadium': (40.8296, -73.9262, 'bronx', 'landmark'),
            'south bronx': (40.8176, -73.9209, 'bronx', 'neighborhood'),
            'riverdale': (40.8990, -73.9057, 'bronx', 'neighborhood'),
            'fordham': (40.8615, -73.9019, 'bronx', 'neighborhood'),
            'mott haven': (40.8084, -73.9264, 'bronx', 'neighborhood'),

            # Staten Island
            'st. george': (40.6431, -74.0776, 'staten_island', 'neighborhood'),
            'stapleton': (40.6276, -74.0807, 'staten_island', 'neighborhood'),
            'new brighton': (40.6434, -74.0776, 'staten_island', 'neighborhood'),
            'tottenville': (40.5062, -74.2446, 'staten_island', 'neighborhood'),

            # Major streets & avenues (approximate central coordinates)
            '5th avenue': (40.7549, -73.9840, 'manhattan', 'street'),
            'broadway': (40.7549, -73.9840, 'manhattan', 'street'),
            'madison avenue': (40.7505, -73.9733, 'manhattan', 'street'),
            'park avenue': (40.7505, -73.9733, 'manhattan', 'street'),
            'lexington avenue': (40.7505, -73.9733, 'manhattan', 'street'),
            '42nd street': (40.7549, -73.9840, 'manhattan', 'street'),
            '34th street': (40.7505, -73.9934, 'manhattan', 'street'),
            '14th street': (40.7359, -73.9911, 'manhattan', 'street'),
            'houston street': (40.7214, -73.9967, 'manhattan', 'street'),
            'canal street': (40.7190, -74.0023, 'manhattan', 'street'),
            '23rd street': (40.7433, -73.9893, 'manhattan', 'street'),
            '57th street': (40.7648, -73.9808, 'manhattan', 'street'),
            '125th street': (40.8076, -73.9482, 'manhattan', 'street'),

            # Transit infrastructure
            'bqe': (40.6892, -73.9442, 'brooklyn', 'highway'),
            'brooklyn-queens expressway': (40.6892, -73.9442, 'brooklyn', 'highway'),
            'fdr drive': (40.7074, -73.9776, 'manhattan', 'highway'),
            'west side highway': (40.7359, -74.0089, 'manhattan', 'highway'),
            'manhattan bridge': (40.7072, -73.9904, 'manhattan', 'bridge'),
            'queensboro bridge': (40.7505, -73.9350, 'queens', 'bridge'),
            'williamsburg bridge': (40.7081, -73.9637, 'brooklyn', 'bridge'),
            'verrazano bridge': (40.6066, -74.0447, 'staten_island', 'bridge'),
            'george washington bridge': (40.8517, -73.9527, 'manhattan', 'bridge'),
            'holland tunnel': (40.7280, -74.0134, 'manhattan', 'tunnel'),
            'lincoln tunnel': (40.7614, -73.9776, 'manhattan', 'tunnel'),
            'queens-midtown tunnel': (40.7433, -73.9626, 'manhattan', 'tunnel'),
        }

    def extract_location_info(self, title: str, content: str) -> Dict:
        """
        Extract location information from post content

        Args:
            title: Post title text
            content: Post content text

        Returns:
            Dictionary containing found locations and coordinate data
        """
        try:
            full_text = f"{title} {content}".lower()

            # Extract locations and coordinates
            found_locations = []
            coordinates = []

            # Find exact location matches
            for location, (lat, lon, borough, loc_type) in self.nyc_locations.items():
                # For short abbreviations like 'lic', require word boundaries
                if len(location) <= 3:
                    # Use word boundary regex for short terms
                    if re.search(rf'\b{re.escape(location)}\b', full_text, re.IGNORECASE):
                        found_locations.append({
                            'name': location,
                            'latitude': lat,
                            'longitude': lon,
                            'borough': borough,
                            'type': loc_type,
                            'confidence': 0.8  # High confidence for exact matches
                        })
                        coordinates.append((lat, lon))
                else:
                    # Regular substring match for longer location names
                    if location in full_text:
                        found_locations.append({
                            'name': location,
                            'latitude': lat,
                            'longitude': lon,
                            'borough': borough,
                            'type': loc_type,
                            'confidence': 0.8  # High confidence for exact matches
                        })
                        coordinates.append((lat, lon))

            # Extract street intersections (e.g., "5th Ave and 42nd St")
            intersection_locations = self._extract_intersections(full_text)
            found_locations.extend(intersection_locations)

            # Extract subway stations
            subway_locations = self._extract_subway_stations(full_text)
            found_locations.extend(subway_locations)

            # Calculate center point if multiple locations found
            center_lat = center_lon = None
            if coordinates:
                center_lat = sum(coord[0]
                                 for coord in coordinates) / len(coordinates)
                center_lon = sum(coord[1]
                                 for coord in coordinates) / len(coordinates)

            return {
                'locations_found': found_locations,
                'center_latitude': center_lat,
                'center_longitude': center_lon,
                'location_count': len(found_locations),
                'primary_borough': found_locations[0]['borough'] if found_locations else None,
                'has_coordinates': len(coordinates) > 0
            }

        except Exception as e:
            logger.warning(f"Error extracting location info: {e}")
            return self._empty_location_result()

    def _extract_intersections(self, text: str) -> List[Dict]:
        """Extract street intersection patterns"""
        intersections = []

        # Pattern for intersections like "5th Ave and 42nd St"
        intersection_pattern = r'(\d+(?:st|nd|rd|th)\s+(?:street|st|avenue|ave))\s+(?:and|&|\+)\s+(\d+(?:st|nd|rd|th)\s+(?:street|st|avenue|ave))'
        matches = re.findall(intersection_pattern, text, re.IGNORECASE)

        for intersection in matches:
            # For intersections, estimate coordinates based on Manhattan grid
            # This is simplified - could be enhanced with proper geocoding
            intersections.append({
                'name': f"{intersection[0]} and {intersection[1]}",
                'latitude': 40.7549,  # Default to Midtown Manhattan
                'longitude': -73.9840,
                'borough': 'manhattan',
                'type': 'intersection',
                'confidence': 0.6  # Medium confidence for intersections
            })

        return intersections

    def _extract_subway_stations(self, text: str) -> List[Dict]:
        """Extract subway station mentions"""
        stations = []

        # Pattern for stations like "at Union Square station"
        subway_pattern = r'(?:at|near)\s+([a-zA-Z\s]+)(?:\s+station|\s+stop)'
        matches = re.findall(subway_pattern, text, re.IGNORECASE)

        for station in matches:
            station = station.strip()
            if len(station) > 2:  # Filter out very short matches
                stations.append({
                    'name': f"{station} station",
                    'latitude': 40.7549,  # Default coordinates
                    'longitude': -73.9840,
                    'borough': 'unknown',
                    'type': 'transit',
                    'confidence': 0.5  # Lower confidence for pattern matches
                })

        return stations

    def _empty_location_result(self) -> Dict:
        """Return empty location result structure"""
        return {
            'locations_found': [],
            'center_latitude': None,
            'center_longitude': None,
            'location_count': 0,
            'primary_borough': None,
            'has_coordinates': False
        }

    def get_location_count(self) -> int:
        """Get total number of locations in database"""
        return len(self.nyc_locations)

    def get_locations_by_borough(self, borough: str) -> List[str]:
        """Get all locations for a specific borough"""
        return [
            name for name, (lat, lon, boro, loc_type) in self.nyc_locations.items()
            if boro.lower() == borough.lower()
        ]

    def get_locations_by_type(self, location_type: str) -> List[str]:
        """Get all locations of a specific type (landmark, neighborhood, etc.)"""
        return [
            name for name, (lat, lon, borough, loc_type) in self.nyc_locations.items()
            if loc_type.lower() == location_type.lower()
        ]
