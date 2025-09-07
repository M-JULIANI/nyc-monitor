#!/usr/bin/env python3
"""
Performance testing script for the new /alerts/viewport endpoint

This script tests the enhanced alert serving strategy with NYC-optimized spatial caching.
It validates cache performance, response times, and various viewport scenarios.

Output files are automatically saved in the backend/performance/ directory with timestamps.

Usage:
    cd backend
    poetry run python performance/test_viewport_performance.py [--base-url http://localhost:8000] [--auth-token your_token]

For local testing with auth bypass:
    poetry run python performance/test_viewport_performance.py --perf-test
"""

import asyncio
import aiohttp
import time
import json
import statistics
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys

class ViewportPerformanceTester:
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.results = {}
        self.session = None
        
    async def __aenter__(self):
        # Create session with auth headers if provided
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        self.session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def clear_cache(self):
        """Clear the API cache"""
        try:
            async with self.session.delete(f"{self.base_url}/api/alerts/cache") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"⚠️  Cache clear failed with status {response.status}")
                    return None
        except Exception as e:
            print(f"⚠️  Cache clear error: {e}")
            return None

    async def make_request(self, endpoint: str, description: str = "") -> Dict[str, Any]:
        """Make a request to the API and measure performance"""
        start_time = time.time()
        
        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        'success': True,
                        'response_time': response_time,
                        'status_code': response.status,
                        'data': data,
                        'description': description
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'response_time': response_time,
                        'status_code': response.status,
                        'error': error_text,
                        'description': description
                    }
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            return {
                'success': False,
                'response_time': response_time,
                'status_code': 0,
                'error': str(e),
                'description': description
            }

    async def test_performance_scenarios(self) -> Dict[str, Any]:
        """Test various performance scenarios as outlined in the strategy document"""
        
        print("🧪 Testing Performance Scenarios")
        print("=" * 50)
        
        # Test cases from the strategy document
        test_cases = [
            {
                'name': 'current_7_days',
                'endpoint': '/api/alerts/recent?hours=168',
                'description': 'Legacy endpoint for comparison'
            },
            {
                'name': 'viewport_7_days',
                'endpoint': '/api/alerts/viewport?bbox=40.7,-74.0,40.8,-73.9&start_date=2024-01-01&end_date=2024-01-07',
                'description': 'New caching system - 1 week Manhattan'
            },
            {
                'name': 'viewport_30_days',
                'endpoint': '/api/alerts/viewport?bbox=40.7,-74.0,40.8,-73.9&start_date=2023-12-01&end_date=2024-01-01',
                'description': 'Extended historical data - 1 month Manhattan'
            },
            {
                'name': 'viewport_6_months',
                'endpoint': '/api/alerts/viewport?bbox=40.7,-74.0,40.8,-73.9&start_date=2023-07-01&end_date=2024-01-01',
                'description': 'Full historical range - 6 months Manhattan'
            },
            {
                'name': 'borough_level',
                'endpoint': '/api/alerts/viewport?bbox=40.6,-74.1,40.9,-73.8&start_date=2024-01-01&end_date=2024-01-07',
                'description': 'Borough-level caching test'
            },
            {
                'name': 'street_level',
                'endpoint': '/api/alerts/viewport?bbox=40.75,-73.99,40.76,-73.98&start_date=2024-01-01&end_date=2024-01-07',
                'description': 'Street-level precision caching'
            },
            {
                'name': 'metro_area',
                'endpoint': '/api/alerts/viewport?bbox=40.0,-75.0,41.0,-73.0&start_date=2024-01-01&end_date=2024-01-07',
                'description': 'Metro area fallback handling'
            }
        ]
        
        results = {}
        
        for test_case in test_cases:
            print(f"\n🔍 Testing: {test_case['name']} - {test_case['description']}")
            
            cold_times = []
            warm_times = []
            cache_hit_data = []
            
            # Test cache misses (cold cache) - reduced runs for simplicity
            for i in range(2):
                await self.clear_cache()
                await asyncio.sleep(0.1)  # Brief pause after cache clear
                
                result = await self.make_request(test_case['endpoint'], f"Cold run {i+1}")
                
                if result['success']:
                    cold_times.append(result['response_time'])
                    perf_data = result['data'].get('performance', {})
                    cache_hit_data.append({
                        'run': i + 1,
                        'type': 'cold',
                        'cache_hit': perf_data.get('cache_hit', False),
                        'response_time': result['response_time'],
                        'alert_count': len(result['data'].get('alerts', [])),
                        'source': perf_data.get('source', 'unknown')
                    })
                else:
                    print(f"   ❌ Cold run {i+1} failed: {result.get('error', 'Unknown error')}")
            
            # Test cache hits (warm cache) - reduced runs for simplicity
            for i in range(3):
                result = await self.make_request(test_case['endpoint'], f"Warm run {i+1}")
                
                if result['success']:
                    warm_times.append(result['response_time'])
                    perf_data = result['data'].get('performance', {})
                    cache_hit_data.append({
                        'run': i + 3,
                        'type': 'warm',
                        'cache_hit': perf_data.get('cache_hit', False),
                        'response_time': result['response_time'],
                        'alert_count': len(result['data'].get('alerts', [])),
                        'source': perf_data.get('source', 'unknown')
                    })
                else:
                    print(f"   ❌ Warm run {i+1} failed: {result.get('error', 'Unknown error')}")
            
            # Calculate statistics
            if cold_times and warm_times:
                avg_cold_time = statistics.mean(cold_times)
                avg_warm_time = statistics.mean(warm_times)
                cache_hits = [d for d in cache_hit_data if d['cache_hit']]
                cache_hit_rate = (len(cache_hits) / len(cache_hit_data)) * 100 if cache_hit_data else 0
                improvement_percent = ((avg_cold_time - avg_warm_time) / avg_cold_time) * 100 if avg_cold_time > 0 else 0
                
                results[test_case['name']] = {
                    'description': test_case['description'],
                    'cold_cache_avg_ms': round(avg_cold_time, 2),
                    'cold_cache_min_ms': round(min(cold_times), 2) if cold_times else 0,
                    'cold_cache_max_ms': round(max(cold_times), 2) if cold_times else 0,
                    'warm_cache_avg_ms': round(avg_warm_time, 2),
                    'warm_cache_min_ms': round(min(warm_times), 2) if warm_times else 0,
                    'warm_cache_max_ms': round(max(warm_times), 2) if warm_times else 0,
                    'cache_hit_rate_percent': round(cache_hit_rate, 1),
                    'performance_improvement_percent': round(improvement_percent, 1),
                    'sample_alert_count': cache_hit_data[0]['alert_count'] if cache_hit_data else 0,
                    'total_runs': len(cache_hit_data),
                    'raw_data': cache_hit_data
                }
                
                print(f"   Cold cache: {avg_cold_time:.1f}ms (min: {min(cold_times):.1f}, max: {max(cold_times):.1f})")
                print(f"   Warm cache: {avg_warm_time:.1f}ms (min: {min(warm_times):.1f}, max: {max(warm_times):.1f})")
                print(f"   Cache hit rate: {cache_hit_rate:.1f}%")
                print(f"   Performance improvement: {improvement_percent:.1f}%")
                print(f"   Alert count: {cache_hit_data[0]['alert_count'] if cache_hit_data else 0}")
            else:
                results[test_case['name']] = {
                    'description': test_case['description'],
                    'error': 'No successful requests',
                    'raw_data': cache_hit_data
                }
                print(f"   ❌ Test failed - no successful requests")
        
        return results

    async def test_cache_patterns(self) -> Dict[str, Any]:
        """Analyze cache hit patterns for overlapping viewports"""
        
        print("\n\n📊 Testing Cache Hit Patterns")
        print("=" * 50)
        
        scenarios = [
            # Test overlapping viewports
            {'bbox': '40.75,-74.0,40.76,-73.99', 'name': 'viewport_a'},
            {'bbox': '40.755,-74.005,40.765,-73.995', 'name': 'viewport_b_overlap'},
            {'bbox': '40.76,-74.01,40.77,-74.00', 'name': 'viewport_c_adjacent'},
            # Test zoom level transitions
            {'bbox': '40.7,-74.1,40.8,-73.9', 'name': 'zoom_out_borough'},
            {'bbox': '40.74,-74.02,40.78,-73.98', 'name': 'zoom_in_neighborhood'},
            {'bbox': '40.755,-74.005,40.765,-73.995', 'name': 'zoom_in_street'}
        ]
        
        results = {}
        
        for scenario in scenarios:
            endpoint = f"/api/alerts/viewport?bbox={scenario['bbox']}&start_date=2024-01-01&end_date=2024-01-07"
            
            # First request (should be cache miss)
            result1 = await self.make_request(endpoint, f"{scenario['name']} - first request")
            await asyncio.sleep(0.1)
            
            # Second request (should be cache hit)
            result2 = await self.make_request(endpoint, f"{scenario['name']} - second request")
            
            if result1['success'] and result2['success']:
                perf1 = result1['data'].get('performance', {})
                perf2 = result2['data'].get('performance', {})
                
                results[scenario['name']] = {
                    'bbox': scenario['bbox'],
                    'first_request': {
                        'cache_hit': perf1.get('cache_hit', False),
                        'response_time': result1['response_time'],
                        'cache_key_type': perf1.get('cache_key_type', 'unknown'),
                        'query_type': perf1.get('query_type', 'unknown')
                    },
                    'second_request': {
                        'cache_hit': perf2.get('cache_hit', False),
                        'response_time': result2['response_time'],
                        'cache_key_type': perf2.get('cache_key_type', 'unknown'),
                        'query_type': perf2.get('query_type', 'unknown')
                    }
                }
                
                print(f"{scenario['name']}: Hit1={perf1.get('cache_hit', False)}, Hit2={perf2.get('cache_hit', False)}, Type={perf2.get('cache_key_type', 'N/A')}")
            else:
                results[scenario['name']] = {
                    'error': 'Request failed',
                    'first_request': result1,
                    'second_request': result2
                }
                print(f"{scenario['name']}: ❌ Request failed")
        
        return results

    async def test_concurrent_load(self, concurrent_users: int = 3, duration: int = 15) -> Dict[str, Any]:
        """Simulate concurrent user load"""
        
        print(f"\n\n⚡ Load Testing: {concurrent_users} concurrent users for {duration}s")
        print("=" * 50)
        
        start_time = time.time()
        all_results = []
        
        async def user_simulation(user_id: int):
            """Simulate a single user's behavior"""
            user_results = []
            
            # Different viewport scenarios to simulate real usage
            scenarios = [
                '40.75,-74.0,40.76,-73.99',  # Street level
                '40.7,-74.1,40.8,-73.9',     # Borough level  
                '40.6,-74.2,40.9,-73.7',     # City wide
            ]
            
            while time.time() - start_time < duration:
                bbox = scenarios[int(time.time() * user_id) % len(scenarios)]  # Pseudo-random selection
                endpoint = f"/api/alerts/viewport?bbox={bbox}&start_date=2024-01-01&end_date=2024-01-07"
                
                result = await self.make_request(endpoint, f"User {user_id}")
                
                if result['success']:
                    perf_data = result['data'].get('performance', {})
                    user_results.append({
                        'user_id': user_id,
                        'response_time': result['response_time'],
                        'cache_hit': perf_data.get('cache_hit', False),
                        'alert_count': len(result['data'].get('alerts', [])),
                        'timestamp': time.time()
                    })
                else:
                    user_results.append({
                        'user_id': user_id,
                        'error': result.get('error', 'Unknown error'),
                        'response_time': result['response_time'],
                        'timestamp': time.time()
                    })
                
                # Random delay between requests (2-6 seconds) - more reasonable for testing
                await asyncio.sleep(2 + (time.time() * user_id % 4))
            
            return user_results
        
        # Run concurrent user simulations
        tasks = [user_simulation(user_id) for user_id in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)
        
        # Flatten results
        for user_result in user_results:
            all_results.extend(user_result)
        
        # Calculate statistics
        successful_requests = [r for r in all_results if 'error' not in r]
        failed_requests = [r for r in all_results if 'error' in r]
        
        if successful_requests:
            avg_response_time = statistics.mean([r['response_time'] for r in successful_requests])
            cache_hits = [r for r in successful_requests if r.get('cache_hit', False)]
            cache_hit_rate = (len(cache_hits) / len(successful_requests)) * 100
        else:
            avg_response_time = 0
            cache_hit_rate = 0
        
        total_requests = len(all_results)
        error_rate = (len(failed_requests) / total_requests) * 100 if total_requests > 0 else 0
        
        results = {
            'concurrent_users': concurrent_users,
            'duration_seconds': duration,
            'total_requests': total_requests,
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'avg_response_time_ms': round(avg_response_time, 2),
            'cache_hit_rate_percent': round(cache_hit_rate, 1),
            'error_rate_percent': round(error_rate, 1),
            'requests_per_second': round(total_requests / duration, 2),
            'raw_data': all_results
        }
        
        print(f"   Total requests: {total_requests}")
        print(f"   Successful: {len(successful_requests)}, Failed: {len(failed_requests)}")
        print(f"   Average response time: {avg_response_time:.1f}ms")
        print(f"   Cache hit rate: {cache_hit_rate:.1f}%")
        print(f"   Error rate: {error_rate:.1f}%")
        print(f"   Requests per second: {total_requests / duration:.1f}")
        
        return results

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        
        print("🚀 Starting Enhanced Alert Serving Strategy Performance Tests")
        print("=" * 70)
        print(f"Base URL: {self.base_url}")
        print(f"Test Time: {datetime.now().isoformat()}")
        print("=" * 70)
        
        # Run all test suites
        performance_results = await self.test_performance_scenarios()
        cache_patterns = await self.test_cache_patterns()
        load_results = await self.test_concurrent_load(3, 15)
        
        # Generate summary
        print("\n\n📋 Test Summary")
        print("=" * 50)
        
        if 'current_7_days' in performance_results and 'viewport_7_days' in performance_results:
            baseline = performance_results['current_7_days']
            new_system = performance_results['viewport_7_days']
            
            if 'cold_cache_avg_ms' in baseline and 'warm_cache_avg_ms' in new_system:
                improvement = ((baseline['cold_cache_avg_ms'] - new_system['warm_cache_avg_ms']) / baseline['cold_cache_avg_ms']) * 100
                print(f"Baseline (7 days): {baseline['cold_cache_avg_ms']}ms")
                print(f"New system (7 days): {new_system['warm_cache_avg_ms']}ms")
                print(f"Improvement: {improvement:.1f}%")
        
        if 'viewport_6_months' in performance_results:
            six_months = performance_results['viewport_6_months']
            if 'warm_cache_avg_ms' in six_months:
                print(f"6-month queries: {six_months['warm_cache_avg_ms']}ms ({six_months.get('cache_hit_rate_percent', 0)}% cache hit rate)")
        
        # Compile final results
        final_results = {
            'test_metadata': {
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'test_duration_seconds': time.time() - self.start_time if hasattr(self, 'start_time') else 0
            },
            'performance_scenarios': performance_results,
            'cache_patterns': cache_patterns,
            'load_testing': load_results
        }
        
        return final_results

    def generate_report(self, results: Dict[str, Any], output_file: str = "perf-test-api.txt"):
        """Generate a detailed performance test report"""
        
        # Ensure output file is in the performance directory
        import os
        if not os.path.isabs(output_file):
            # Get the directory where this script is located (performance directory)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, output_file)
        
        with open(output_file, 'w') as f:
            f.write("Enhanced Alert Serving Strategy - Performance Test Report\n")
            f.write("=" * 60 + "\n\n")
            
            # Test metadata
            metadata = results.get('test_metadata', {})
            f.write(f"Test Timestamp: {metadata.get('timestamp', 'Unknown')}\n")
            f.write(f"Base URL: {metadata.get('base_url', 'Unknown')}\n")
            f.write(f"Test Duration: {metadata.get('test_duration_seconds', 0):.1f} seconds\n\n")
            
            # Performance scenarios summary
            f.write("PERFORMANCE SCENARIOS SUMMARY\n")
            f.write("-" * 40 + "\n")
            
            perf_results = results.get('performance_scenarios', {})
            for test_name, test_data in perf_results.items():
                if isinstance(test_data, dict) and 'description' in test_data:
                    f.write(f"\n{test_name.upper()}:\n")
                    f.write(f"  Description: {test_data['description']}\n")
                    
                    if 'error' in test_data:
                        f.write(f"  Status: FAILED - {test_data['error']}\n")
                    else:
                        f.write(f"  Cold Cache Avg: {test_data.get('cold_cache_avg_ms', 0)}ms\n")
                        f.write(f"  Warm Cache Avg: {test_data.get('warm_cache_avg_ms', 0)}ms\n")
                        f.write(f"  Cache Hit Rate: {test_data.get('cache_hit_rate_percent', 0)}%\n")
                        f.write(f"  Performance Improvement: {test_data.get('performance_improvement_percent', 0)}%\n")
                        f.write(f"  Sample Alert Count: {test_data.get('sample_alert_count', 0)}\n")
            
            # Cache patterns analysis
            f.write("\n\nCACHE PATTERNS ANALYSIS\n")
            f.write("-" * 40 + "\n")
            
            cache_results = results.get('cache_patterns', {})
            for pattern_name, pattern_data in cache_results.items():
                if isinstance(pattern_data, dict):
                    f.write(f"\n{pattern_name}:\n")
                    if 'error' in pattern_data:
                        f.write(f"  Status: FAILED - {pattern_data['error']}\n")
                    else:
                        first = pattern_data.get('first_request', {})
                        second = pattern_data.get('second_request', {})
                        f.write(f"  First Request: Cache Hit = {first.get('cache_hit', False)}, Time = {first.get('response_time', 0):.1f}ms\n")
                        f.write(f"  Second Request: Cache Hit = {second.get('cache_hit', False)}, Time = {second.get('response_time', 0):.1f}ms\n")
                        f.write(f"  Cache Key Type: {second.get('cache_key_type', 'unknown')}\n")
            
            # Load testing results
            f.write("\n\nLOAD TESTING RESULTS\n")
            f.write("-" * 40 + "\n")
            
            load_results = results.get('load_testing', {})
            if load_results:
                f.write(f"Concurrent Users: {load_results.get('concurrent_users', 0)}\n")
                f.write(f"Test Duration: {load_results.get('duration_seconds', 0)} seconds\n")
                f.write(f"Total Requests: {load_results.get('total_requests', 0)}\n")
                f.write(f"Successful Requests: {load_results.get('successful_requests', 0)}\n")
                f.write(f"Failed Requests: {load_results.get('failed_requests', 0)}\n")
                f.write(f"Average Response Time: {load_results.get('avg_response_time_ms', 0)}ms\n")
                f.write(f"Cache Hit Rate: {load_results.get('cache_hit_rate_percent', 0)}%\n")
                f.write(f"Error Rate: {load_results.get('error_rate_percent', 0)}%\n")
                f.write(f"Requests Per Second: {load_results.get('requests_per_second', 0)}\n")
            
            # Success criteria evaluation
            f.write("\n\nSUCCESS CRITERIA EVALUATION\n")
            f.write("-" * 40 + "\n")
            
            # Check cache hit rate target (>75%)
            overall_cache_hit_rates = []
            for test_data in perf_results.values():
                if isinstance(test_data, dict) and 'cache_hit_rate_percent' in test_data:
                    overall_cache_hit_rates.append(test_data['cache_hit_rate_percent'])
            
            if overall_cache_hit_rates:
                avg_cache_hit_rate = sum(overall_cache_hit_rates) / len(overall_cache_hit_rates)
                f.write(f"Average Cache Hit Rate: {avg_cache_hit_rate:.1f}% (Target: >75%)\n")
                f.write(f"Cache Hit Rate Status: {'✅ PASS' if avg_cache_hit_rate > 75 else '❌ FAIL'}\n")
            
            # Check load testing error rate (<5%)
            if load_results:
                error_rate = load_results.get('error_rate_percent', 100)
                f.write(f"Load Test Error Rate: {error_rate}% (Target: <5%)\n")
                f.write(f"Error Rate Status: {'✅ PASS' if error_rate < 5 else '❌ FAIL'}\n")
            
            f.write("\n\nRAW DATA (JSON)\n")
            f.write("-" * 40 + "\n")
            f.write(json.dumps(results, indent=2))
        
        print(f"\n📄 Detailed report saved to: {output_file}")

async def main():
    # Generate default output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_output = f"perf-test-api-{timestamp}.txt"
    
    parser = argparse.ArgumentParser(description='Test the viewport endpoint performance')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL of the API (default: http://localhost:8000)')
    parser.add_argument('--auth-token', default=None,
                       help='Authentication token for API requests')
    parser.add_argument('--output-file', default=default_output,
                       help=f'Output file for test results (default: {default_output})')
    parser.add_argument('--perf-test', action='store_true',
                       help='Enable performance testing mode (sets PERF_TEST=true to bypass auth)')
    
    args = parser.parse_args()
    
    # Set environment variable for performance testing if requested
    if args.perf_test:
        import os
        os.environ['PERF_TEST'] = 'true'
        print("🚀 Performance testing mode enabled - authentication bypassed")
        print("⚠️  IMPORTANT: Make sure the backend server was started with:")
        print("   PERF_TEST=true make run")
    else:
        print("⚠️  WARNING: Running without --perf-test flag. Authentication is required!")
        print("   Add --perf-test to bypass authentication for local testing.")
        print("   Example: poetry run python performance/test_viewport_performance.py --perf-test")
    
    # Test the basic connection first
    print(f"🔗 Testing connection to {args.base_url}...")
    
    async with ViewportPerformanceTester(args.base_url, args.auth_token) as tester:
        tester.start_time = time.time()
        
        try:
            # Run comprehensive test suite
            results = await tester.run_all_tests()
            
            # Generate report
            tester.generate_report(results, args.output_file)
            
            print(f"\n🎉 Performance testing completed!")
            print(f"📊 Results saved to: {args.output_file}")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            # Save error details
            error_results = {
                'test_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'base_url': args.base_url,
                    'error': str(e)
                },
                'error': str(e)
            }
            tester.generate_report(error_results, args.output_file)
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
