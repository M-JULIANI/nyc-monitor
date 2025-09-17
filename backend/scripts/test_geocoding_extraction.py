#!/usr/bin/env python3
"""
Test script for the enhanced geocoding-based location extraction
"""
import logging
from monitor.utils.location_extractor import NYCLocationExtractor
import asyncio
import sys
import os
import pytest

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.expensive_api
@pytest.mark.asyncio
async def test_geocoding_extraction():
    """Test the new geocoding-based location extraction"""

    extractor = NYCLocationExtractor()

    # Test cases with real-world alert titles
    test_cases = [
        {
            'title': 'AOC rallies for No Kings Act at Bryant Park',
            'content': 'Rally happening this afternoon',
            'expected_location': 'Bryant Park'
        },
        {
            'title': 'Protest march from Madison Square Garden to Times Square',
            'content': 'Large crowd expected',
            'expected_location': 'Madison Square Garden or Times Square'
        },
        {
            'title': 'Staten Island Ferry service disrupted',
            'content': 'Mechanical issues reported',
            'expected_location': 'Staten Island'
        },
        {
            'title': 'Traffic incident on 5th Avenue and 42nd Street',
            'content': 'Multiple lanes blocked',
            'expected_location': '5th Avenue and 42nd Street'
        },
        {
            'title': 'Community event in Williamsburg Brooklyn',
            'content': 'Local festival this weekend',
            'expected_location': 'Williamsburg'
        }
    ]

    print("🧪 TESTING GEOCODING-BASED LOCATION EXTRACTION")
    print("=" * 60)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📍 TEST {i}: {test_case['title']}")
        print(f"Expected: {test_case['expected_location']}")

        try:
            # Test the new geocoding method
            result = await extractor.extract_location_info_with_geocoding(
                test_case['title'],
                test_case['content']
            )

            if result['has_coordinates']:
                location = result['locations_found'][0] if result['locations_found'] else {
                }
                print(f"✅ SUCCESS:")
                print(f"   📍 Location: {location.get('name', 'Unknown')}")
                print(
                    f"   🗺️  Coordinates: {result['center_latitude']:.4f}, {result['center_longitude']:.4f}")
                print(f"   🏙️  Borough: {location.get('borough', 'Unknown')}")
                print(
                    f"   🎯 Confidence: {location.get('confidence', 0.0):.2f}")
                print(
                    f"   📡 Source: {result.get('geocoding_source', 'unknown')}")
            else:
                print(f"❌ FAILED: No coordinates found")
                print(
                    f"   Fallback used: {len(result['locations_found'])} hardcoded locations found")

        except Exception as e:
            print(f"💥 ERROR: {str(e)}")

    print("\n" + "=" * 60)
    print("🏁 GEOCODING EXTRACTION TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_geocoding_extraction())
