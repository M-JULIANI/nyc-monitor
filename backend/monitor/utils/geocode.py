"""
Geocoding utility for NYC Monitor System.
Uses free Nominatim (OpenStreetMap) service to convert addresses and neighborhoods to coordinates.
"""
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Tuple
from urllib.parse import quote
import time

logger = logging.getLogger(__name__)


class NYCGeocoder:
    """Geocoder for NYC addresses and neighborhoods using free Nominatim service"""

    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.rate_limit_delay = 1.0  # Nominatim requires 1 request per second
        self.last_request_time = 0
        self.timeout = 10  # seconds

        # NYC bounds for better results
        self.nyc_bounds = {
            'north': 40.9176,  # Bronx
            'south': 40.4774,  # Staten Island
            'east': -73.7004,  # Queens
            'west': -74.2591   # Staten Island
        }

    async def geocode_address(self, address: str, neighborhood: Optional[str] = None) -> Dict:
        """
        Geocode a specific address in NYC

        Args:
            address: Street address (e.g., "123 5th Avenue, Manhattan")
            neighborhood: Optional neighborhood context

        Returns:
            Dict with lat, lng, formatted_address, confidence
        """
        try:
            # Ensure NYC context
            if 'new york' not in address.lower() and 'nyc' not in address.lower():
                if neighborhood:
                    address = f"{address}, {neighborhood}, New York, NY"
                else:
                    address = f"{address}, New York, NY"

            return await self._geocode_query(address, query_type="address")

        except Exception as e:
            logger.error(f"Error geocoding address '{address}': {e}")
            return self._empty_result()

    async def geocode_neighborhood(self, neighborhood: str, borough: Optional[str] = None) -> Dict:
        """
        Geocode a NYC neighborhood

        Args:
            neighborhood: Neighborhood name (e.g., "Times Square", "Williamsburg")
            borough: Optional borough context (e.g., "Manhattan", "Brooklyn")

        Returns:
            Dict with lat, lng, formatted_address, confidence
        """
        try:
            # Build query with NYC context
            if borough:
                query = f"{neighborhood}, {borough}, New York, NY"
            else:
                query = f"{neighborhood}, New York, NY"

            return await self._geocode_query(query, query_type="neighborhood")

        except Exception as e:
            logger.error(f"Error geocoding neighborhood '{neighborhood}': {e}")
            return self._empty_result()

    async def geocode_venue(self, venue_name: str, address: Optional[str] = None) -> Dict:
        """
        Geocode a specific venue in NYC

        Args:
            venue_name: Name of the venue (e.g., "Madison Square Garden")
            address: Optional address context

        Returns:
            Dict with lat, lng, formatted_address, confidence
        """
        try:
            if address:
                query = f"{venue_name}, {address}, New York, NY"
            else:
                query = f"{venue_name}, New York, NY"

            return await self._geocode_query(query, query_type="venue")

        except Exception as e:
            logger.error(f"Error geocoding venue '{venue_name}': {e}")
            return self._empty_result()

    async def geocode_intersection(self, street1: str, street2: str, borough: Optional[str] = None) -> Dict:
        """
        Geocode a street intersection in NYC

        Args:
            street1: First street name
            street2: Second street name  
            borough: Optional borough context

        Returns:
            Dict with lat, lng, formatted_address, confidence
        """
        try:
            if borough:
                query = f"{street1} and {street2}, {borough}, New York, NY"
            else:
                query = f"{street1} and {street2}, New York, NY"

            return await self._geocode_query(query, query_type="intersection")

        except Exception as e:
            logger.error(
                f"Error geocoding intersection '{street1} & {street2}': {e}")
            return self._empty_result()

    async def _geocode_query(self, query: str, query_type: str = "general") -> Dict:
        """
        Internal method to perform geocoding query with rate limiting

        Args:
            query: Address/location query string
            query_type: Type of query for logging

        Returns:
            Dict with geocoding results
        """
        # Rate limiting - Nominatim requires max 1 request per second
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)

        self.last_request_time = time.time()

        try:
            # Build Nominatim query parameters
            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'us',
                'bounded': 1,
                'viewbox': f"{self.nyc_bounds['west']},{self.nyc_bounds['north']},{self.nyc_bounds['east']},{self.nyc_bounds['south']}",
                'addressdetails': 1
            }

            url = f"{self.base_url}?" + \
                "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])

            logger.debug(f"Geocoding {query_type}: {query}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data and len(data) > 0:
                            result = data[0]
                            lat = float(result.get('lat', 0))
                            lng = float(result.get('lon', 0))

                            # Validate coordinates are within NYC bounds
                            if self._is_in_nyc_bounds(lat, lng):
                                return {
                                    'lat': lat,
                                    'lng': lng,
                                    'formatted_address': result.get('display_name', query),
                                    'confidence': self._calculate_confidence(result, query_type),
                                    'source': 'nominatim',
                                    'success': True
                                }
                            else:
                                logger.warning(
                                    f"Geocoded location outside NYC bounds: {lat}, {lng}")

                        logger.warning(f"No geocoding results for: {query}")
                        return self._empty_result()
                    else:
                        logger.error(
                            f"Geocoding API error {response.status} for: {query}")
                        return self._empty_result()

        except asyncio.TimeoutError:
            logger.error(f"Geocoding timeout for: {query}")
            return self._empty_result()
        except Exception as e:
            logger.error(f"Geocoding error for '{query}': {e}")
            return self._empty_result()

    def _is_in_nyc_bounds(self, lat: float, lng: float) -> bool:
        """Check if coordinates are within NYC bounds"""
        return (self.nyc_bounds['south'] <= lat <= self.nyc_bounds['north'] and
                self.nyc_bounds['west'] <= lng <= self.nyc_bounds['east'])

    def _calculate_confidence(self, result: Dict, query_type: str) -> float:
        """Calculate confidence score based on geocoding result"""
        # Base confidence by query type
        base_confidence = {
            'address': 0.9,
            'venue': 0.8,
            'intersection': 0.8,
            'neighborhood': 0.6,
            'general': 0.5
        }.get(query_type, 0.5)

        # Adjust based on result type
        place_type = result.get('type', '').lower()
        class_type = result.get('class', '').lower()

        if place_type in ['house', 'building'] or class_type == 'building':
            return min(base_confidence + 0.2, 1.0)
        elif place_type in ['amenity', 'tourism'] or class_type in ['amenity', 'tourism']:
            return min(base_confidence + 0.1, 1.0)
        elif 'road' in place_type or 'highway' in class_type:
            return base_confidence
        else:
            return max(base_confidence - 0.1, 0.1)

    def _empty_result(self) -> Dict:
        """Return empty geocoding result"""
        return {
            'lat': None,
            'lng': None,
            'formatted_address': None,
            'confidence': 0.0,
            'source': 'nominatim',
            'success': False
        }


# Convenience functions for common use cases
async def geocode_nyc_location(location_text: str, context: Optional[str] = None) -> Dict:
    """
    Convenience function to geocode any NYC location text

    Args:
        location_text: Address, venue, neighborhood, or intersection
        context: Optional context (borough, area)

    Returns:
        Geocoding result dict
    """
    geocoder = NYCGeocoder()

    # Try to determine location type and geocode accordingly
    location_lower = location_text.lower()

    # Check for intersection patterns
    if ' and ' in location_lower or ' & ' in location_lower:
        parts = location_text.replace(' & ', ' and ').split(' and ')
        if len(parts) == 2:
            return await geocoder.geocode_intersection(parts[0].strip(), parts[1].strip(), context)

    # Check for known venues
    known_venues = ['madison square garden', 'yankee stadium', 'citi field', 'barclays center',
                    'central park', 'times square', 'brooklyn bridge', 'staten island ferry']
    if any(venue in location_lower for venue in known_venues):
        return await geocoder.geocode_venue(location_text, context)

    # Check for address pattern (numbers)
    if any(char.isdigit() for char in location_text):
        return await geocoder.geocode_address(location_text, context)

    # Default to neighborhood geocoding
    return await geocoder.geocode_neighborhood(location_text, context)
