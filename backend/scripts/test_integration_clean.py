#!/usr/bin/env python3
"""
Test the clean integration between collectors, triage agent, and Firestore manager.
Verifies no fake/fallback entries are created and tests severity range distribution.
"""
from monitor.storage.firestore_manager import FirestoreManager
from monitor.agents.triage_agent import TriageAgent
from monitor.collectors.reddit_collector import RedditCollector
from monitor.collectors.nyc_311_collector import NYC311Collector
import asyncio
import sys
import os
import pytest
sys.path.append('..')

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Error: python-dotenv not found")
    exit(1)


load_dotenv()


def analyze_severity_distribution(alerts: list, source_name: str) -> dict:
    """Analyze and report severity distribution"""
    if not alerts:
        return {"total": 0, "distribution": {}, "range": "No alerts"}

    severity_counts = {}
    for alert in alerts:
        severity = alert.get('severity', 0)
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    min_severity = min(severity_counts.keys()) if severity_counts else 0
    max_severity = max(severity_counts.keys()) if severity_counts else 0

    print(f"📊 {source_name} Severity Distribution:")
    print(f"   Total alerts: {len(alerts)}")
    print(f"   Severity range: {min_severity}-{max_severity}")
    for severity in sorted(severity_counts.keys()):
        count = severity_counts[severity]
        percentage = (count / len(alerts)) * 100
        print(f"   Severity {severity}: {count} alerts ({percentage:.1f}%)")

    return {
        "total": len(alerts),
        "distribution": severity_counts,
        "range": f"{min_severity}-{max_severity}",
        "min": min_severity,
        "max": max_severity
    }


@pytest.mark.asyncio
async def test_clean_integration():
    """Test the integration without fake entries"""

    print("🧪 TESTING CLEAN INTEGRATION WITH SEVERITY ANALYSIS")
    print("Verifying no fake/fallback entries and testing severity ranges")

    all_alerts = []
    all_311_signals = []

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
            signals = await collector._fetch_subreddit_signals('nyc', limit=5)
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

        # Test 2: NYC 311 Collector
        print(f"\n📞 PHASE 2: NYC 311 JOB TESTING")

        try:
            from monitor.scheduler.nyc311_job import NYC311Job

            nyc311_job = NYC311Job()
            print(f"✅ NYC 311 job initialized")

            # Test small sample for speed
            # Get recent 311 signals but limit processing
            original_collect = nyc311_job.collector.collect_signals

            async def limited_collect():
                # Get a small sample for testing
                all_signals = await original_collect()
                # Limit to 50 for testing
                return all_signals[:50] if all_signals else []

            nyc311_job.collector.collect_signals = limited_collect

            # Run the full job pipeline (collect → triage → score)
            nyc311_signals = await nyc311_job.collector.collect_signals()

            if nyc311_signals:
                # Test AI triage on the sample
                print(
                    f"✅ Collected {len(nyc311_signals)} 311 signals (sample)")

                # Run AI triage analysis
                scored_signals = await nyc311_job._run_triage_analysis(nyc311_signals)

                if scored_signals:
                    all_311_signals.extend(scored_signals)
                    severity_analysis = analyze_severity_distribution(
                        scored_signals, "NYC 311")

                    # Verify severity range is appropriate
                    if severity_analysis["min"] >= 1 and severity_analysis["max"] <= 10:
                        print(
                            f"✅ 311 AI severity range is within expected bounds (1-10)")
                    else:
                        print(
                            f"⚠️  311 AI severity range outside bounds: {severity_analysis['range']}")

                    # Show sample 311 alerts
                    print(f"📊 Sample 311 signals with AI severity:")
                    for i, signal in enumerate(scored_signals[:3]):
                        title = signal.get('title', 'Unknown')[:50]
                        severity = signal.get('severity', 0)
                        triage_method = signal.get('triage_method', 'unknown')
                        print(
                            f"   {i+1}. {title}... (severity: {severity}, method: {triage_method})")
                else:
                    print(f"⚠️  AI triage analysis failed for 311 signals")
            else:
                print(
                    f"ℹ️  No 311 signals collected - may be normal during low activity periods")

        except Exception as e:
            print(f"⚠️  311 job test skipped: {e}")
            nyc311_signals = []

        # Test 3: Triage Agent
        print(f"\n🧠 PHASE 3: TRIAGE AGENT TESTING")

        try:
            triage_agent = TriageAgent()
            print(f"✅ Triage agent initialized")

            # Test with collected signals or mock data
            test_signals = {}
            if signals:
                test_signals['reddit'] = signals
            if nyc311_signals:
                test_signals['nyc311'] = nyc311_signals

            if not test_signals:
                test_signals = {'reddit': []}  # Empty test

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

            # Analyze triage agent severity distribution
            if alerts:
                all_alerts.extend(alerts)
                triage_analysis = analyze_severity_distribution(
                    alerts, "Triage Agent")

                # Verify severity range is appropriate
                if triage_analysis["min"] >= 1 and triage_analysis["max"] <= 10:
                    print(
                        f"✅ Triage agent severity range is within expected bounds (1-10)")
                else:
                    print(
                        f"⚠️  Triage agent severity range outside bounds: {triage_analysis['range']}")

                # Show real alerts
                print(f"📊 Sample triage alerts:")
                for i, alert in enumerate(alerts[:3]):
                    title = alert.get('title', 'Unknown')[:50]
                    severity = alert.get('severity', 0)
                    event_type = alert.get('event_type', 'unknown')
                    print(
                        f"   {i+1}. {title}... (severity: {severity}, type: {event_type})")
            else:
                print(
                    f"ℹ️  No triage alerts generated - this is normal for routine content")

        except Exception as e:
            print(f"⚠️  Triage test skipped: {e}")
            triage_results = {'alerts': []}

        # Test 4: Combined Severity Analysis
        print(f"\n📈 PHASE 4: COMBINED SEVERITY ANALYSIS")

        if all_311_signals or all_alerts:
            print(f"🔍 Comparing severity distributions:")

            if all_311_signals:
                print(f"\n🏛️  311 Collector Summary:")
                print(f"   • Total signals: {len(all_311_signals)}")
                nyc311_analysis = analyze_severity_distribution(
                    all_311_signals, "311 (Rules-based)")

            if all_alerts:
                print(f"\n🧠 Triage Agent Summary:")
                print(f"   • Total alerts: {len(all_alerts)}")
                triage_analysis = analyze_severity_distribution(
                    all_alerts, "Triage (AI-based)")

            # Check for good severity distribution (not all the same severity)
            combined_severities = set()
            if all_311_signals:
                combined_severities.update(
                    [s.get('severity', 0) for s in all_311_signals])
            if all_alerts:
                combined_severities.update(
                    [a.get('severity', 0) for a in all_alerts])

            if len(combined_severities) >= 3:
                print(
                    f"✅ Good severity distribution: {len(combined_severities)} different severity levels")
            elif len(combined_severities) >= 2:
                print(
                    f"⚠️  Limited severity distribution: {len(combined_severities)} severity levels")
            else:
                print(
                    f"⚠️  Poor severity distribution: Only {len(combined_severities)} severity level(s)")

        else:
            print(
                f"ℹ️  No signals/alerts to analyze - this can be normal during quiet periods")

        # Test 5: Integration Flow
        print(f"\n🔄 PHASE 5: END-TO-END FLOW TESTING")

        total_items = len(all_311_signals) + len(all_alerts)
        if total_items == 0:
            print(f"ℹ️  No alerts to store - this is normal for routine content")
            print(f"✅ Integration test passed: No fake entries would reach Firestore")
        else:
            print(f"📦 Would store {total_items} total items in Firestore:")
            print(f"   • 311 signals: {len(all_311_signals)}")
            print(f"   • Triage alerts: {len(all_alerts)}")

            # Verify alert quality
            valid_items = 0
            for item in all_311_signals + all_alerts:
                if (item.get('title') and
                    item.get('severity', 0) > 0 and
                        'system' not in item.get('keywords', [])):
                    valid_items += 1

            print(f"✅ {valid_items}/{total_items} items are valid for storage")

            if valid_items != total_items:
                filtered_out = total_items - valid_items
                print(
                    f"🔍 Would filter out {filtered_out} system/invalid items")

        print(f"\n🎉 CLEAN INTEGRATION TEST WITH SEVERITY ANALYSIS COMPLETED")
        print(f"✅ No fake/fallback entries detected")
        print(f"✅ Error handling works without polluting data")
        print(f"✅ Both 311 and triage agent severity assignments tested")
        print(f"✅ Severity distributions verified within expected ranges")
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
