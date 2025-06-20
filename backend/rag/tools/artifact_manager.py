#!/usr/bin/env python3
"""
GCS-based Artifact Manager for NYC Atlas Investigation System.
Uses Vertex AI native artifact services and the existing staging bucket.
"""

import os
import logging
import requests
import io
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union
from pathlib import Path
from google.cloud import storage
from google.adk.artifacts import GcsArtifactService
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)

# Configuration
STAGING_BUCKET = os.getenv("STAGING_BUCKET", "gs://atlas-460522-vertex-deploy")
ARTIFACTS_PREFIX = "artifacts/investigations"

# Extract bucket name from gs:// URL
BUCKET_NAME = STAGING_BUCKET.replace("gs://", "").split("/")[0]


class AtlasArtifactManager:
    """
    GCS-based artifact manager using Vertex AI native services.
    Stores artifacts in the existing staging bucket with proper organization.
    """

    def __init__(self):
        self.bucket_name = BUCKET_NAME
        self.artifacts_prefix = ARTIFACTS_PREFIX
        self.storage_client = None
        self.bucket = None
        self.adk_artifact_service = None

        # Initialize GCS client and ADK artifact service
        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.bucket_name)

            # Use ADK's native GCS artifact service
            self.adk_artifact_service = GcsArtifactService(
                bucket_name=self.bucket_name)

            logger.info(
                f"✅ Initialized Atlas Artifact Manager with bucket: {self.bucket_name}")

        except Exception as e:
            logger.warning(
                f"⚠️ Could not initialize Google Cloud Storage: {e}")
            logger.info(
                "🔧 Artifact manager will operate in limited mode (no GCS operations)")
            # Don't raise - allow the application to continue without GCS

    def _ensure_gcs_initialized(self) -> bool:
        """Ensure GCS is initialized before operations."""
        if self.storage_client is None:
            logger.error(
                "❌ Google Cloud Storage not initialized - cannot perform GCS operations")
            return False
        return True

    def save_artifact(
        self,
        investigation_id: str,
        artifact_type: str,
        data: Union[bytes, str],
        filename: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Save an artifact to GCS with proper organization.

        Args:
            investigation_id: Investigation ID for organization
            artifact_type: Type of artifact (maps, screenshots, images, documents)
            data: Artifact data (bytes or string)
            filename: Filename for the artifact
            content_type: MIME type of the artifact
            metadata: Additional metadata to store

        Returns:
            Dict with artifact information including public and signed URLs
        """
        # Check if GCS is initialized
        if not self._ensure_gcs_initialized():
            return {
                "success": False,
                "error": "Google Cloud Storage not initialized",
                "investigation_id": investigation_id,
                "filename": filename
            }

        try:
            # Create organized path: artifacts/investigations/{investigation_id}/{artifact_type}/{filename}
            artifact_path = f"{self.artifacts_prefix}/{investigation_id}/{artifact_type}/{filename}"

            # Prepare data
            if isinstance(data, str):
                data = data.encode('utf-8')

            # Create blob and upload
            blob = self.bucket.blob(artifact_path)

            # Set metadata
            if metadata:
                blob.metadata = metadata

            # Upload with content type
            blob.upload_from_string(data, content_type=content_type)

            # Generate URLs
            gcs_url = f"gs://{self.bucket_name}/{artifact_path}"
            public_url = blob.public_url

            # Generate signed URL (valid for 4 hours - good for Google Slides)
            # Handle cases where signed URL generation might fail in development
            signed_url = None
            try:
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.utcnow() + timedelta(hours=4),
                    method="GET"
                )
                logger.debug(f"✅ Generated signed URL for {filename}")
            except Exception as signed_url_error:
                logger.warning(
                    f"⚠️ Could not generate signed URL for {filename}: {signed_url_error}")
                logger.info(
                    "Using public URL as fallback (may require bucket to be public)")
                signed_url = public_url

            artifact_info = {
                "success": True,
                "investigation_id": investigation_id,
                "artifact_type": artifact_type,
                "filename": filename,
                "gcs_path": artifact_path,
                "gcs_url": gcs_url,
                "public_url": public_url,
                "signed_url": signed_url,
                "content_type": content_type,
                "size_bytes": len(data),
                "created_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            logger.info(
                f"✅ Saved artifact: {artifact_path} ({len(data)} bytes)")
            return artifact_info

        except Exception as e:
            logger.error(f"❌ Failed to save artifact {filename}: {e}")
            return {
                "success": False,
                "error": f"Failed to save artifact: {str(e)}",
                "investigation_id": investigation_id,
                "filename": filename
            }

    def download_and_save_image(
        self,
        investigation_id: str,
        image_url: str,
        artifact_type: str = "images",
        description: str = "",
        timeout: int = 30
    ) -> Dict:
        """
        Download an image from a URL and save it to GCS.

        Args:
            investigation_id: Investigation ID
            image_url: URL of the image to download
            artifact_type: Type of artifact (images, screenshots, maps)
            description: Description of the image
            timeout: Download timeout in seconds

        Returns:
            Dict with saved artifact information
        """
        # Check if GCS is initialized
        if not self._ensure_gcs_initialized():
            return {
                "success": False,
                "error": "Google Cloud Storage not initialized",
                "image_url": image_url,
                "investigation_id": investigation_id
            }

        try:
            # Download the image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(
                image_url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Determine file extension from content type or URL
            content_type = response.headers.get(
                'content-type', 'application/octet-stream')

            if 'image/jpeg' in content_type or image_url.lower().endswith(('.jpg', '.jpeg')):
                ext = '.jpg'
                content_type = 'image/jpeg'
            elif 'image/png' in content_type or image_url.lower().endswith('.png'):
                ext = '.png'
                content_type = 'image/png'
            elif 'image/gif' in content_type or image_url.lower().endswith('.gif'):
                ext = '.gif'
                content_type = 'image/gif'
            elif 'image/webp' in content_type or image_url.lower().endswith('.webp'):
                ext = '.webp'
                content_type = 'image/webp'
            else:
                ext = '.jpg'  # Default fallback
                content_type = 'image/jpeg'

            # Generate filename with better uniqueness
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Add microseconds for even better uniqueness
            microsecond_suffix = datetime.now().strftime("%f")[:3]
            filename = f"{artifact_type}_{investigation_id}_{timestamp}_{microsecond_suffix}_{url_hash}{ext}"

            # Prepare metadata
            metadata = {
                "source_url": image_url,
                "description": description,
                "downloaded_at": datetime.utcnow().isoformat(),
                "content_length": str(len(response.content))
            }

            # Save to GCS
            return self.save_artifact(
                investigation_id=investigation_id,
                artifact_type=artifact_type,
                data=response.content,
                filename=filename,
                content_type=content_type,
                metadata=metadata
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to download and save image {image_url}: {e}")
            return {
                "success": False,
                "error": f"Failed to download image: {str(e)}",
                "image_url": image_url,
                "investigation_id": investigation_id
            }

    def generate_google_maps_image(
        self,
        investigation_id: str,
        location: str,
        zoom_level: int = 16,
        map_type: str = "satellite",
        include_pin: bool = True,
        size: str = "640x640"
    ) -> Dict:
        """
        Generate and save a Google Maps static image to GCS.

        Args:
            investigation_id: Investigation ID
            location: Location to map
            zoom_level: Map zoom level
            map_type: Map type (satellite, roadmap, hybrid, terrain)
            include_pin: Whether to include a location pin
            size: Image size

        Returns:
            Dict with saved map artifact information
        """
        # Check if GCS is initialized
        if not self._ensure_gcs_initialized():
            return {
                "success": False,
                "error": "Google Cloud Storage not initialized",
                "location": location,
                "investigation_id": investigation_id
            }

        try:
            # Get Google Maps API key
            api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
            if not api_key:
                raise ValueError("GOOGLE_MAPS_API_KEY not configured")

            # Build Google Maps Static API URL
            base_url = "https://maps.googleapis.com/maps/api/staticmap"
            params = {
                "center": location,
                "zoom": zoom_level,
                "size": size,
                "maptype": map_type,
                "key": api_key,
                "format": "png"
            }

            # Add marker pin if requested
            if include_pin:
                params["markers"] = f"color:red|size:mid|{location}"

            # Make API request
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            # Validate response is an image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise ValueError(f"Invalid response type: {content_type}")

            # Generate filename with better uniqueness
            location_clean = location.replace(
                ' ', '_').replace(',', '').replace('/', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Add microseconds for better uniqueness
            microsecond_suffix = datetime.now().strftime("%f")[:3]
            filename = f"map_{investigation_id}_{timestamp}_{microsecond_suffix}_{location_clean}.png"

            # Prepare metadata
            metadata = {
                "location": location,
                "zoom_level": str(zoom_level),
                "map_type": map_type,
                "include_pin": str(include_pin),
                "size": size,
                "api_source": "google_maps_static_api",
                "generated_at": datetime.utcnow().isoformat()
            }

            # Save to GCS
            result = self.save_artifact(
                investigation_id=investigation_id,
                artifact_type="maps",
                data=response.content,
                filename=filename,
                content_type="image/png",
                metadata=metadata
            )

            if result["success"]:
                result["map_metadata"] = metadata
                logger.info(
                    f"✅ Generated and saved Google Maps image: {filename}")

            return result

        except Exception as e:
            logger.error(
                f"❌ Failed to generate Google Maps image for {location}: {e}")
            return {
                "success": False,
                "error": f"Failed to generate map: {str(e)}",
                "location": location,
                "investigation_id": investigation_id
            }

    def list_investigation_artifacts(self, investigation_id: str) -> Dict:
        """
        List all artifacts for an investigation.

        Args:
            investigation_id: Investigation ID

        Returns:
            Dict with list of artifacts and summary
        """
        # Check if GCS is initialized
        if not self._ensure_gcs_initialized():
            return {
                "success": False,
                "error": "Google Cloud Storage not initialized",
                "investigation_id": investigation_id,
                "total_artifacts": 0,
                "artifacts": []
            }

        try:
            prefix = f"{self.artifacts_prefix}/{investigation_id}/"
            blobs = list(self.bucket.list_blobs(prefix=prefix))

            artifacts = []
            total_size = 0

            for blob in blobs:
                # Parse artifact info from path
                path_parts = blob.name.split('/')
                if len(path_parts) >= 4:
                    artifact_type = path_parts[-2]
                    filename = path_parts[-1]

                    artifacts.append({
                        "filename": filename,
                        "artifact_type": artifact_type,
                        "gcs_path": blob.name,
                        "gcs_url": f"gs://{self.bucket_name}/{blob.name}",
                        "public_url": blob.public_url,
                        "size_bytes": blob.size,
                        "content_type": blob.content_type,
                        "created": blob.time_created.isoformat() if blob.time_created else None,
                        "metadata": blob.metadata or {}
                    })

                    total_size += blob.size or 0

            # Group by type
            by_type = {}
            for artifact in artifacts:
                artifact_type = artifact["artifact_type"]
                if artifact_type not in by_type:
                    by_type[artifact_type] = []
                by_type[artifact_type].append(artifact)

            return {
                "success": True,
                "investigation_id": investigation_id,
                "total_artifacts": len(artifacts),
                "total_size_bytes": total_size,
                "artifacts": artifacts,
                "by_type": by_type,
                "summary": f"Found {len(artifacts)} artifacts ({total_size} bytes) for investigation {investigation_id}"
            }

        except Exception as e:
            logger.error(
                f"❌ Failed to list artifacts for {investigation_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to list artifacts: {str(e)}",
                "investigation_id": investigation_id
            }

    # =========================================================================
    # DEPRECATED: Public/Private Access Management Methods
    # These methods are no longer needed with the service account approach
    # but are kept for potential future use or emergency fallbacks
    # =========================================================================

    # def make_artifact_public_for_slides(self, investigation_id: str, filename: str, duration_hours: int = 4) -> Dict:
    #     """
    #     DEPRECATED: Use get_slides_accessible_url() instead.
    #     Temporarily make an artifact public for Google Slides access.
    #     """
    #     # Implementation kept but commented out...
    #     pass

    # def cleanup_public_artifacts(self, investigation_id: str) -> Dict:
    #     """
    #     DEPRECATED: No longer needed with service account approach.
    #     Clean up public artifacts by making them private again.
    #     """
    #     # Implementation kept but commented out...
    #     pass

    def get_slides_accessible_url(self, investigation_id: str, filename: str) -> Dict:
        """
        Generate a signed URL that Google Slides can access using the same service account.
        This is much cleaner than making artifacts public temporarily.

        Args:
            investigation_id: Investigation ID
            filename: Artifact filename

        Returns:
            Dict with signed URL that Google Slides service account can access
        """
        try:
            # Find the artifact blob
            artifact_path = f"{self.artifacts_prefix}/{investigation_id}"
            blobs = list(self.bucket.list_blobs(prefix=artifact_path))

            target_blob = None
            for blob in blobs:
                if filename in blob.name:
                    target_blob = blob
                    break

            if not target_blob:
                return {
                    "success": False,
                    "error": f"Artifact {filename} not found",
                    "url": None
                }

            # Try to generate signed URL using the same service account as Google Slides
            try:
                # Import the same credential logic as Google Slides
                import base64
                import json
                from google.oauth2 import service_account
                from google.auth import default

                credentials = None

                # Use the same credential priority as Google Slides
                google_service_account_key_b64 = os.getenv(
                    "GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64")
                if google_service_account_key_b64:
                    try:
                        # Decode base64 and parse JSON
                        service_account_json = base64.b64decode(
                            google_service_account_key_b64).decode('utf-8')
                        service_account_info = json.loads(service_account_json)
                        credentials = service_account.Credentials.from_service_account_info(
                            service_account_info,
                            scopes=[
                                'https://www.googleapis.com/auth/cloud-platform']
                        )
                        logger.debug(
                            "Using Google Slides service account for signed URL")
                    except Exception as e:
                        logger.debug(
                            f"Could not use base64 service account: {e}")

                # Try service account key file
                if not credentials:
                    service_account_key_path = os.getenv(
                        "GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "atlas-reports-key.json")
                    if os.path.exists(service_account_key_path):
                        credentials = service_account.Credentials.from_service_account_file(
                            service_account_key_path,
                            scopes=[
                                'https://www.googleapis.com/auth/cloud-platform']
                        )
                        logger.debug(
                            "Using Google Slides service account file for signed URL")

                # If we have service account credentials, create a new blob instance with them
                if credentials:
                    from google.cloud import storage
                    signed_storage_client = storage.Client(
                        credentials=credentials)
                    signed_bucket = signed_storage_client.bucket(
                        self.bucket_name)
                    signed_blob = signed_bucket.blob(target_blob.name)

                    # Generate signed URL (valid for 4 hours)
                    signed_url = signed_blob.generate_signed_url(
                        version="v4",
                        expiration=datetime.utcnow() + timedelta(hours=4),
                        method="GET"
                    )

                    logger.info(
                        f"✅ Generated signed URL using Google Slides service account: {filename}")

                    return {
                        "success": True,
                        "url": signed_url,
                        "url_type": "signed_url_service_account",
                        "filename": filename,
                        "expires_at": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
                        "accessible_by": "google_slides_service_account"
                    }

            except Exception as e:
                logger.debug(
                    f"Could not generate signed URL with service account: {e}")

            # Fallback: try with default credentials (development environment)
            try:
                signed_url = target_blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.utcnow() + timedelta(hours=4),
                    method="GET"
                )

                logger.info(
                    f"✅ Generated signed URL using default credentials: {filename}")

                return {
                    "success": True,
                    "url": signed_url,
                    "url_type": "signed_url_default",
                    "filename": filename,
                    "expires_at": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
                    "accessible_by": "default_credentials"
                }

            except Exception as e:
                logger.warning(
                    f"Could not generate signed URL with default credentials: {e}")

            # Final fallback: return public URL but warn that it may not work
            public_url = target_blob.public_url
            logger.warning(
                f"⚠️ Falling back to public URL (may not be accessible): {filename}")

            return {
                "success": True,
                "url": public_url,
                "url_type": "public_url_fallback",
                "filename": filename,
                "warning": "Using public URL - may require bucket to be public or proper service account access",
                "accessible_by": "public_access_required"
            }

        except Exception as e:
            logger.error(f"❌ Failed to get Slides-accessible URL: {e}")
            return {
                "success": False,
                "error": f"Failed to get accessible URL: {str(e)}",
                "url": None
            }


# Global instance
artifact_manager = AtlasArtifactManager()
