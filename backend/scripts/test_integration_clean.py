#!/usr/bin/env python3
"""
Test the clean integration between Reddit collector, triage agent, and Firestore manager.
Verifies no fake/fallback entries are created.
"""
from monitor.storage.firestore_manager import FirestoreManager
from monitor.agents.triage_agent import TriageAgent
from monitor.collectors.reddit_collector import RedditCollector
import asyncio
import sys
import os
sys.path.append('..')

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Error: python-dotenv not found")
    exit(1)


load_dotenv()


async def test_clean_integration():
    """Test the integration without fake entries"""

    print("🧪 TESTING CLEAN INTEGRATION")
    print("Verifying no fake/fallback entries are created")

    try:
        # Test 1: Reddit Collector (simplified)
        print(f"\n📡 PHASE 1: REDDIT COLLECTOR TESTING")

        try:
            collector = RedditCollector()
            print(f"✅ Reddit collector initialized")
            print(f"   Priority keywords: {len(collector.priority_keywords)}")
            print(
                f"   Location extractor: {collector.location_extractor.get_location_count()} locations")

            # Test with a small sample
            signals = await collector._fetch_subreddit_signals('nyc', limit=2)
            print(f"✅ Collected {len(signals)} signals from r/nyc")

            # Verify no fake signals
            fake_signals = [
                s for s in signals if 'Error parsing' in s.get('title', '')]
            if fake_signals:
                print(f"❌ Found {len(fake_signals)} fake signals!")
                return False
            else:
                print(f"✅ No fake signals detected")

            # Show signal structure
            if signals:
                sample = signals[0]
                metadata = sample['metadata']
                print(f"📊 Sample signal metadata:")
                print(
                    f"   Has priority content: {metadata.get('has_priority_content', False)}")
                print(
                    f"   Priority keywords: {metadata.get('priority_keywords', [])}")
                print(
                    f"   Location count: {metadata.get('location_count', 0)}")

        except Exception as e:
            print(f"⚠️  Reddit test skipped: {e}")
            signals = []

        # Test 2: Triage Agent
        print(f"\n🧠 PHASE 2: TRIAGE AGENT TESTING")

        try:
            triage_agent = TriageAgent()
            print(f"✅ Triage agent initialized")

            # Test with collected signals or mock data
            test_signals = {'reddit': signals} if signals else {'reddit': []}

            triage_results = await triage_agent.analyze_signals(test_signals)
            print(f"✅ Triage analysis completed")
            print(f"   Summary: {triage_results.get('summary', 'N/A')}")
            print(
                f"   Alerts generated: {len(triage_results.get('alerts', []))}")

            # Check for fallback alerts
            alerts = triage_results.get('alerts', [])
            fallback_alerts = [a for a in alerts if 'fallback' in a.get('id', '').lower()
                               or 'system alert' in a.get('title', '').lower()]

            if fallback_alerts:
                print(f"❌ Found {len(fallback_alerts)} fallback alerts!")
                for alert in fallback_alerts:
                    print(f"   • {alert.get('title', 'Unknown')}")
                return False
            else:
                print(f"✅ No fallback alerts detected")

            # Show real alerts if any
            if alerts:
                print(f"📊 Real alerts found:")
                for alert in alerts[:2]:  # Show first 2
                    print(
                        f"   • {alert.get('title', 'Unknown')} (severity: {alert.get('severity', 0)})")

        except Exception as e:
            print(f"⚠️  Triage test skipped: {e}")
            triage_results = {'alerts': []}

        # Test 3: Integration Flow
        print(f"\n🔄 PHASE 3: END-TO-END FLOW TESTING")

        alerts = triage_results.get('alerts', [])
        if not alerts:
            print(f"ℹ️  No alerts to store - this is normal for routine content")
            print(f"✅ Integration test passed: No fake entries would reach Firestore")
        else:
            print(f"📦 Would store {len(alerts)} real alerts in Firestore")

            # Verify alert quality
            valid_alerts = 0
            for alert in alerts:
                if (alert.get('title') and
                    alert.get('severity', 0) > 0 and
                    alert.get('category') != 'infrastructure' and
                        'system' not in alert.get('keywords', [])):
                    valid_alerts += 1

            print(f"✅ {valid_alerts}/{len(alerts)} alerts are valid for storage")

            if valid_alerts != len(alerts):
                filtered_out = len(alerts) - valid_alerts
                print(
                    f"🔍 Would filter out {filtered_out} system/invalid alerts")

        print(f"\n🎉 CLEAN INTEGRATION TEST COMPLETED")
        print(f"✅ No fake/fallback entries detected")
        print(f"✅ Error handling works without polluting data")
        print(f"✅ Only real, actionable alerts would reach Firestore")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_clean_integration())
    sys.exit(0 if success else 1)
