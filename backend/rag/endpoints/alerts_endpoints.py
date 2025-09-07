from monitor.types.alert_categories import get_categories_summary, ALERT_TYPES, categorize_311_complaint, get_alert_type_info, normalize_category, get_main_categories
from fastapi import APIRouter, HTTPException, Query, Depends
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore
from ..config import get_config
from ..auth import verify_session
from ..exceptions import AlertError, DatabaseError
import os
import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Any, Optional
import time
import difflib
import math
import hashlib

# Import the new categorization system
import sys
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)

# Initialize router
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])

# Simple in-memory cache
_cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

# NYC bounding box constants
NYC_BOUNDS = {
    'north': 40.92,   # Northernmost point of NYC
    'south': 40.49,   # Southernmost point of NYC  
    'east': -73.70,   # Easternmost point of NYC
    'west': -74.27    # Westernmost point of NYC
}


def get_db():
    """Get Firestore client instance"""
    return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)


def get_cache_key(limit: int, hours: int) -> str:
    """Generate cache key for alerts query"""
    return f"alerts:{limit}:{hours}"


def is_within_nyc(bbox: str) -> bool:
    """Check if bbox is entirely within NYC bounds"""
    try:
        lat1, lng1, lat2, lng2 = map(float, bbox.split(','))
        return (
            lat1 >= NYC_BOUNDS['south'] and lat2 <= NYC_BOUNDS['north'] and
            lng1 >= NYC_BOUNDS['west'] and lng2 <= NYC_BOUNDS['east']
        )
    except (ValueError, IndexError):
        return False


def get_viewport_cache_key(bbox: str, start_date: str, end_date: str) -> str:
    """Generate NYC-optimized cache key for viewport queries"""
    try:
        lat1, lng1, lat2, lng2 = map(float, bbox.split(','))
        
        # Handle requests outside NYC with special metro area cache
        if not is_within_nyc(bbox):
            return f"metro_area:{start_date}:{end_date}"
        
        # Calculate viewport size for NYC-specific grid sizing
        bbox_width = abs(lng2 - lng1)
        bbox_height = abs(lat2 - lat1)
        bbox_area = bbox_width * bbox_height
        
        # NYC-optimized grid sizes
        if bbox_area > 0.05:  # City-wide view (>50% of NYC)
            grid_size = 0.02
            cache_prefix = "city"
        elif bbox_area > 0.01:  # Borough view (10-50% of NYC)
            grid_size = 0.01
            cache_prefix = "borough"
        elif bbox_area > 0.002:  # Neighborhood view (2-10% of NYC)
            grid_size = 0.005
            cache_prefix = "neighborhood" 
        else:  # Street level (<2% of NYC)
            grid_size = 0.002
            cache_prefix = "street"
        
        # Snap viewport to grid boundaries
        lat1_grid = math.floor(lat1 / grid_size) * grid_size
        lng1_grid = math.floor(lng1 / grid_size) * grid_size  
        lat2_grid = math.ceil(lat2 / grid_size) * grid_size
        lng2_grid = math.ceil(lng2 / grid_size) * grid_size
        
        return f"viewport:{cache_prefix}:{grid_size}:{lat1_grid},{lng1_grid},{lat2_grid},{lng2_grid}:{start_date}:{end_date}"
    
    except (ValueError, IndexError) as e:
        logger.warning(f"Invalid bbox format '{bbox}': {e}")
        # Fallback to simple hash-based key
        bbox_hash = hashlib.md5(bbox.encode()).hexdigest()[:8]
        return f"viewport_fallback:{bbox_hash}:{start_date}:{end_date}"


def is_cache_valid(timestamp: float) -> bool:
    """Check if cache entry is still valid"""
    return (time.time() - timestamp) < CACHE_TTL_SECONDS


def get_cached_alerts(limit: int, hours: int):
    """Get alerts from cache if available and valid"""
    cache_key = get_cache_key(limit, hours)

    if cache_key in _cache:
        entry = _cache[cache_key]
        if is_cache_valid(entry['timestamp']):
            logger.info(f"✅ Cache HIT for {cache_key}")
            # Mark the cached response as cached
            cached_data = entry['data'].copy()
            if 'performance' in cached_data:
                cached_data['performance']['cached'] = True
                cached_data['performance']['cache_age_seconds'] = round(
                    time.time() - entry['timestamp'], 2)
            return cached_data
        else:
            # Remove expired cache entry
            del _cache[cache_key]
            logger.info(f"🗑️ Cache EXPIRED for {cache_key}")

    logger.info(f"❌ Cache MISS for {cache_key}")
    return None


def cache_alerts(limit: int, hours: int, data):
    """Cache alerts data with current timestamp"""
    cache_key = get_cache_key(limit, hours)
    _cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }
    logger.info(f"💾 Cached data for {cache_key}")

    # Simple cache cleanup - remove entries older than 1 hour
    cutoff = time.time() - 3600  # 1 hour
    expired_keys = [k for k, v in _cache.items() if v['timestamp'] < cutoff]
    for key in expired_keys:
        del _cache[key]

    if expired_keys:
        logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")


def normalize_311_signal(signal: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Normalize NYC 311 signal to alert format for frontend compatibility
    """
    try:
        return {
            'id': signal.get('unique_key', signal.get('id', '')),
            'title': f"{signal.get('complaint_type', 'Unknown')}: {signal.get('descriptor', '')[:50]}",
            'description': signal.get('descriptor', ''),
            'source': '311',
            'priority': 'high' if signal.get('is_emergency', False) else 'medium',
            'status': _normalize_311_alert_status(signal.get('status', 'Open')),
            'timestamp': _extract_311_timestamp(signal),
            'neighborhood': signal.get('full_signal_data', {}).get('metadata', {}).get('incident_zip', signal.get('incident_zip', 'Unknown')),
            'borough': signal.get('full_signal_data', {}).get('metadata', {}).get('borough', signal.get('borough', 'Unknown')),
            'coordinates': {
                'lat': signal.get('latitude') or 40.7589,
                'lng': signal.get('longitude') or -73.9851
            } if signal.get('latitude') and signal.get('longitude') else {
                'lat': 40.7589, 'lng': -73.9851
            },
            'area': signal.get('borough', 'Unknown'),
            'venue_address': '',
            'specific_streets': [],
            'cross_streets': [],
            'crowd_impact': 'unknown',
            'transportation_impact': '',
            'estimated_attendance': '',
            'severity': 7 if signal.get('is_emergency', False) else 3,
            'keywords': [signal.get('complaint_type', '')],
            'signals': ['311'],
            'url': f"https://portal.311.nyc.gov/article/?kanumber=KA-01010",

            # Simplified categorization - just the main category
            'category': normalize_category(signal.get('category', 'general')),

            # NYC 311 specific metadata
            'complaint_type': signal.get('complaint_type', ''),
            'agency': signal.get('agency_name', ''),
            'incident_zip': signal.get('incident_zip', ''),
            'signal_category': signal.get('signal_category', ''),
            'is_emergency': signal.get('is_emergency', False),
            'is_event': signal.get('is_event', False),
        }
    except Exception as e:
        logger.error(f"Error normalizing 311 signal: {e}")
        # Return minimal fallback
        return {
            'id': signal.get('unique_key', 'unknown'),
            'title': signal.get('complaint_type', 'NYC 311 Request'),
            'description': signal.get('descriptor', ''),
            'source': '311',
            'priority': 'medium',
            'status': _normalize_311_alert_status('Open'),
            'timestamp': datetime.utcnow().isoformat(),
            'neighborhood': signal.get('borough', 'Unknown'),
            'borough': signal.get('borough', 'Unknown'),
            'coordinates': {'lat': 40.7589, 'lng': -73.9851},
            'area': signal.get('borough', 'Unknown'),
            'severity': 3,
            'keywords': [],
            'signals': ['311'],
            'url': "https://portal.311.nyc.gov/article/?kanumber=KA-01010"
        }


def query_alerts_in_bbox_and_daterange(bbox: str, start_date: str, end_date: str, limit: int = 2000) -> List[Dict]:
    """
    Query alerts within a bounding box and date range from both collections
    
    Args:
        bbox: "lat1,lng1,lat2,lng2" format
        start_date: "YYYY-MM-DD" format  
        end_date: "YYYY-MM-DD" format
        limit: Maximum alerts to return
        
    Returns:
        List of normalized alert dictionaries
    """
    try:
        lat1, lng1, lat2, lng2 = map(float, bbox.split(','))
        
        # Convert date strings to datetime objects
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include full end day
        
        db = get_db()
        all_alerts = []
        
        # Allocate limits between collections
        monitor_limit = min(600, int(limit * 0.3))  # 30% for monitor alerts
        signals_limit = limit - monitor_limit       # 70% for 311 signals
        
        # Query 1: Monitor alerts with spatial and temporal filters
        try:
            alerts_ref = db.collection('nyc_monitor_alerts')
            
            # Temporal filter first (most selective)
            temporal_query = alerts_ref.where('created_at', '>=', start_datetime).where('created_at', '<', end_datetime)
            
            monitor_count = 0
            for doc in temporal_query.limit(monitor_limit * 2).stream():  # Get extra to account for spatial filtering
                if monitor_count >= monitor_limit:
                    break
                    
                data = doc.to_dict()
                
                # Extract coordinates from nested structure
                coords = data.get('original_alert', {})
                alert_lat = coords.get('latitude')
                alert_lng = coords.get('longitude')
                
                # Skip if no coordinates
                if alert_lat is None or alert_lng is None:
                    continue
                
                # Spatial filter: check if alert is within bbox
                if not (lat1 <= alert_lat <= lat2 and lng1 <= alert_lng <= lng2):
                    continue
                
                # Extract the real source from nested structure
                real_source = 'monitor'  # Default fallback
                try:
                    original_alert = data.get('original_alert', {})
                    if original_alert:
                        original_alert_data = original_alert.get('original_alert_data', {})
                        if original_alert_data:
                            signals = original_alert_data.get('signals', [])
                            if signals and len(signals) > 0:
                                real_source = signals[0]
                except Exception:
                    pass  # Keep default
                
                # Create normalized alert
                alert = {
                    'id': doc.id,
                    'title': data.get('title', 'NYC Alert'),
                    'description': data.get('description', ''),
                    'source': real_source,
                    'priority': _get_priority_from_severity(data.get('severity', 5)),
                    'severity': data.get('severity', 5),
                    'timestamp': _extract_monitor_timestamp(data),
                    'coordinates': {
                        'lat': alert_lat,
                        'lng': alert_lng
                    },
                    'neighborhood': coords.get('neighborhood', 'Unknown'),
                    'borough': coords.get('borough', 'Unknown'),
                    'category': normalize_category(data.get('category', 'general')),
                }
                all_alerts.append(alert)
                monitor_count += 1
                
        except Exception as e:
            logger.error(f"Error querying monitor alerts: {e}")
        
        # Query 2: 311 signals with spatial and temporal filters
        try:
            signals_ref = db.collection('nyc_311_signals')
            
            # Temporal filter first
            temporal_query = signals_ref.where('signal_timestamp', '>=', start_datetime).where('signal_timestamp', '<', end_datetime)
            
            signals_count = 0
            for doc in temporal_query.limit(signals_limit * 2).stream():  # Get extra to account for spatial filtering
                if signals_count >= signals_limit:
                    break
                    
                data = doc.to_dict()
                
                # Extract coordinates directly
                alert_lat = data.get('latitude')
                alert_lng = data.get('longitude')
                
                # Skip if no coordinates
                if alert_lat is None or alert_lng is None:
                    continue
                
                # Spatial filter: check if alert is within bbox
                if not (lat1 <= alert_lat <= lat2 and lng1 <= alert_lng <= lng2):
                    continue
                
                # Use calculated severity from rule-based triage
                severity = data.get('severity')
                if severity is None:
                    severity = 7 if data.get('is_emergency', False) else 3
                
                # Get categorization
                complaint_type = data.get('complaint_type', '')
                category = data.get('category')
                if not category:
                    event_type = data.get('event_type') or categorize_311_complaint(complaint_type)
                    alert_type_info = get_alert_type_info(event_type)
                    category = alert_type_info.category.value
                
                # Create normalized alert
                alert = {
                    'id': doc.id,
                    'title': f"{complaint_type}: {data.get('descriptor', '')[:50]}",
                    'description': data.get('descriptor', ''),
                    'source': '311',
                    'priority': _get_priority_from_severity(severity),
                    'severity': severity,
                    'timestamp': data.get('signal_timestamp', datetime.utcnow()).isoformat(),
                    'coordinates': {
                        'lat': alert_lat,
                        'lng': alert_lng
                    },
                    'neighborhood': data.get('incident_zip', 'Unknown'),
                    'borough': data.get('borough', 'Unknown'),
                    'category': normalize_category(category),
                    'complaint_type': complaint_type,
                    'agency': data.get('agency_name', ''),
                    'is_emergency': data.get('is_emergency', False),
                }
                all_alerts.append(alert)
                signals_count += 1
                
        except Exception as e:
            logger.error(f"Error querying 311 signals: {e}")
        
        logger.info(f"Spatial query returned {len(all_alerts)} alerts from bbox {bbox}")
        return all_alerts
        
    except Exception as e:
        logger.error(f"Error in spatial query: {e}")
        return []


def get_metro_area_highlights(start_date: str, end_date: str, limit: int = 100) -> List[Dict]:
    """Return high-priority alerts for metro area view (outside NYC bounds)"""
    bbox = f"{NYC_BOUNDS['south']},{NYC_BOUNDS['west']},{NYC_BOUNDS['north']},{NYC_BOUNDS['east']}"
    
    # Get all alerts from NYC area
    all_alerts = query_alerts_in_bbox_and_daterange(bbox, start_date, end_date, limit * 3)
    
    # Filter for high-severity alerts only
    high_priority_alerts = [
        alert for alert in all_alerts 
        if alert.get('severity', 0) >= 7  # Only critical alerts
    ]
    
    # Sort by severity descending, then by timestamp
    high_priority_alerts.sort(
        key=lambda x: (x.get('severity', 0), x.get('timestamp', '')), 
        reverse=True
    )
    
    return high_priority_alerts[:limit]


def is_recent_data(start_date: str) -> bool:
    """Check if the start date is within the last 7 days (recent data)"""
    try:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        return start_datetime >= cutoff_date
    except ValueError:
        return False


# Define the viewport endpoint with conditional authentication
if os.getenv('PERF_TEST', '').lower() == 'true':
    # Performance testing mode - no auth required
    @alerts_router.get('/viewport')
    async def get_viewport_alerts(
        bbox: str = Query(..., description="Bounding box as 'lat1,lng1,lat2,lng2'"),
        start_date: str = Query(..., description="Start date as 'YYYY-MM-DD'"),
        end_date: str = Query(..., description="End date as 'YYYY-MM-DD'"),
        limit: int = Query(2000, ge=1, le=50000, description="Maximum alerts to return")
    ):
        """
        Get alerts within a specific viewport (bounding box) and date range
        
        Uses NYC-optimized spatial grid caching for enhanced performance:
        - Different grid sizes based on zoom level (city/borough/neighborhood/street)
        - Special handling for viewports outside NYC (metro area highlights)
        - Comprehensive performance instrumentation
        - Extended historical data support (6+ months)
        
        **PERF_TEST MODE**: Authentication bypassed for testing
        """
        user = {"email": "perf-test@example.com", "testing": True}
        
        # Function body continues below...
        return await _viewport_alerts_implementation(bbox, start_date, end_date, limit, user)
        
else:
    # Production mode - authentication required
    @alerts_router.get('/viewport')
    async def get_viewport_alerts(
        bbox: str = Query(..., description="Bounding box as 'lat1,lng1,lat2,lng2'"),
        start_date: str = Query(..., description="Start date as 'YYYY-MM-DD'"),
        end_date: str = Query(..., description="End date as 'YYYY-MM-DD'"),
        limit: int = Query(2000, ge=1, le=50000, description="Maximum alerts to return"),
        user=Depends(verify_session)
    ):
        """
        Get alerts within a specific viewport (bounding box) and date range
        
        Uses NYC-optimized spatial grid caching for enhanced performance:
        - Different grid sizes based on zoom level (city/borough/neighborhood/street)
        - Special handling for viewports outside NYC (metro area highlights)
        - Comprehensive performance instrumentation
        - Extended historical data support (6+ months)
        
        **Requires authentication**: Valid Google OAuth token
        """
        
        # Function body continues below...
        return await _viewport_alerts_implementation(bbox, start_date, end_date, limit, user)


async def _viewport_alerts_implementation(bbox: str, start_date: str, end_date: str, limit: int, user: Dict[str, Any]):
    """Implementation of viewport alerts logic shared between auth and no-auth versions"""
    # Input validation with normalization
    try:
        lat1, lng1, lat2, lng2 = map(float, bbox.split(','))
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lng1 <= 180 and -180 <= lng2 <= 180):
            raise AlertError("Invalid latitude/longitude values")
        
        # Normalize bounding box to ensure consistent ordering for caching
        lat1, lat2 = min(lat1, lat2), max(lat1, lat2)
        lng1, lng2 = min(lng1, lng2), max(lng1, lng2)
        
        # Calculate bbox area for optimization decisions
        bbox_area = (lat2 - lat1) * (lng2 - lng1)
        if bbox_area > 1.0:  # Very large area (>111km x 111km)
            logger.warning(f"⚠️ Large viewport request: {bbox_area:.4f} sq degrees for user {user.get('email')}")
            # Could implement stricter limits or different caching strategy for very large areas
    except (ValueError, IndexError):
        raise AlertError("Invalid bbox format. Use 'lat1,lng1,lat2,lng2'")
    
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        raise AlertError("Invalid date format. Use 'YYYY-MM-DD'")
    
    if limit < 1 or limit > 50000:
        raise AlertError("Limit must be between 1 and 50000")
    
    logger.info(f"🔒 Authenticated user {user.get('email')} accessing viewport alerts")
    logger.info(f"📍 Viewport: {bbox}, Date range: {start_date} to {end_date}")
    
    # Performance timing
    start_time = time.time()
    cache_start = time.time()
    
    # Generate cache key using NYC-optimized strategy
    cache_key = get_viewport_cache_key(bbox, start_date, end_date)
    
    # Try cache first
    cached = _cache.get(cache_key)
    cache_time = time.time() - cache_start
    
    if cached and is_cache_valid(cached['timestamp']):
        total_time = time.time() - start_time
        cached_data = cached['data'].copy()
        
        # Add cache hit performance metrics
        cached_data['performance'].update({
            'total_time_ms': round(total_time * 1000, 2),
            'cache_hit': True,
            'cache_time_ms': round(cache_time * 1000, 2),
            'cache_age_seconds': round(time.time() - cached['timestamp'], 2),
            'source': 'in_memory_cache'
        })
        
        logger.info(f"✅ Cache HIT for {cache_key} ({round(total_time * 1000)}ms)")
        return cached_data
    
    logger.info(f"❌ Cache MISS for {cache_key}")
    
    # Database query with timing
    db_start = time.time()
    
    # Handle metro area requests (outside NYC)
    if cache_key.startswith("metro_area:"):
        alerts = get_metro_area_highlights(start_date, end_date, min(limit, 100))
        query_type = "metro_area_highlights"
    else:
        alerts = query_alerts_in_bbox_and_daterange(bbox, start_date, end_date, limit)
        query_type = "spatial_query"
    
    db_time = time.time() - db_start
    
    # Cache write timing
    cache_write_start = time.time()
    
    # Determine TTL based on data recency
    ttl = 3600 if is_recent_data(start_date) else 86400  # 1 hour vs 24 hours
    
    # Prepare response with performance metrics
    response_data = {
        'alerts': alerts,
        'performance': {
            'total_time_ms': 0,  # Will be updated below
            'cache_hit': False,
            'db_query_time_ms': round(db_time * 1000, 2),
            'alert_count': len(alerts),
            'source': 'database_fresh',
            'query_type': query_type,
            'cache_key_type': cache_key.split(':')[0] if ':' in cache_key else 'unknown',
            'bbox': bbox,
            'date_range_days': (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days,
            'ttl_seconds': ttl
        }
    }
    
    # Cache the response
    _cache[cache_key] = {
        'data': response_data,
        'timestamp': time.time()
    }
    
    cache_write_time = time.time() - cache_write_start
    total_time = time.time() - start_time
    
    # Update final performance metrics
    response_data['performance'].update({
        'total_time_ms': round(total_time * 1000, 2),
        'cache_write_time_ms': round(cache_write_time * 1000, 2)
    })
    
    # Simple cache cleanup
    cutoff = time.time() - 3600  # 1 hour
    expired_keys = [k for k, v in _cache.items() if v['timestamp'] < cutoff]
    for key in expired_keys:
        del _cache[key]
    
    if expired_keys:
        logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    logger.info(f"✅ Viewport query completed: {len(alerts)} alerts in {round(total_time * 1000)}ms")
    return response_data


# Define the recent alerts endpoint with conditional authentication
if os.getenv('PERF_TEST', '').lower() == 'true':
    # Performance testing mode - no auth required
    @alerts_router.get('/recent')
    async def get_recent_alerts(
        limit: int = Query(2000, ge=1, le=50000,
                           description="Number of alerts to return"),
        hours: int = Query(24, ge=1, le=4380, description="Hours to look back (up to 6 months)")
    ):
        """
        Get recent alerts with MINIMAL data - ultra-fast for map display

        Returns only: title, description, source, severity, date, coordinates

        Optimizations:
        - Ultra-minimal field selection (8x speedup)
        - NO sorting
        - NO complex transformations
        - In-memory caching (5 min TTL)

        **PERF_TEST MODE**: Authentication bypassed for testing
        """
        user = {"email": "perf-test@example.com", "testing": True}
        return await _recent_alerts_implementation(limit, hours, user)
        
else:
    # Production mode - authentication required
    @alerts_router.get('/recent')
    async def get_recent_alerts(
        limit: int = Query(2000, ge=1, le=50000,
                           description="Number of alerts to return"),
        hours: int = Query(24, ge=1, le=4380, description="Hours to look back (up to 6 months)"),
        user=Depends(verify_session)
    ):
        """
        Get recent alerts with MINIMAL data - ultra-fast for map display

        Returns only: title, description, source, severity, date, coordinates

        Optimizations:
        - Ultra-minimal field selection (8x speedup)
        - NO sorting
        - NO complex transformations
        - In-memory caching (5 min TTL)

        **Requires authentication**: Valid Google OAuth token
        """
        return await _recent_alerts_implementation(limit, hours, user)


async def _recent_alerts_implementation(limit: int, hours: int, user: Dict[str, Any]):
    """Implementation of recent alerts logic shared between auth and no-auth versions"""
    # Input validation
    if limit < 1 or limit > 50000:
        raise AlertError("Limit must be between 1 and 50000")

    if hours < 1 or hours > 4380:
        raise AlertError("Hours must be between 1 and 4380 (6 months)")

    logger.info(
        f"🔒 Authenticated user {user.get('email')} accessing recent alerts")

    # Check cache first
    cache_key = f"minimal:{limit}:{hours}"

    if cache_key in _cache:
        entry = _cache[cache_key]
        if is_cache_valid(entry['timestamp']):
            logger.info(f"✅ Cache HIT for {cache_key}")
            cached_data = entry['data'].copy()
            if 'performance' in cached_data:
                cached_data['performance']['cached'] = True
                cached_data['performance']['cache_age_seconds'] = round(
                    time.time() - entry['timestamp'], 2)
            return cached_data

    start_time = datetime.utcnow()
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Allocate limits
    monitor_limit = min(600, int(limit * 0.3))  # 30% for monitor
    signals_limit = limit - monitor_limit   # 70% for 311

    logger.info(
        f"🚀 MINIMAL FETCH: {monitor_limit} monitor + {signals_limit} 311")

    all_alerts = []
    query_stats = {}

    # Query 1: Monitor alerts - minimal fields
    monitor_start = datetime.utcnow()
    try:
        alerts_ref = db.collection('nyc_monitor_alerts')
        monitor_query = (alerts_ref
                         .where('created_at', '>=', cutoff_time)
                         .limit(monitor_limit))

        for doc in monitor_query.stream():
            data = doc.to_dict()

            # Extract the real source from the nested structure
            real_source = 'monitor'  # Default fallback
            try:
                original_alert = data.get('original_alert', {})
                if original_alert:
                    original_alert_data = original_alert.get(
                        'original_alert_data', {})
                    if original_alert_data:
                        signals = original_alert_data.get('signals', [])
                        if signals and len(signals) > 0:
                            # First signal is the true source (reddit, twitter, etc.)
                            real_source = signals[0]
            except Exception as e:
                logger.warning(
                    f"Could not extract source for alert {doc.id}: {e}")

            # Ultra-minimal transformation
            alert = {
                'id': doc.id,
                'title': data.get('title', 'NYC Alert'),
                'description': data.get('description', ''),
                # Now shows the actual source: reddit, twitter, etc.
                'source': real_source,
                'priority': _get_priority_from_severity(data.get('severity', 5)),
                'severity': data.get('severity', 5),
                'timestamp': _extract_monitor_timestamp(data),
                'coordinates': {
                    'lat': data.get('original_alert', {}).get('latitude', 40.7589),
                    'lng': data.get('original_alert', {}).get('longitude', -73.9851)
                },
                # Extract neighborhood and borough from original_alert
                'neighborhood': data.get('original_alert', {}).get('neighborhood', 'Unknown'),
                'borough': data.get('original_alert', {}).get('borough', 'Unknown'),
                # Simplified categorization - just the main category
                'category': normalize_category(data.get('category', 'general')),
            }
            all_alerts.append(alert)
            # logger.info(
            #     f"✅ Alert {doc.id} has priority: {alert.get('priority')}")

        monitor_time = (datetime.utcnow() - monitor_start).total_seconds()
        query_stats['monitor'] = {
            # Count non-311 alerts
            'count': len([a for a in all_alerts if a['source'] != '311']),
            'time_seconds': round(monitor_time, 3),
            # Show actual sources found
            'sources_found': list(set([a['source'] for a in all_alerts if a['source'] != '311']))
        }

    except Exception as e:
        logger.error(f"Monitor error: {e}")
        query_stats['monitor'] = {'error': str(e)}

    # Query 2: 311 signals - ultra-minimal fields
    signals_start = datetime.utcnow()
    try:
        signals_ref = db.collection('nyc_311_signals')
        signals_query = (signals_ref
                         .where('signal_timestamp', '>=', cutoff_time)
                         .select(['signal_timestamp', 'complaint_type', 'descriptor', 'latitude', 'longitude', 'is_emergency', 'category', 'full_signal_data', 'incident_zip', 'borough', 'status', 'severity', 'event_type'])
                         .limit(signals_limit))

        signals_count = 0
        for doc in signals_query.stream():
            data = doc.to_dict()

            # Use calculated severity from rule-based triage, fallback to emergency logic
            severity = data.get('severity')
            if severity is None:
                # Fallback for old records without severity
                severity = 7 if data.get('is_emergency', False) else 3

            # Get categorization (may be stored in DB or need to calculate)
            complaint_type = data.get('complaint_type', '')

            # Get the main category (simplified approach) - ORIGINAL OPTIMIZED LOGIC
            category = data.get('category')
            if not category:
                # Calculate from event_type if available, otherwise from complaint_type
                event_type = data.get(
                    'event_type') or categorize_311_complaint(complaint_type)
                alert_type_info = get_alert_type_info(event_type)
                category = alert_type_info.category.value

            # Create alert with proper status normalization
            alert = {
                'id': doc.id,
                'title': f"{complaint_type}: {(data.get('descriptor', '') or '')[:50]}",
                'description': data.get('descriptor', ''),
                'source': '311',
                'priority': _get_priority_from_severity(data.get('severity', 5)),
                # Proper status normalization
                'status': _normalize_311_alert_status(data.get('status', 'Open')),
                'severity': severity,
                'timestamp': _extract_311_timestamp(data),
                'coordinates': {
                    'lat': data.get('latitude', 40.7589),
                    'lng': data.get('longitude', -73.9851)
                },
                # Extract neighborhood and borough from full_signal_data.metadata
                'neighborhood': data.get('full_signal_data', {}).get('metadata', {}).get('incident_zip', data.get('incident_zip', 'Unknown')),
                'borough': data.get('full_signal_data', {}).get('metadata', {}).get('borough', data.get('borough', 'Unknown')),
                # Simplified categorization - just the main category (ORIGINAL LOGIC)
                'category': normalize_category(category),
            }

            all_alerts.append(alert)
            signals_count += 1

        signals_time = (datetime.utcnow() - signals_start).total_seconds()
        query_stats['311'] = {
            'count': signals_count,
            'time_seconds': round(signals_time, 3)
        }

    except Exception as e:
        logger.error(f"311 error: {e}")
        query_stats['311'] = {'error': str(e)}

    total_time = (datetime.utcnow() - start_time).total_seconds()

    # Deduplicate alerts by title (linear time) - EXCLUDE 311 alerts
    dedup_start = datetime.utcnow()

    # Separate 311 and non-311 alerts
    alerts_311 = [
        alert for alert in all_alerts if alert.get('source') == '311']
    alerts_non_311 = [
        alert for alert in all_alerts if alert.get('source') != '311']

    # Keep all 311 alerts (no deduplication)
    deduplicated_alerts = alerts_311.copy()

    # Deduplicate non-311 alerts using similarity detection
    seen_titles = []  # List of normalized titles for similarity comparison
    duplicate_count = 0
    similarity_threshold = 0.85  # 85% similarity threshold

    for alert in alerts_non_311:
        # Normalize title for comparison (lowercase, stripped, truncated)
        normalized_title = alert.get('title', '').lower().strip()[:150]

        if not normalized_title:
            continue

        is_duplicate = False

        # Check similarity against all seen titles
        for seen_title in seen_titles:
            similarity = difflib.SequenceMatcher(
                None, normalized_title, seen_title).ratio()
            if similarity >= similarity_threshold:
                is_duplicate = True
                duplicate_count += 1
                break

        if not is_duplicate:
            seen_titles.append(normalized_title)
            deduplicated_alerts.append(alert)

    dedup_time = (datetime.utcnow() - dedup_start).total_seconds()

    # Sort deduplicated alerts to prioritize Reddit first
    sort_start = datetime.utcnow()

    def get_source_priority(alert):
        """Return sort priority for sources (lower = higher priority)"""
        source = alert.get('source', 'unknown')
        if source == 'reddit':
            return 0  # Highest priority
        elif source == '311':
            return 1  # Second priority
        elif source == 'twitter':
            return 2  # Third priority
        else:
            return 3  # Everything else

    # Sort by source priority, then by timestamp (newest first)
    deduplicated_alerts.sort(key=lambda alert: (
        get_source_priority(alert),
        -int(datetime.fromisoformat(alert.get('timestamp',
             '1970-01-01T00:00:00').replace('Z', '+00:00')).timestamp())
    ))

    sort_time = (datetime.utcnow() - sort_start).total_seconds()

    logger.info(
        f"🔍 DEDUP: {len(all_alerts)} → {len(deduplicated_alerts)} alerts "
        f"({duplicate_count} non-311 duplicates removed, {len(alerts_311)} 311 alerts kept) "
        f"in {dedup_time:.3f}s")

    logger.info(
        f"📊 SORT: Prioritized Reddit alerts in {sort_time:.3f}s")

    logger.info(
        f"🎯 MINIMAL: {len(deduplicated_alerts)} alerts in {total_time:.3f}s ({len(deduplicated_alerts)/total_time:.0f} alerts/sec)")

    result = {
        'alerts': deduplicated_alerts,
        'count': len(deduplicated_alerts),
        'performance': {
            'total_time_seconds': round(total_time, 3),
            'alerts_per_second': round(len(deduplicated_alerts) / total_time if total_time > 0 else 0, 1),
            'query_breakdown': query_stats,
            'deduplication': {
                'original_count': len(all_alerts),
                'final_count': len(deduplicated_alerts),
                'duplicates_removed': duplicate_count,
                'alerts_311_kept': len(alerts_311),
                'similarity_threshold': similarity_threshold,
                'dedup_time_seconds': round(dedup_time, 3)
            },
            'optimizations': ['ultra_minimal_fields', 'no_sorting', 'minimal_transform', 'similarity_deduplication_non_311'],
            'cached': False,
            'cache_ttl_seconds': CACHE_TTL_SECONDS,
            'accessed_by': user.get('email')  # Track who accessed the data
        }
    }

    # Cache the result
    _cache[cache_key] = {
        'data': result,
        'timestamp': time.time()
    }

    return result


@alerts_router.get('/get/{alert_id}')
async def get_single_alert(alert_id: str, user=Depends(verify_session)):
    """
    Get a single alert with full details by ID

    Searches both collections (monitor and 311) for the alert ID
    Returns complete alert object with all available fields

    **Requires authentication**: Valid Google OAuth token
    """
    # Input validation
    if not alert_id or not alert_id.strip():
        raise AlertError("Alert ID is required")

    logger.info(
        f"🔒 Authenticated user {user.get('email')} accessing alert: {alert_id}")

    db = get_db()

    # Try monitor collection first
    try:
        monitor_doc = db.collection(
            'nyc_monitor_alerts').document(alert_id).get()
        if monitor_doc.exists:
            alert_data = monitor_doc.to_dict()
            alert_data['id'] = monitor_doc.id
            alert_data['source'] = 'monitor'

            logger.info(f"✅ Found monitor alert: {alert_id}")
            return {
                'alert': alert_data,
                'source_collection': 'nyc_monitor_alerts',
                'found': True,
                'accessed_by': user.get('email')
            }
    except Exception as e:
        logger.error(f"Error checking monitor collection: {e}")

    # Try 311 collection
    try:
        signals_doc = db.collection(
            'nyc_311_signals').document(alert_id).get()
        if signals_doc.exists:
            signal_data = signals_doc.to_dict()

            # Return full 311 signal with normalization for consistency
            normalized_signal = normalize_311_signal(signal_data)
            normalized_signal['id'] = signals_doc.id

            logger.info(f"✅ Found 311 signal: {alert_id}")
            return {
                'alert': normalized_signal,
                'source_collection': 'nyc_311_signals',
                'found': True,
                'accessed_by': user.get('email')
            }
    except Exception as e:
        logger.error(f"Error checking 311 collection: {e}")

    # Also try searching by unique_key for 311 signals
    try:
        signals_ref = db.collection('nyc_311_signals')
        query = signals_ref.where('unique_key', '==', alert_id).limit(1)
        docs = list(query.stream())

        if docs:
            doc = docs[0]
            signal_data = doc.to_dict()
            normalized_signal = normalize_311_signal(signal_data)
            normalized_signal['id'] = doc.id

            logger.info(f"✅ Found 311 signal by unique_key: {alert_id}")
            return {
                'alert': normalized_signal,
                'source_collection': 'nyc_311_signals',
                'found': True,
                'matched_by': 'unique_key',
                'accessed_by': user.get('email')
            }
    except Exception as e:
        logger.error(f"Error searching by unique_key: {e}")

    # Not found in any collection
    logger.warning(f"Alert not found: {alert_id}")
    raise AlertError(
        f"Alert with ID '{alert_id}' not found in any collection", alert_id=alert_id)


def _get_priority_from_severity(severity: int) -> str:
    """Convert severity number to priority string"""
    if severity >= 8:
        return 'critical'
    elif severity >= 6:
        return 'high'
    elif severity >= 4:
        return 'medium'
    else:
        return 'low'


def _normalize_311_alert_status(status: str) -> str:
    """
    Normalize alert status values to standard format with lowercase handling.

    Maps:
    - 'open' -> 'active'
    - 'assigned' -> 'investigating'
    - 'closed' -> 'resolved'

    All comparisons are done in lowercase to handle case variations.
    """
    if not status or not isinstance(status, str):
        return 'active'  # Default fallback

    status_lower = status.lower().strip()

    status_mapping = {
        'open': 'active',
        'unknown': 'active',
        'assigned': 'investigating',
        'closed': 'resolved'
    }

    return status_mapping.get(status_lower, status_lower)


def _extract_311_timestamp(data: dict) -> str:
    """
    Extract timestamp for 311 alerts with fallback logic
    Handles format: "Jun 18, 2025, 12:11:00.000 PM"
    1. Try signal_timestamp first
    2. Fall back to created_at
    3. Final fallback to current time
    """
    try:
        # First try signal_timestamp
        signal_timestamp = data.get('signal_timestamp')
        if signal_timestamp:
            if isinstance(signal_timestamp, datetime):
                return signal_timestamp.isoformat()
            elif isinstance(signal_timestamp, str) and signal_timestamp.strip():
                try:
                    # Handle the specific format: "Jun 18, 2025, 12:11:00.000 PM"
                    if 'AM' in signal_timestamp or 'PM' in signal_timestamp:
                        parsed = datetime.strptime(
                            signal_timestamp, "%b %d, %Y, %I:%M:%S.%f %p")
                        return parsed.isoformat()
                    else:
                        # Try standard ISO format parsing
                        parsed = datetime.fromisoformat(
                            signal_timestamp.replace('Z', '+00:00'))
                        return parsed.isoformat()
                except:
                    # If parsing fails, continue to fallback
                    pass

        # Fall back to created_at
        created_at = data.get('created_at')
        if created_at:
            if isinstance(created_at, datetime):
                return created_at.isoformat()
            elif isinstance(created_at, str) and created_at.strip():
                try:
                    parsed = datetime.fromisoformat(
                        created_at.replace('Z', '+00:00'))
                    return parsed.isoformat()
                except:
                    return created_at

        # Final fallback to current time
        return datetime.utcnow().isoformat()

    except Exception as e:
        logger.warning(f"Error extracting 311 timestamp: {e}")
        return datetime.utcnow().isoformat()


def _extract_monitor_timestamp(data: dict) -> str:
    """
    Extract timestamp for monitor alerts from original_alert
    Tries multiple timestamp fields in order of preference
    """
    try:
        original_alert = data.get('original_alert', {})

        # Try timestamp first (likely the original Reddit post timestamp)
        timestamp = original_alert.get('timestamp')
        if timestamp:
            if isinstance(timestamp, datetime):
                return timestamp.isoformat()
            elif isinstance(timestamp, str) and timestamp.strip():
                return timestamp

        # Try event_date_str (date format like "2025-06-14")
        event_date_str = original_alert.get('event_date_str')
        if event_date_str and event_date_str.strip():
            return event_date_str

        # Try time_created as another fallback
        time_created = original_alert.get('time_created')
        if time_created:
            if isinstance(time_created, datetime):
                return time_created.isoformat()
            elif isinstance(time_created, str) and time_created.strip():
                return time_created

        # Also try some other potential timestamp fields
        for field in ['created_at', 'date_created', 'event_date']:
            value = original_alert.get(field)
            if value:
                if isinstance(value, datetime):
                    return value.isoformat()
                elif isinstance(value, str) and value.strip():
                    return value

        # Final fallback to current time
        return datetime.utcnow().isoformat()

    except Exception as e:
        logger.warning(f"Error extracting monitor timestamp: {e}")
        return datetime.utcnow().isoformat()


@alerts_router.get('/cache/info')
async def get_cache_info(user=Depends(verify_session)):
    """
    Get information about current cache state

    **Requires authentication**: Valid Google OAuth token
    """
    logger.info(
        f"🔒 Authenticated user {user.get('email')} accessing cache info")

    current_time = time.time()
    cache_info = {}

    for key, entry in _cache.items():
        age_seconds = current_time - entry['timestamp']
        is_valid = is_cache_valid(entry['timestamp'])

        cache_info[key] = {
            'age_seconds': round(age_seconds, 2),
            'is_valid': is_valid,
            'expires_in_seconds': max(0, CACHE_TTL_SECONDS - age_seconds) if is_valid else 0,
            'alert_count': entry['data'].get('count', 0)
        }

    return {
        'cache_ttl_seconds': CACHE_TTL_SECONDS,
        'entries': cache_info,
        'total_entries': len(_cache),
        'accessed_by': user.get('email')
    }


# Define the cache clear endpoint with conditional authentication
if os.getenv('PERF_TEST', '').lower() == 'true':
    # Performance testing mode - no auth required
    @alerts_router.delete('/cache')
    async def clear_cache():
        """
        Clear all cached data

        **PERF_TEST MODE**: Authentication bypassed for testing
        """
        user = {"email": "perf-test@example.com", "testing": True}
        logger.warning(
            f"🔒⚠️ PERF_TEST user {user.get('email')} clearing all cache data - TESTING ACTION")

        cleared_count = len(_cache)
        _cache.clear()
        return {
            'message': f"Cleared {cleared_count} cache entries",
            'cache_size': len(_cache),
            'cleared_by': user.get('email')
        }
else:
    # Production mode - authentication required
    @alerts_router.delete('/cache')
    async def clear_cache(user=Depends(verify_session)):
        """
        Clear all cached data

        **Requires authentication**: Valid Google OAuth token - ADMINISTRATIVE ACTION
        """
        logger.warning(
            f"🔒⚠️ Authenticated user {user.get('email')} clearing all cache data - ADMINISTRATIVE ACTION")

        cleared_count = len(_cache)
        _cache.clear()
        return {
            'message': f"Cleared {cleared_count} cache entries",
            'cache_size': len(_cache),
            'cleared_by': user.get('email')
        }


@alerts_router.get('/stats')
async def get_alert_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    user=Depends(verify_session)
):
    """
    Get simple statistics for both collections

    **Requires authentication**: Valid Google OAuth token
    """
    # Input validation
    if hours < 1 or hours > 4380:
        raise AlertError("Hours must be between 1 and 4380 (6 months)")

    logger.info(
        f"🔒 Authenticated user {user.get('email')} accessing alert stats")

    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    stats = {
        'monitor_alerts': 0,
        'nyc_311_signals': 0,
        'total': 0
    }

    # Count monitor alerts
    try:
        monitor_ref = db.collection('nyc_monitor_alerts')
        monitor_docs = monitor_ref.where(
            'created_at', '>=', cutoff_time).stream()
        stats['monitor_alerts'] = sum(1 for _ in monitor_docs)
    except Exception as e:
        logger.error(f"Error counting monitor alerts: {e}")

    # Count 311 signals
    try:
        signals_ref = db.collection('nyc_311_signals')
        signals_docs = signals_ref.where(
            'signal_timestamp', '>=', cutoff_time).stream()
        stats['nyc_311_signals'] = sum(1 for _ in signals_docs)
    except Exception as e:
        logger.error(f"Error counting 311 signals: {e}")

    stats['total'] = stats['monitor_alerts'] + stats['nyc_311_signals']

    return {
        'stats': stats,
        'timeframe': f"Last {hours} hours",
        'generated_at': datetime.utcnow().isoformat(),
        'accessed_by': user.get('email')
    }


@alerts_router.get('/categories')
async def get_alert_categories(user=Depends(verify_session)):
    """
    Get all available alert categories and types with metadata for frontend use

    Returns:
        Dictionary with categorized alert types including descriptions

    **Requires authentication**: Valid Google OAuth token
    """
    logger.info(
        f"🔒 Authenticated user {user.get('email')} accessing alert categories")

    # Get the categories summary from our categorization system
    categories = get_categories_summary()

    # Add additional metadata for frontend
    response = {
        'categories': categories,
        # Simplified list for frontend filtering
        'main_categories': get_main_categories(),
        'total_categories': len(categories),
        'total_alert_types': len(ALERT_TYPES),
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0',
        'accessed_by': user.get('email')
    }

    logger.info(
        f"✅ Returned {len(categories)} categories with {len(ALERT_TYPES)} alert types")
    return response


@alerts_router.get('/agent-traces/{trace_id}')
async def get_agent_trace(trace_id: str, user=Depends(verify_session)):
    """
    Get agent trace from Firestore by trace ID

    Args:
        trace_id: Firestore document ID for the trace

    Returns:
        Agent trace data formatted as markdown

    **Requires authentication**: Valid Google OAuth token - SENSITIVE INVESTIGATION DATA
    """
    # Input validation
    if not trace_id or not trace_id.strip():
        raise AlertError("Trace ID is required")

    logger.warning(
        f"🔒🔍 Authenticated user {user.get('email')} accessing SENSITIVE agent trace: {trace_id}")

    # Get Firestore client
    db = get_db()

    # Fetch trace document
    trace_doc = db.collection('agent_traces').document(trace_id).get()

    if not trace_doc.exists:
        raise AlertError(
            f"Agent trace not found: {trace_id}", alert_id=trace_id)

    trace_data = trace_doc.to_dict()

    # Format trace as markdown
    trace_markdown = format_trace_as_markdown(trace_data)

    logger.info(f"✅ Retrieved agent trace: {trace_id}")
    return {
        'trace_id': trace_id,
        'investigation_id': trace_data.get('investigation_id'),
        'trace': trace_markdown,
        'created_at': trace_data.get('created_at'),
        'approach': trace_data.get('approach'),
        'accessed_by': user.get('email')
    }


def format_trace_as_markdown(trace_data: dict) -> str:
    """Format trace data as readable markdown.

    Args:
        trace_data: Firestore trace document data

    Returns:
        Formatted markdown string
    """
    try:
        markdown = f"# Investigation Trace\n\n"

        if trace_data.get('investigation_id'):
            markdown += f"**Investigation ID:** {trace_data['investigation_id']}\n\n"

        if trace_data.get('approach'):
            markdown += f"**Approach:** {trace_data['approach']}\n\n"

        if trace_data.get('created_at'):
            markdown += f"**Created:** {trace_data['created_at']}\n\n"

        # Format the actual trace data
        raw_trace = trace_data.get('trace_data', {})

        if raw_trace.get('investigation_id'):
            markdown += f"## Investigation Details\n\n"
            markdown += f"- **ID:** {raw_trace.get('investigation_id')}\n"
            markdown += f"- **Approach:** {raw_trace.get('approach', 'Unknown')}\n"
            markdown += f"- **Export Time:** {raw_trace.get('exported_at', 'Unknown')}\n\n"

        # Add raw trace data as JSON for detailed inspection
        markdown += f"## Raw Trace Data\n\n"
        markdown += "```json\n"
        markdown += json.dumps(raw_trace, indent=2, default=str)
        markdown += "\n```\n"

        return markdown

    except Exception as e:
        logger.error(f"Error formatting trace: {e}")
        return f"Error formatting trace data: {str(e)}"


@alerts_router.get('/reports')
async def get_alerts_with_reports(
    limit: int = Query(100, ge=1, le=500,
                       description="Number of alerts with reports to return"),
    user=Depends(verify_session)
):
    """
    Get alerts that have reports (status='resolved' and reportUrl exists)
    Ordered by most recently updated/created

    Returns only alerts that have completed investigations with report URLs

    **Requires authentication**: Valid Google OAuth token
    """
    # Input validation
    if limit < 1 or limit > 500:
        raise AlertError("Limit must be between 1 and 500")

    logger.info(
        f"🔒 Authenticated user {user.get('email')} accessing alerts with reports")

    # Check cache first
    cache_key = f"reports:{limit}"

    if cache_key in _cache:
        entry = _cache[cache_key]
        if is_cache_valid(entry['timestamp']):
            logger.info(f"✅ Cache HIT for {cache_key}")
            cached_data = entry['data'].copy()
            if 'performance' in cached_data:
                cached_data['performance']['cached'] = True
                cached_data['performance']['cache_age_seconds'] = round(
                    time.time() - entry['timestamp'], 2)
            return cached_data

    start_time = datetime.utcnow()
    db = get_db()

    all_alerts_with_reports = []
    query_stats = {}

    # Query monitor alerts with reports - SIMPLIFIED APPROACH
    monitor_start = datetime.utcnow()
    try:
        alerts_ref = db.collection('nyc_monitor_alerts')

        # STRATEGY 1: First try simple status filter, then check report_url in code
        # This avoids composite index issues
        logger.info("🔍 Querying resolved alerts...")

        resolved_query = (alerts_ref
                          .where('status', '==', 'resolved')
                          .limit(limit * 2))  # Get more to account for filtering

        monitor_count = 0
        total_resolved = 0

        for doc in resolved_query.stream():
            data = doc.to_dict()
            total_resolved += 1

            # Check if report_url exists and is not empty (multiple field name variations)
            report_url = None
            for field_name in ['report_url', 'reportUrl', 'reportURL', 'report_URL']:
                if field_name in data and data[field_name]:
                    report_url = data[field_name]
                    break

            if not report_url:
                logger.debug(
                    f"Skipping alert {doc.id} - no report URL found")
                continue

            logger.info(
                f"✅ Found alert with report: {doc.id} - {report_url}")

            # Extract the real source from the nested structure
            real_source = 'monitor'  # Default fallback
            try:
                original_alert = data.get('original_alert', {})
                if original_alert:
                    original_alert_data = original_alert.get(
                        'original_alert_data', {})
                    if original_alert_data:
                        signals = original_alert_data.get('signals', [])
                        if signals and len(signals) > 0:
                            real_source = signals[0]
            except Exception as e:
                logger.warning(
                    f"Could not extract source for alert {doc.id}: {e}")

            # Create alert object with report information - MINIMAL PAYLOAD
            alert = {
                'id': doc.id,
                'title': data.get('title', 'NYC Alert'),
                'status': data.get('status', 'resolved'),
                'source': real_source,
                # Use updated_at as primary date
                'date': data.get('updated_at', data.get('created_at')),
                'reportUrl': report_url,
            }
            all_alerts_with_reports.append(alert)
            monitor_count += 1

            # Stop if we have enough
            if monitor_count >= limit:
                break

        monitor_time = (datetime.utcnow() - monitor_start).total_seconds()
        query_stats['monitor'] = {
            'count': monitor_count,
            'total_resolved_checked': total_resolved,
            'time_seconds': round(monitor_time, 3),
            'sources_found': list(set([a['source'] for a in all_alerts_with_reports if a['source'] != '311']))
        }

        logger.info(
            f"📊 Monitor query: {monitor_count} alerts with reports from {total_resolved} resolved alerts")

    except Exception as e:
        logger.error(f"Monitor reports error: {e}")
        query_stats['monitor'] = {'error': str(e)}

    # Query 311 signals with reports (similar approach)
    signals_start = datetime.utcnow()
    try:
        signals_ref = db.collection('nyc_311_signals')

        # Simple approach for 311 as well
        resolved_311_query = (signals_ref
                              .where('status', '==', 'resolved')
                              .limit(limit // 4))  # Smaller limit for 311

        signals_count = 0
        total_311_resolved = 0

        for doc in resolved_311_query.stream():
            data = doc.to_dict()
            total_311_resolved += 1

            # Check if report_url exists and is not empty
            report_url = None
            for field_name in ['report_url', 'reportUrl', 'reportURL', 'report_URL']:
                if field_name in data and data[field_name]:
                    report_url = data[field_name]
                    break

            if not report_url:
                continue

            # Create minimal 311 alert object - MINIMAL PAYLOAD
            alert = {
                'id': doc.id,
                'title': f"{data.get('complaint_type', 'NYC 311')}: {(data.get('descriptor', '') or '')[:50]}",
                'status': _normalize_311_alert_status(data.get('status', 'resolved')),
                'source': '311',
                'date': data.get('updated_at', data.get('created_at')),
                'reportUrl': report_url,
            }
            all_alerts_with_reports.append(alert)
            signals_count += 1

        signals_time = (datetime.utcnow() - signals_start).total_seconds()
        query_stats['311'] = {
            'count': signals_count,
            'total_resolved_checked': total_311_resolved,
            'time_seconds': round(signals_time, 3)
        }

    except Exception as e:
        logger.error(f"311 reports error: {e}")
        query_stats['311'] = {'error': str(e)}

    # Sort all alerts by updated_at descending (most recent first)
    sort_start = datetime.utcnow()

    def get_sort_timestamp(alert):
        """Get timestamp for sorting (date field from minimal payload)"""
        date_value = alert.get('date')
        if date_value:
            if isinstance(date_value, datetime):
                return date_value.timestamp()
            elif isinstance(date_value, str):
                try:
                    return datetime.fromisoformat(date_value.replace('Z', '+00:00')).timestamp()
                except:
                    pass

        # Fallback to epoch if no valid date
        return 0

    all_alerts_with_reports.sort(key=get_sort_timestamp, reverse=True)

    # Apply final limit
    final_alerts = all_alerts_with_reports[:limit]

    sort_time = (datetime.utcnow() - sort_start).total_seconds()
    total_time = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        f"📊 REPORTS: Found {len(final_alerts)} alerts with reports in {total_time:.3f}s")

    result = {
        'alerts': final_alerts,
        'count': len(final_alerts),
        'performance': {
            'total_time_seconds': round(total_time, 3),
            'query_breakdown': query_stats,
            'sort_time_seconds': round(sort_time, 3),
            'alerts_per_second': round(len(final_alerts) / total_time if total_time > 0 else 0, 1),
            'optimizations': ['resolved_status_filter_only', 'report_url_code_filter', 'no_composite_index_needed'],
            'cached': False,
            'cache_ttl_seconds': CACHE_TTL_SECONDS,
            'accessed_by': user.get('email')
        }
    }

    # Cache the result
    _cache[cache_key] = {
        'data': result,
        'timestamp': time.time()
    }

    return result
