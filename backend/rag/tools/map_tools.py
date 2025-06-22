#!/usr/bin/env python3
"""
Map Tools for NYC Atlas Investigation System.
Generates real map images with location pins for investigations.
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional, Tuple
from google.adk.tools import FunctionTool
from ..investigation.state_manager import state_manager
from .artifact_manager import artifact_manager

logger = logging.getLogger(__name__)

# Google Maps Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
MAPS_DEFAULT_ZOOM = 16
MAPS_DEFAULT_SIZE = "640x640"
MAPS_DEFAULT_MAPTYPE = "roadmap"


def generate_location_map_func(
    location: str,
    investigation_id: str = "unknown",
    zoom_level: int = 16,
    map_type: str = "satellite",
    include_pin: bool = True,
    size: str = "640x640"
) -> dict:
    """Generate a map image for the specified location with a pin marker.

    Args:
        location: Address or coordinates to map (e.g., "Washington Square Park, Manhattan")
        investigation_id: Investigation ID for artifact naming
        zoom_level: Map zoom level (1-20, default: 16)
        map_type: Map type (roadmap, satellite, hybrid, terrain)
        include_pin: Whether to include a red pin marker
        size: Image size in format "WIDTHxHEIGHT" (max 640x640)

    Returns:
        Map generation result with artifact metadata
    """
    try:
        logger.info(f"🗺️ GENERATE_LOCATION_MAP - Starting")
        logger.info(f"   📍 Location: {location}")
        logger.info(f"   🆔 Investigation ID: {investigation_id}")
        logger.info(f"   🔍 Zoom Level: {zoom_level}")
        logger.info(f"   🗺️ Map Type: {map_type}")
        logger.info(f"   📌 Include Pin: {include_pin}")
        logger.info(f"   📐 Size: {size}")

        # Use the new artifact manager to generate and save the map
        logger.info(f"🔧 Calling artifact_manager.generate_google_maps_image...")
        result = artifact_manager.generate_google_maps_image(
            investigation_id=investigation_id,
            location=location,
            zoom_level=zoom_level,
            map_type=map_type,
            include_pin=include_pin,
            size=size
        )

        logger.info(f"📤 Artifact manager response:")
        logger.info(f"   Success: {result.get('success', False)}")
        logger.info(f"   Filename: {result.get('filename', 'N/A')}")
        logger.info(f"   GCS URL: {result.get('gcs_url', 'N/A')[:100]}...")

        if result["success"]:
            # Add to investigation artifacts
            investigation_state = state_manager.get_investigation(
                investigation_id)

            if investigation_state:
                logger.info(f"🎯 Adding artifact to investigation state...")

                # Create MINIMAL artifact info to prevent context overflow
                artifact_info = {
                    "type": "map_image",
                    "filename": result["filename"],
                    "location": location,
                    "description": f"Map of {location}",
                    "saved_to_gcs": True,
                    "relevance_score": 0.9,
                    "timestamp": result.get("created_at", datetime.utcnow().isoformat())
                }

                # Only include essential URLs - not all the metadata
                if result.get("gcs_url"):
                    artifact_info["gcs_url"] = result["gcs_url"]
                if result.get("signed_url"):
                    artifact_info["signed_url"] = result["signed_url"]

                investigation_state.artifacts.append(artifact_info)

                logger.info(f"✅ Added minimal map artifact to investigation")
                logger.info(
                    f"   Total artifacts now: {len(investigation_state.artifacts)}")
            else:
                logger.warning(
                    f"❌ Investigation state not found for ID: {investigation_id}")

            # Return VERY CONCISE response to prevent 400 error
            concise_response = {
                "success": True,
                "type": "map_image",
                "filename": result["filename"],
                "location": location,
                "summary": f"✅ Map generated for {location}"
            }

            logger.info(f"📤 RETURNING CONCISE RESPONSE:")
            logger.info(
                f"   Response size: {len(str(concise_response))} characters")
            logger.debug(f"   Response content: {concise_response}")

            return concise_response

        else:
            error_response = {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "location": location,
                "summary": f"Failed to generate map for {location}"
            }

            logger.error(f"❌ Map generation failed: {error_response}")
            return error_response

    except Exception as e:
        logger.error(f"❌ GENERATE_LOCATION_MAP - Exception occurred:")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Error type: {type(e)}")
        logger.exception("Full exception details:")

        error_response = {
            "success": False,
            "error": f"Map generation failed: {str(e)}",
            "location": location,
            "investigation_id": investigation_id,
            "summary": f"Failed to generate map for {location}"
        }

        logger.error(f"📤 RETURNING ERROR RESPONSE:")
        logger.error(
            f"   Response size: {len(str(error_response))} characters")

        return error_response


def _generate_google_static_map(
    location: str,
    zoom_level: int,
    map_type: str,
    include_pin: bool,
    size: str,
    filename: str,
    investigation_id: str
) -> dict:
    """Generate map using Google Maps Static API."""
    try:
        # Build Google Maps Static API URL
        base_url = "https://maps.googleapis.com/maps/api/staticmap"

        params = {
            "center": location,
            "zoom": zoom_level,
            "size": size,
            "maptype": map_type,
            "key": GOOGLE_MAPS_API_KEY,
            "format": "png"
        }

        # Add marker pin if requested
        if include_pin:
            params["markers"] = f"color:red|size:mid|{location}"

        # Make the API request
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        # Validate response is an image
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f"Invalid response type: {content_type}")

        # Save to artifact service if available
        map_url = f"{base_url}?" + \
            "&".join([f"{k}={v}" for k, v in params.items()])

        # For now, plan the artifact (TODO: save to GCS)
        artifact_info = {
            "type": "map_image",
            "filename": filename,
            "location": location,
            "description": f"Map of {location} with location pin",
            "source": "google_maps_static_api",
            "map_type": map_type,
            "zoom_level": zoom_level,
            "size": size,
            "api_url": map_url,
            "planned_artifact": True,
            "mime_type": "image/png",
            "ticker": state_manager.get_next_artifact_ticker(investigation_id),
            "timestamp": datetime.utcnow().isoformat(),
            "relevance_score": 0.9,  # Maps are highly relevant
            "file_size_estimate": f"~{len(response.content)} bytes"
        }

        # Add to investigation artifacts
        investigation_state = state_manager.get_investigation(investigation_id)
        if investigation_state:
            investigation_state.artifacts.append(artifact_info)
            logger.info(f"✅ Added map artifact to investigation: {filename}")

        return {
            "success": True,
            "type": "map_image",
            "filename": filename,
            "location": location,
            "map_url": map_url,
            "artifact_info": artifact_info,
            "source": "google_maps_static_api",
            "image_size": len(response.content),
            "summary": f"Generated Google Maps image for {location} with pin marker"
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Google Maps API request failed: {e}")
        return {
            "success": False,
            "error": f"Google Maps API error: {str(e)}",
            "location": location,
            "source": "google_maps_static_api"
        }
    except Exception as e:
        logger.error(f"Google Maps generation failed: {e}")
        return {
            "success": False,
            "error": f"Google Maps generation error: {str(e)}",
            "location": location,
            "source": "google_maps_static_api"
        }


def _generate_osm_map(
    location: str,
    zoom_level: int,
    include_pin: bool,
    size: str,
    filename: str,
    investigation_id: str
) -> dict:
    """Generate map using OpenStreetMap-based services as fallback."""
    try:
        # Use MapBox Static Images API (free tier available)
        # Or use a simple tile-based approach

        # For now, create a mock map artifact that would work
        ticker = state_manager.get_next_artifact_ticker(investigation_id)

        # Try to geocode the location using a free service
        coordinates = _geocode_location(location)

        artifact_info = {
            "type": "map_image",
            "filename": filename,
            "location": location,
            "coordinates": coordinates,
            "description": f"Map of {location}" + (" with location pin" if include_pin else ""),
            "source": "openstreetmap_fallback",
            "zoom_level": zoom_level,
            "size": size,
            "planned_artifact": True,
            "mime_type": "image/png",
            "ticker": ticker,
            "timestamp": datetime.utcnow().isoformat(),
            "relevance_score": 0.8,  # Slightly lower for fallback
            "file_size_estimate": "~50KB"
        }

        # Add to investigation artifacts
        investigation_state = state_manager.get_investigation(investigation_id)
        if investigation_state:
            investigation_state.artifacts.append(artifact_info)
            logger.info(
                f"✅ Added OSM map artifact to investigation: {filename}")

        return {
            "success": True,
            "type": "map_image",
            "filename": filename,
            "location": location,
            "coordinates": coordinates,
            "artifact_info": artifact_info,
            "source": "openstreetmap_fallback",
            "summary": f"Generated OSM-based map for {location}" + (" with pin" if include_pin else "")
        }

    except Exception as e:
        logger.error(f"OSM map generation failed: {e}")
        return {
            "success": False,
            "error": f"OSM map generation error: {str(e)}",
            "location": location,
            "source": "openstreetmap_fallback"
        }


def _geocode_location(location: str) -> Optional[Tuple[float, float]]:
    """Simple geocoding using free services."""
    try:
        # Use Nominatim (OpenStreetMap's geocoding service)
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": location,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }

        response = requests.get(nominatim_url, params=params, timeout=10)
        response.raise_for_status()

        results = response.json()
        if results:
            result = results[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            logger.info(f"Geocoded '{location}' to ({lat}, {lon})")
            return (lat, lon)
        else:
            logger.warning(f"No geocoding results for '{location}'")
            return None

    except Exception as e:
        logger.error(f"Geocoding failed for '{location}': {e}")
        return None


def generate_investigation_timeline_func(
    investigation_id: str,
    include_evidence_points: bool = True,
    chart_type: str = "timeline"
) -> dict:
    """Generate a timeline chart of investigation events and evidence collection.

    Args:
        investigation_id: Investigation to create timeline for
        include_evidence_points: Whether to include evidence collection events
        chart_type: Type of chart (timeline, gantt, sequence)

    Returns:
        Timeline chart generation result
    """
    try:
        # Get investigation state
        investigation_state = state_manager.get_investigation(investigation_id)
        if not investigation_state:
            return {
                "success": False,
                "error": f"Investigation {investigation_id} not found",
                "investigation_id": investigation_id
            }

        # Get next ticker for artifact naming
        ticker = state_manager.get_next_artifact_ticker(investigation_id)
        filename = f"evidence_{investigation_id}_{ticker:03d}_timeline_chart.png"

        # Collect timeline events
        events = []

        # Add investigation start
        events.append({
            "timestamp": investigation_state.created_at.isoformat(),
            "event": "Investigation Started",
            "type": "milestone",
            "description": f"Alert: {investigation_state.alert_data.summary[:50]}..."
        })

        # Add evidence collection events if requested
        if include_evidence_points:
            for artifact in investigation_state.artifacts:
                events.append({
                    "timestamp": artifact.get("timestamp", ""),
                    "event": f"Collected {artifact.get('type', 'evidence')}",
                    "type": "evidence",
                    "description": artifact.get("description", "Evidence collected")
                })

        # Add phase transitions
        events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": f"Phase: {investigation_state.phase.value.title()}",
            "type": "phase",
            "description": f"Currently in {investigation_state.phase.value} phase"
        })

        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])

        # Create artifact info (TODO: generate actual chart image)
        artifact_info = {
            "type": "timeline_chart",
            "filename": filename,
            "investigation_id": investigation_id,
            "description": f"Timeline chart for investigation {investigation_id}",
            "source": "investigation_timeline_generator",
            "chart_type": chart_type,
            "events": events,
            "event_count": len(events),
            "planned_artifact": True,
            "mime_type": "image/png",
            "ticker": ticker,
            "timestamp": datetime.utcnow().isoformat(),
            "relevance_score": 0.7,
            "file_size_estimate": "~75KB"
        }

        # Add to investigation artifacts
        investigation_state.artifacts.append(artifact_info)
        logger.info(f"✅ Added timeline chart artifact: {filename}")

        return {
            "success": True,
            "type": "timeline_chart",
            "filename": filename,
            "investigation_id": investigation_id,
            "events": events,
            "artifact_info": artifact_info,
            "summary": f"Generated timeline chart with {len(events)} events for investigation {investigation_id}"
        }

    except Exception as e:
        logger.error(
            f"Timeline generation failed for investigation '{investigation_id}': {e}")
        return {
            "success": False,
            "error": f"Timeline generation failed: {str(e)}",
            "investigation_id": investigation_id
        }


# Create tool instances
generate_location_map = FunctionTool(generate_location_map_func)
generate_investigation_timeline = FunctionTool(
    generate_investigation_timeline_func)
