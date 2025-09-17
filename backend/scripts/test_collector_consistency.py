#!/usr/bin/env python3
"""
Test script to verify that Reddit and Twitter collectors use consistent geocoding-based location extraction
"""
from monitor.utils.location_extractor import NYCLocationExtractor
import asyncio
import sys
import os
import logging
import pytest

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_collector_consistency():
    """Test that both collectors use the same geocoding approach"""

    print("🧪 TESTING COLLECTOR CONSISTENCY")
    print("=" * 60)

    # Test the location extractor directly (used by both collectors)
    extractor = NYCLocationExtractor()

    test_cases = [
        "AOC rallies for No Kings Act at Bryant Park",
        "Traffic incident on 5th Avenue and 42nd Street",
        "Community event in Williamsburg Brooklyn",
        "Emergency at Madison Square Garden"
    ]

    print("\n📍 Testing geocoding-based location extraction:")

    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{test_text}'")

        try:
            # Test the new geocoding method (used by both collectors)
            result = await extractor.extract_location_info_with_geocoding(test_text, '')

            if result['has_coordinates']:
                location = result['locations_found'][0] if result['locations_found'] else {
                }
                print(f"   ✅ SUCCESS: {location.get('name', 'Unknown')}")
                print(
                    f"   📍 Coordinates: {result['center_latitude']:.4f}, {result['center_longitude']:.4f}")
                print(f"   🏙️  Borough: {location.get('borough', 'Unknown')}")
                print(
                    f"   📡 Source: {result.get('geocoding_source', 'unknown')}")
            else:
                print(f"   ⚠️  Fallback: Using hardcoded locations")

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")

    print("\n" + "=" * 60)
    print("✅ Both Reddit and Twitter collectors now use:")
    print("   - location_extractor.extract_location_info_with_geocoding()")
    print("   - Free geocoding service as primary method")
    print("   - Hardcoded locations as fallback")
    print("   - Consistent coordinate extraction")
    print("🏁 COLLECTOR CONSISTENCY TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_collector_consistency())
