from monitor.types.alert_categories import get_categories_summary, ALERT_TYPES, categorize_311_complaint, get_alert_type_info, normalize_category, get_main_categories
from fastapi import APIRouter, HTTPException, Query, Depends
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore
from ..config import get_config
from ..auth import verify_session
from ..exceptions import AlertError, DatabaseError
import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Any, Optional
import time

# Import the new categorization system
import sys
import os
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)

# Initialize router
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])

# Simple in-memory cache
_cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_db():
    """Get Firestore client instance"""
    return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)


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


@alerts_router.get('/recent/stream')
async def stream_alerts(
    hours: int = Query(24, ge=1, le=4320, description="Hours to look back (max 6 months)"),
    chunk_size: int = Query(200, ge=50, le=5000, description="Number of alerts per chunk"),
    user=Depends(verify_session)
):
    """
    Stream alerts using Server-Sent Events for progressive loading
    
    Returns alerts in chunks to provide immediate feedback and better UX.
    Each chunk contains a portion of the total alerts with progress information.
    
    **Requires authentication**: Valid Google OAuth token
    """
    # Input validation
    if hours < 1 or hours > 4320:
        raise AlertError("Hours must be between 1 and 4320 (6 months)")
    
    if chunk_size < 100 or chunk_size > 5000:
        raise AlertError("Chunk size must be between 100 and 5000")

    logger.info(
        f"🔒 Authenticated user {user.get('email')} starting streaming alerts (hours={hours}, chunk_size={chunk_size})")

    async def generate_alert_stream():
        db = None
        try:
            # Create a new Firestore client for this specific stream to avoid retry issues
            db = firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'start', 'hours': hours, 'chunk_size': chunk_size, 'cutoff_time': cutoff_time.isoformat()})}\n\n"
            
            total_alerts = []
            chunk_num = 0
            
            # Stream monitor alerts first with better error handling
            try:
                alerts_ref = db.collection('nyc_monitor_alerts')
                monitor_query = (alerts_ref
                               .where(filter=firestore.FieldFilter('created_at', '>=', cutoff_time))
                               .limit(min(2000, chunk_size * 2)))  # Reasonable limit for monitor
                
                monitor_alerts = []
                try:
                    # Convert stream to list to avoid iterator issues
                    docs = list(monitor_query.stream())
                    for doc in docs:
                        try:
                            data = doc.to_dict()
                            
                            # Extract the real source from the nested structure
                            real_source = 'monitor'
                            try:
                                original_alert = data.get('original_alert', {})
                                if original_alert:
                                    original_alert_data = original_alert.get('original_alert_data', {})
                                    if original_alert_data:
                                        signals = original_alert_data.get('signals', [])
                                        if signals and len(signals) > 0:
                                            real_source = signals[0]
                            except Exception as e:
                                logger.warning(f"Could not extract source for alert {doc.id}: {e}")
                            
                            alert = {
                                'id': doc.id,
                                'source': real_source,
                                'priority': _get_priority_from_severity(data.get('severity', 5)),
                                'timestamp': _extract_monitor_timestamp(data),
                                'coordinates': {
                                    'lat': data.get('original_alert', {}).get('latitude', 40.7589),
                                    'lng': data.get('original_alert', {}).get('longitude', -73.9851)
                                },
                                'category': normalize_category(data.get('category', 'general')),
                            }
                            monitor_alerts.append(alert)
                        except Exception as doc_error:
                            logger.warning(f"Error processing monitor alert doc {doc.id}: {doc_error}")
                            continue
                
                except Exception as stream_error:
                    logger.error(f"Monitor query stream error: {stream_error}")
                    # Don't fail the entire stream for monitor errors
                
                # Send monitor alerts chunk
                if monitor_alerts:
                    chunk_num += 1
                    total_alerts.extend(monitor_alerts)
                    yield f"data: {json.dumps({'type': 'chunk', 'chunk': chunk_num, 'alerts': monitor_alerts, 'source': 'monitor', 'total_so_far': len(total_alerts)})}\n\n"
                    
            except Exception as e:
                logger.error(f"Monitor streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'source': 'monitor', 'message': str(e)})}\n\n"
            
            # Stream 311 signals in smaller, more manageable chunks to prevent connection issues
            try:
                signals_ref = db.collection('nyc_311_signals')
                
                # Use the filter method instead of positional arguments to avoid deprecation warning
                signals_query = (signals_ref
                               .where(filter=firestore.FieldFilter('signal_timestamp', '>=', cutoff_time))
                               .select(['signal_timestamp', 'complaint_type', 'descriptor', 'latitude', 'longitude', 'is_emergency', 'category', 'full_signal_data', 'incident_zip', 'borough', 'status', 'severity', 'event_type'])
                               .limit(50000))  # Hard limit to prevent excessive memory usage
                
                signals_batch = []
                signals_processed = 0
                max_docs_to_process = 50000  # Safety limit
                docs_processed = 0
                
                try:
                    # Process documents in a single pass without intermediate storage
                    for doc in signals_query.stream():
                        try:
                            if docs_processed >= max_docs_to_process:
                                logger.warning(f"Reached processing limit of {max_docs_to_process} documents")
                                break
                                
                            data = doc.to_dict()
                            docs_processed += 1
                            
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
                            
                            alert = {
                                'id': doc.id,
                                'source': '311',
                                'priority': _get_priority_from_severity(severity),
                                'timestamp': _extract_311_timestamp(data),
                                'coordinates': {
                                    'lat': data.get('latitude', 40.7589),
                                    'lng': data.get('longitude', -73.9851)
                                },
                                'category': normalize_category(category),
                            }
                            
                            signals_batch.append(alert)
                            signals_processed += 1
                            
                            # Send chunk when we reach chunk_size
                            if len(signals_batch) >= chunk_size:
                                chunk_num += 1
                                total_alerts.extend(signals_batch)
                                yield f"data: {json.dumps({'type': 'chunk', 'chunk': chunk_num, 'alerts': signals_batch, 'source': '311', 'total_so_far': len(total_alerts), 'signals_processed': signals_processed})}\n\n"
                                signals_batch = []
                                
                        except Exception as doc_error:
                            logger.warning(f"Error processing 311 signal doc {doc.id}: {doc_error}")
                            continue
                
                except Exception as stream_error:
                    logger.error(f"311 query stream error: {stream_error}")
                    # Continue with whatever we have
                
                # Send remaining signals
                if signals_batch:
                    chunk_num += 1
                    total_alerts.extend(signals_batch)
                    yield f"data: {json.dumps({'type': 'chunk', 'chunk': chunk_num, 'alerts': signals_batch, 'source': '311', 'total_so_far': len(total_alerts), 'signals_processed': signals_processed})}\n\n"
                    
            except Exception as e:
                logger.error(f"311 streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'source': '311', 'message': str(e)})}\n\n"
            
            # Send completion message
            yield f"data: {json.dumps({'type': 'complete', 'total_alerts': len(total_alerts), 'total_chunks': chunk_num, 'accessed_by': user.get('email')})}\n\n"
            
            logger.info(f"🎯 STREAMING COMPLETE: {len(total_alerts)} alerts in {chunk_num} chunks for user {user.get('email')}")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Ensure we properly close the database connection
            try:
                if db is not None:
                    db.close()
            except Exception as close_error:
                logger.warning(f"Error closing database connection: {close_error}")
    
    # Add headers to help with connection management
    response = EventSourceResponse(
        generate_alert_stream(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
    return response


@alerts_router.get('/recent')
async def get_recent_alerts(
    limit: int = Query(2000, ge=1, le=50000,
                       description="Number of alerts to return"),
    hours: int = Query(24, ge=1, le=4320, description="Hours to look back (max 6 months)"),
    user=Depends(verify_session)
):
    """
    Get recent alerts with ULTRA-MINIMAL data - optimized for map display

    Returns only essential fields:
    - Core: id, title, description, source, priority, status, timestamp
    - Location: coordinates, neighborhood, borough, category  
    - Investigation: reportUrl, traceId, investigationId (if present)

    Optimizations:
    - Ultra-minimal field selection (90%+ payload reduction)
    - NO unnecessary metadata or nested objects
    - NO deduplication (raw speed over duplicate removal)
    - NO sorting (database order for maximum performance)
    - In-memory caching (5 min TTL)

    **Requires authentication**: Valid Google OAuth token
    """
    # Input validation
    if limit < 1 or limit > 50000:
        raise AlertError("Limit must be between 1 and 50000")

    if hours < 1 or hours > 4320:
        raise AlertError("Hours must be between 1 and 4320 (6 months)")

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
                         .where(filter=firestore.FieldFilter('created_at', '>=', cutoff_time))
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

            # ULTRA-MINIMAL transformation - only essential fields for map display
            alert = {
                'id': doc.id,
                'source': real_source,
                'priority': _get_priority_from_severity(data.get('severity', 5)),
                'timestamp': _extract_monitor_timestamp(data),
                'coordinates': {
                    'lat': data.get('original_alert', {}).get('latitude', 40.7589),
                    'lng': data.get('original_alert', {}).get('longitude', -73.9851)
                },
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
                         .where(filter=firestore.FieldFilter('signal_timestamp', '>=', cutoff_time))
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

            # ULTRA-MINIMAL transformation - only essential fields for map display
            alert = {
                'id': doc.id,
                'source': '311',
                'priority': _get_priority_from_severity(severity),
                'timestamp': _extract_311_timestamp(data),
                'coordinates': {
                    'lat': data.get('latitude', 40.7589),
                    'lng': data.get('longitude', -73.9851)
                },
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

    logger.info(
        f"🎯 ULTRA-FAST: {len(all_alerts)} alerts in {total_time:.3f}s ({len(all_alerts)/total_time:.0f} alerts/sec)")

    result = {
        'alerts': all_alerts,
        'count': len(all_alerts),
        'performance': {
            'total_time_seconds': round(total_time, 3),
            'alerts_per_second': round(len(all_alerts) / total_time if total_time > 0 else 0, 1),
            'query_breakdown': query_stats,
            'optimizations': ['ultra_minimal_fields', 'no_deduplication', 'no_sorting', 'minimal_transform'],
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
        query = signals_ref.where(filter=firestore.FieldFilter('unique_key', '==', alert_id)).limit(1)
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
    hours: int = Query(24, ge=1, le=4320, description="Hours to look back (max 6 months)"),
    user=Depends(verify_session)
):
    """
    Get simple statistics for both collections

    **Requires authentication**: Valid Google OAuth token
    """
    # Input validation
    if hours < 1 or hours > 4320:
        raise AlertError("Hours must be between 1 and 4320 (6 months)")

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
            filter=firestore.FieldFilter('created_at', '>=', cutoff_time)).stream()
        stats['monitor_alerts'] = sum(1 for _ in monitor_docs)
    except Exception as e:
        logger.error(f"Error counting monitor alerts: {e}")

    # Count 311 signals
    try:
        signals_ref = db.collection('nyc_311_signals')
        signals_docs = signals_ref.where(
            filter=firestore.FieldFilter('signal_timestamp', '>=', cutoff_time)).stream()
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
                          .where(filter=firestore.FieldFilter('status', '==', 'resolved'))
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
                              .where(filter=firestore.FieldFilter('status', '==', 'resolved'))
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
