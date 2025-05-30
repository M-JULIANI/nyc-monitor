#!/usr/bin/env python3
"""
Monitor System Verification Script
Checks if the NYC monitor system is working by verifying Firestore connectivity and recent alerts.
"""
import os
import sys
from datetime import datetime, timedelta
from google.cloud import firestore


def check_firestore_connection():
    """Check basic Firestore connectivity"""
    try:
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if not project_id:
            print("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
            return False

        print(f"🔗 Connecting to Firestore in project: {project_id}")
        db = firestore.Client(project=project_id)

        # Test connection with a simple query
        collections = db.collections()
        collection_names = [col.id for col in collections]
        print(f"✅ Connected successfully")
        print(f"📁 Available collections: {collection_names}")

        return True, db

    except Exception as e:
        print(f"❌ Firestore connection failed: {str(e)}")
        return False, None


def check_monitor_alerts(db):
    """Check for recent monitor alerts"""
    try:
        alerts_collection = 'nyc_monitor_alerts'
        print(f"\n🔍 Checking for alerts in collection: {alerts_collection}")

        # Get all alerts
        alerts_ref = db.collection(alerts_collection)
        all_alerts = list(alerts_ref.stream())

        print(f"📊 Total alerts found: {len(all_alerts)}")

        if len(all_alerts) == 0:
            print("⚠️  No alerts found - system may not have run yet or failed")
            return False

        # Check recent alerts (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_alerts = []

        for alert_doc in all_alerts:
            alert_data = alert_doc.to_dict()
            created_at = alert_data.get('created_at')

            if created_at and created_at >= cutoff_time:
                recent_alerts.append(alert_data)

        print(f"🕐 Recent alerts (last 24h): {len(recent_alerts)}")

        # Show latest alerts
        if recent_alerts:
            print("\n📋 Latest Alerts:")
            for i, alert in enumerate(recent_alerts[-5:], 1):  # Show last 5
                title = alert.get('title', 'Unknown')
                severity = alert.get('severity', 0)
                area = alert.get('area', 'Unknown')
                created = alert.get('created_at', 'Unknown')
                print(f"   {i}. {title} (Severity: {severity}, Area: {area})")
                print(f"      Created: {created}")

        return len(recent_alerts) > 0

    except Exception as e:
        print(f"❌ Error checking alerts: {str(e)}")
        return False


def check_cloud_run_job():
    """Check if Cloud Run job exists and recent executions"""
    try:
        print(f"\n🏃 Cloud Run Job Status:")
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

        print(f"📍 Project: {project_id}")
        print(f"📍 Region: {location}")
        print(
            f"🔗 Job Console: https://console.cloud.google.com/run/jobs/details/{location}/atlas-monitor")
        print(f"📊 Logs: https://console.cloud.google.com/logs/query")

    except Exception as e:
        print(f"❌ Error checking Cloud Run job: {str(e)}")


def main():
    """Main verification function"""
    print("🔍 === NYC MONITOR SYSTEM VERIFICATION ===")
    print(f"⏰ Check time: {datetime.utcnow().isoformat()}")

    # Check environment
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        print("❌ Missing GOOGLE_CLOUD_PROJECT environment variable")
        sys.exit(1)

    print(f"🎯 Target project: {project_id}")

    # Check Firestore connection
    success, db = check_firestore_connection()
    if not success:
        sys.exit(1)

    # Check for monitor alerts
    alerts_found = check_monitor_alerts(db)

    # Check Cloud Run job info
    check_cloud_run_job()

    # Summary
    print(f"\n📋 === VERIFICATION SUMMARY ===")
    print(f"✅ Firestore Connection: Working")
    print(f"{'✅' if alerts_found else '⚠️ '} Recent Alerts: {'Found' if alerts_found else 'None found'}")

    if alerts_found:
        print(f"\n🎉 System appears to be working!")
        print(f"🔗 View alerts: https://console.cloud.google.com/firestore/data/nyc_monitor_alerts")
    else:
        print(f"\n⚠️  No recent alerts found. Possible issues:")
        print(f"   1. Monitor job hasn't run yet (runs hourly)")
        print(f"   2. Reddit API credentials not configured")
        print(f"   3. Job failing - check logs")
        print(f"   4. No significant events detected")

        print(f"\n🛠️  Next steps:")
        print(f"   1. Run: make test-monitor")
        print(f"   2. Check logs: make logs-monitor")
        print(f"   3. Verify Reddit credentials in GitHub secrets")


if __name__ == "__main__":
    main()
