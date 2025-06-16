#!/usr/bin/env python3
"""
Test script for NYC Geocoder
Tests geocoding functionality with various NYC addresses, venues, and neighborhoods.
"""

from monitor.utils.geocode import NYCGeocoder, geocode_nyc_location
import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


async def test_geocoder():
    """Test the NYC geocoder with various location types"""

    print("🗽 Testing NYC Geocoder")
    print("=" * 50)

    geocoder = NYCGeocoder()

    # Test cases with different types of NYC locations
    test_cases = [
        # Specific addresses
        {
            'type': 'Address',
            'input': '350 5th Avenue, Manhattan',
            'method': 'geocode_address',
            'expected_area': 'Empire State Building area'
        },
        {
            'type': 'Address',
            'input': '620 Atlantic Avenue, Brooklyn',
            'method': 'geocode_address',
            'expected_area': 'Barclays Center area'
        },
        {
            'type': 'Address',
            'input': '1 Times Square, Manhattan',
            'method': 'geocode_address',
            'expected_area': 'Times Square'
        },

        # Famous venues
        {
            'type': 'Venue',
            'input': 'Madison Square Garden',
            'method': 'geocode_venue',
            'expected_area': 'Midtown Manhattan'
        },
        {
            'type': 'Venue',
            'input': 'Yankee Stadium',
            'method': 'geocode_venue',
            'expected_area': 'Bronx'
        },
        {
            'type': 'Venue',
            'input': 'Brooklyn Bridge',
            'method': 'geocode_venue',
            'expected_area': 'Between Manhattan and Brooklyn'
        },

        # Neighborhoods
        {
            'type': 'Neighborhood',
            'input': 'Williamsburg',
            'method': 'geocode_neighborhood',
            'context': 'Brooklyn',
            'expected_area': 'Brooklyn'
        },
        {
            'type': 'Neighborhood',
            'input': 'Times Square',
            'method': 'geocode_neighborhood',
            'context': 'Manhattan',
            'expected_area': 'Midtown Manhattan'
        },
        {
            'type': 'Neighborhood',
            'input': 'SoHo',
            'method': 'geocode_neighborhood',
            'context': 'Manhattan',
            'expected_area': 'Lower Manhattan'
        },

        # Street intersections
        {
            'type': 'Intersection',
            'input': ('42nd Street', '7th Avenue'),
            'method': 'geocode_intersection',
            'context': 'Manhattan',
            'expected_area': 'Times Square area'
        },
        {
            'type': 'Intersection',
            'input': ('5th Avenue', '59th Street'),
            'method': 'geocode_intersection',
            'context': 'Manhattan',
            'expected_area': 'Central Park area'
        }
    ]

    print(f"Testing {len(test_cases)} different NYC locations...\n")

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(
            f"Test {i}/{len(test_cases)}: {test_case['type']} - {test_case['input']}")

        try:
            # Call the appropriate geocoding method
            method_name = test_case['method']
            method = getattr(geocoder, method_name)

            if method_name == 'geocode_intersection':
                street1, street2 = test_case['input']
                result = await method(street1, street2, test_case.get('context'))
            elif 'context' in test_case:
                result = await method(test_case['input'], test_case['context'])
            else:
                result = await method(test_case['input'])

            # Display results
            if result['success']:
                lat, lng = result['lat'], result['lng']
                print(f"  ✅ SUCCESS: {lat:.6f}, {lng:.6f}")
                print(f"     Address: {result['formatted_address']}")
                print(f"     Confidence: {result['confidence']:.2f}")
                print(f"     Expected: {test_case['expected_area']}")

                # Validate coordinates are in reasonable NYC range
                if is_valid_nyc_coordinates(lat, lng):
                    print(f"     ✅ Coordinates are within NYC bounds")
                else:
                    print(f"     ❌ WARNING: Coordinates outside expected NYC bounds")

                results.append({
                    'test': test_case,
                    'result': result,
                    'success': True
                })
            else:
                print(f"  ❌ FAILED: No results found")
                results.append({
                    'test': test_case,
                    'result': result,
                    'success': False
                })

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append({
                'test': test_case,
                'result': None,
                'success': False,
                'error': str(e)
            })

        print()  # Empty line for readability

    # Test the enhanced geocode_nyc_location function
    print("\n" + "=" * 50)
    print("🔍 Testing Enhanced Geocoding Function")
    print("=" * 50)

    enhanced_tests = [
        "Tyler the Creator concert at Barclays Center on 620 Atlantic Avenue",
        "Protest rally at Bryant Park in Manhattan",
        "Traffic incident near 42nd Street and Broadway",
        "Event happening at Washington Square Park",
        "March from Union Square to Times Square",
        "Williamsburg Bridge closure affecting traffic"
    ]

    for test_text in enhanced_tests:
        print(f"Testing: {test_text}")
        try:
            result = await geocode_nyc_location(test_text)
            if result['success']:
                print(f"  ✅ Found: {result['lat']:.6f}, {result['lng']:.6f}")
                print(f"     Address: {result['formatted_address']}")
                print(f"     Confidence: {result['confidence']:.2f}")
            else:
                print(f"  ❌ Could not geocode")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()

    # Summary
    print("=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)

    successful = sum(1 for r in results if r['success'])
    total = len(results)

    print(
        f"Basic geocoding tests: {successful}/{total} successful ({successful/total*100:.1f}%)")

    if successful > 0:
        avg_confidence = sum(r['result']['confidence']
                             for r in results if r['success']) / successful
        print(f"Average confidence: {avg_confidence:.2f}")

    print("\nFailed tests:")
    for r in results:
        if not r['success']:
            test_input = r['test']['input']
            print(f"  - {r['test']['type']}: {test_input}")

    return results


def is_valid_nyc_coordinates(lat: float, lng: float) -> bool:
    """Check if coordinates are within reasonable NYC bounds"""
    # NYC approximate bounds
    return (40.4774 <= lat <= 40.9176 and  # Latitude range
            -74.2591 <= lng <= -73.7004)    # Longitude range


async def main():
    """Main test function"""
    try:
        results = await test_geocoder()

        # If most tests pass, geocoder is working
        successful = sum(1 for r in results if r['success'])
        if successful >= len(results) * 0.7:  # 70% success rate
            print(
                f"\n🎉 Geocoder appears to be working! ({successful}/{len(results)} tests passed)")
            return 0
        else:
            print(
                f"\n⚠️  Geocoder may have issues. Only {successful}/{len(results)} tests passed.")
            return 1

    except Exception as e:
        print(f"❌ Test script failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
