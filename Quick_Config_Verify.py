"""
Quick Configuration Verification Script
Run this in Ignition Designer Script Console to verify health monitor settings

Based on your SiteSync project implementation
"""

import json

print("=" * 80)
print("QUICK CONFIGURATION VERIFICATION")
print("=" * 80)

# Test 1: SiteSync API (YOUR PROJECT USES THIS!)
print("\n1. SiteSync API Test:")
try:
    tenantID = 1
    result = system.sitesync.testJoinAPIImpl(tenantID)
    if result and "error" not in str(result).lower():
        print("   [OK] SiteSync API working")
        print("   Result: " + str(result)[:80])
    else:
        print("   [WARN] API returned error: " + str(result)[:80])
except Exception as e:
    print("   [ERROR] " + str(e))

# Test 2: MQTT Transmission Tag Path
print("\n2. MQTT Transmission Tag:")
mqtt_tag = "[MQTT Transmission]Transmission Info/Connected"
if system.tag.exists(mqtt_tag):
    qv = system.tag.readBlocking([mqtt_tag])[0]
    print("   [OK] Tag exists - Value: " + str(qv.value))
else:
    print("   [MISSING] Tag not found")
    print("   >> FIX: In health monitor script, set:")
    print("      MQTT_TX_STATUS_TAG = None")

# Test 3: Device Tags Path
print("\n3. Device Tags:")
devices_root = "[default]SiteSync/Devices"
if system.tag.exists(devices_root):
    results = system.tag.browse(devices_root, {"recursive": False})
    count = len(results.getResults())
    print("   [OK] Found %d device folders" % count)
    if count == 0:
        print("   [WARN] No devices yet")
else:
    print("   [MISSING] Path not found: " + devices_root)
    print("   >> FIX: Update DEVICES_ROOT in health monitor script")

# Test 4: PI Adapter (YOUR PROJECT USES THIS!)
print("\n4. PI Adapter:")
try:
    adapter = system.piAdapter.getSettings("adapter")
    webapi = system.piAdapter.getSettings("webAPI")

    if adapter and adapter != "null":
        print("   [OK] PI Adapter configured")
    else:
        print("   [WARN] PI Adapter not configured")

    if webapi and webapi != "null":
        print("   [OK] PI Web API configured")
    else:
        print("   [WARN] PI Web API not configured")
except Exception as e:
    print("   [ERROR] " + str(e))

# Test 5: Check if Health tags are at correct path
print("\n5. Health Tag Structure:")
correct = "[default]Health/MQTT_Broker"
wrong = "[default]Health/Health/MQTT_Broker"

if system.tag.exists(correct):
    print("   [OK] Tags at correct location")
elif system.tag.exists(wrong):
    print("   [ERROR] Duplicate Health folder detected!")
    print("   >> FIX: Run the cleanup script from previous messages")
else:
    print("   [INFO] Tags not created yet - timer will create them")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print("\nRECOMMENDED CHANGES TO HEALTH MONITOR SCRIPT:")
print("\n1. If MQTT Transmission tag is MISSING:")
print("   Change line 41 to:")
print("   MQTT_TX_STATUS_TAG = None")
print("")
print("2. If Device path is MISSING:")
print("   Change line 36 to match your actual device path")
print("   OR disable ThingPark_Inbound check temporarily")
print("")
print("3. All other settings look correct based on your project scripts!")
