from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore
from ..config import get_config
import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Any
import time

logger = logging.getLogger(__name__)

# Initialize router
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])

# Simple in-memory cache
_cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_db():
    """Get Firestore client instance"""
    try:
        return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")
        raise HTTPException(
            status_code=500, detail="Database configuration error")


def get_cache_key(limit: int, hours: int) -> str:
    """Generate cache key for alerts query"""
    return f"alerts:{limit}:{hours}"


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
            'status': signal.get('status', 'Open'),
            'timestamp': signal.get('created_at', datetime.utcnow()).isoformat() if isinstance(signal.get('created_at'), datetime) else signal.get('created_at', ''),
            'neighborhood': signal.get('borough', 'Unknown'),
            'borough': signal.get('borough', 'Unknown'),
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
            'status': 'Open',
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


@alerts_router.get('/recent')
async def get_recent_alerts(
    limit: int = Query(2000, ge=1, le=5000,
                       description="Number of alerts to return"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """
    Get recent alerts with MINIMAL data - ultra-fast for map display

    Returns only: title, description, source, severity, date, coordinates

    Optimizations:
    - Ultra-minimal field selection (8x speedup)
    - NO sorting
    - NO complex transformations
    - In-memory caching (5 min TTL)
    """
    try:
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
        monitor_limit = min(100, limit // 20)  # 5% for monitor
        signals_limit = limit - monitor_limit   # 95% for 311

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
                             .select(['created_at', 'title', 'description', 'priority', 'latitude', 'longitude', 'original_alert'])
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
                    'severity': _get_severity_from_priority(data.get('priority', 'medium')),
                    'date': data.get('created_at', datetime.utcnow()).isoformat() if isinstance(data.get('created_at'), datetime) else str(data.get('created_at', '')),
                    'coordinates': {
                        'lat': data.get('latitude', 40.7589),
                        'lng': data.get('longitude', -73.9851)
                    }
                }
                all_alerts.append(alert)

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
                             .select(['signal_timestamp', 'complaint_type', 'descriptor', 'latitude', 'longitude', 'is_emergency', 'severity', 'priority'])
                             .limit(signals_limit))

            signals_count = 0
            for doc in signals_query.stream():
                data = doc.to_dict()

                # Use calculated severity from rule-based triage, fallback to emergency logic
                severity = data.get('severity')
                if severity is None:
                    # Fallback for old records without severity
                    severity = 7 if data.get('is_emergency', False) else 3

                # Ultra-minimal transformation
                alert = {
                    'id': doc.id,
                    'title': f"{data.get('complaint_type', 'NYC 311')}: {(data.get('descriptor', '') or '')[:50]}",
                    'description': data.get('descriptor', ''),
                    'source': '311',
                    'severity': severity,
                    'timestamp': _extract_311_timestamp(data),
                    'coordinates': {
                        'lat': data.get('latitude', 40.7589),
                        'lng': data.get('longitude', -73.9851)
                    }
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

        logger.info(
            f"🎯 MINIMAL: {len(all_alerts)} alerts in {total_time:.3f}s ({len(all_alerts)/total_time:.0f} alerts/sec)")

        result = {
            'alerts': all_alerts,
            'count': len(all_alerts),
            'performance': {
                'total_time_seconds': round(total_time, 3),
                'alerts_per_second': round(len(all_alerts) / total_time if total_time > 0 else 0, 1),
                'query_breakdown': query_stats,
                'optimizations': ['ultra_minimal_fields', 'no_sorting', 'minimal_transform'],
                'cached': False,
                'cache_ttl_seconds': CACHE_TTL_SECONDS
            }
        }

        # Cache the result
        _cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }

        return result

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@alerts_router.get('/get/{alert_id}')
async def get_single_alert(alert_id: str):
    """
    Get a single alert with full details by ID

    Searches both collections (monitor and 311) for the alert ID
    Returns complete alert object with all available fields
    """
    try:
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
                    'found': True
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
                    'found': True
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
                    'matched_by': 'unique_key'
                }
        except Exception as e:
            logger.error(f"Error searching by unique_key: {e}")

        # Not found in any collection
        logger.warning(f"Alert not found: {alert_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Alert with ID '{alert_id}' not found in any collection"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching single alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert")


def _get_severity_from_priority(priority: str) -> int:
    """Convert priority to numeric severity"""
    priority_map = {
        'critical': 9,
        'high': 7,
        'medium': 5,
        'low': 3,
        'info': 1
    }
    return priority_map.get(priority.lower(), 5)


@alerts_router.get('/cache/info')
async def get_cache_info():
    """Get information about current cache state"""
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
        'total_entries': len(_cache)
    }


@alerts_router.delete('/cache')
async def clear_cache():
    """Clear all cached data"""
    cleared_count = len(_cache)
    _cache.clear()
    return {
        'message': f"Cleared {cleared_count} cache entries",
        'cache_size': len(_cache)
    }


# Keep the stream endpoint for potential future use
@alerts_router.get('/stream')
async def stream_alerts():
    """Stream alerts via Server-Sent Events (legacy endpoint)"""
    return EventSourceResponse(alert_stream())


async def alert_stream():
    """Basic alert streaming (legacy)"""
    try:
        db = get_db()
        while True:
            yield {
                'event': 'ping',
                'data': json.dumps({'timestamp': datetime.utcnow().isoformat()})
            }
            await asyncio.sleep(60)  # Ping every minute
    except Exception as e:
        logger.error(f"Error in alert stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@alerts_router.get('/stats')
async def get_alert_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """Get simple statistics for both collections"""
    try:
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
                'created_at', '>=', cutoff_time).stream()
            stats['nyc_311_signals'] = sum(1 for _ in signals_docs)
        except Exception as e:
            logger.error(f"Error counting 311 signals: {e}")

        stats['total'] = stats['monitor_alerts'] + stats['nyc_311_signals']

        return {
            'stats': stats,
            'timeframe': f"Last {hours} hours",
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate stats")
