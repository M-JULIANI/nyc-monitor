"""
Geocoding utility for NYC Monitor System.
Uses free Nominatim (OpenStreetMap) service to convert addresses and neighborhoods to coordinates.
"""
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Tuple, List
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
    Enhanced function to geocode any NYC location text with smart preprocessing

    Args:
        location_text: Address, venue, neighborhood, or intersection (could be a full title/sentence)
        context: Optional context (borough, area)

    Returns:
        Geocoding result dict
    """
    geocoder = NYCGeocoder()

    # Preprocess the location text to extract likely location information
    processed_queries = _extract_location_queries(location_text)

    # Try each extracted query in order of likelihood
    for query, query_type in processed_queries:
        try:
            logger.debug(f"Trying to geocode: '{query}' as {query_type}")

            if query_type == 'intersection':
                parts = query.replace(' & ', ' and ').split(' and ')
                if len(parts) == 2:
                    result = await geocoder.geocode_intersection(parts[0].strip(), parts[1].strip(), context)
            elif query_type == 'venue':
                result = await geocoder.geocode_venue(query, context)
            elif query_type == 'address':
                result = await geocoder.geocode_address(query, context)
            else:  # neighborhood or general
                result = await geocoder.geocode_neighborhood(query, context)

            # If successful, return the result
            if result.get('success'):
                logger.info(
                    f"Successfully geocoded '{query}' -> {result.get('formatted_address')}")
                return result

        except Exception as e:
            logger.debug(f"Failed to geocode '{query}': {e}")
            continue

    # If all specific queries fail, try the original text as-is
    try:
        logger.debug(
            f"Trying original text as neighborhood: '{location_text}'")
        result = await geocoder.geocode_neighborhood(location_text, context)
        if result.get('success'):
            return result
    except Exception as e:
        logger.debug(f"Failed to geocode original text: {e}")

    # Return empty result if everything fails
    logger.warning(f"Could not geocode any part of: '{location_text}'")
    return geocoder._empty_result()


def _extract_location_queries(text: str) -> List[Tuple[str, str]]:
    """
    Extract potential location queries from text with their likely types

    Returns:
        List of (query, type) tuples ordered by likelihood of success
    """
    import re

    queries = []
    text_lower = text.lower().strip()

    # Remove common non-location words that might confuse geocoding
    noise_words = ['rally', 'march', 'protest', 'event', 'happening', 'at', 'in', 'on', 'near', 'around',
                   'no kings', 'aoc', 'rallies', 'for', 'against', 'supports', 'mayor', 'video', 'link',
                   'reddit', 'post', 'indicates', 'content', 'includes', 'engagement', 'upvotes', 'comments',
                   'traffic', 'incident', 'service', 'disrupted', 'community', 'from', 'to']

    # 1. Look for street intersections FIRST (highest priority)
    intersection_patterns = [
        r'(\d+(?:st|nd|rd|th)?\s+(?:street|st|avenue|ave))\s+(?:and|&|\+)\s+(\d+(?:st|nd|rd|th)?\s+(?:street|st|avenue|ave))',
        r'(5th avenue)\s+(?:and|&|\+)\s+(42nd street)',
        r'(broadway)\s+(?:and|&|\+)\s+(\d+(?:st|nd|rd|th)?\s+(?:street|st))',
        r'(\w+\s+(?:street|st|avenue|ave))\s+(?:and|&|\+)\s+(\w+\s+(?:street|st|avenue|ave))'
    ]

    for pattern in intersection_patterns:
        intersection_matches = re.findall(pattern, text_lower)
        for match in intersection_matches:
            intersection = f"{match[0]} and {match[1]}"
            queries.append((intersection, 'intersection'))

    # 2. Look for specific venue patterns (high priority)
    venue_patterns = [
        r'(bryant park)',
        r'(madison square garden|msg)',
        r'(central park)',
        r'(times square)',
        r'(union square)',
        r'(washington square)',
        r'(yankee stadium)',
        r'(citi field)',
        r'(barclays center)',
        r'(lincoln center)',
        r'(grand central)',
        r'(penn station)',
        r'(port authority)'
    ]

    for pattern in venue_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            queries.append((match.strip(), 'venue'))

    # 3. Look for neighborhood patterns (medium priority)
    neighborhood_patterns = [
        r'(williamsburg)',
        r'(park slope)',
        r'(astoria)',
        r'(harlem)',
        r'(soho)',
        r'(tribeca)',
        r'(chelsea)',
        r'(midtown)',
        r'(downtown)',
        r'(uptown)',
        r'(financial district)',
        r'(upper east side)',
        r'(upper west side)',
        r'(east village)',
        r'(west village)',
        r'(greenwich village)',
        r'(lower east side)',
        r'(long island city)',
        r'(forest hills)',
        r'(jackson heights)',
        r'(crown heights)',
        r'(bed-stuy|bedford-stuyvesant)',
        r'(bushwick)',
        r'(dumbo)',
        r'(red hook)',
        r'(sunset park)'
    ]

    for pattern in neighborhood_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            queries.append((match.strip(), 'neighborhood'))

    # 4. Look for borough names (medium priority)
    borough_patterns = [
        r'(staten island)',
        r'(manhattan)',
        r'(brooklyn)',
        r'(queens)',
        r'(bronx)'
    ]

    for pattern in borough_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            queries.append((match.strip(), 'neighborhood'))

    # 5. Look for addresses (numbers + street names)
    address_pattern = r'(\d+\s+[a-zA-Z\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd))'
    address_matches = re.findall(address_pattern, text_lower)
    for match in address_matches:
        queries.append((match.strip(), 'address'))

    # 6. Extract potential location phrases (remove noise words) - LOWEST priority
    words = text_lower.split()
    clean_words = [
        word for word in words if word not in noise_words and len(word) > 2]

    # Only try 2-3 word combinations that might be locations
    for i in range(len(clean_words)):
        for j in range(i+2, min(i+4, len(clean_words)+1)):  # Only 2-3 word combinations
            phrase = ' '.join(clean_words[i:j])
            # Only add if it looks like a location (contains common location words)
            location_indicators = ['park', 'square', 'center',
                                   'bridge', 'station', 'terminal', 'plaza', 'garden']
            if (len(phrase) > 5 and
                any(indicator in phrase for indicator in location_indicators) and
                    phrase not in [q[0] for q in queries]):
                queries.append((phrase, 'neighborhood'))

    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for query, qtype in queries:
        if query not in seen:
            seen.add(query)
            unique_queries.append((query, qtype))

    return unique_queries
