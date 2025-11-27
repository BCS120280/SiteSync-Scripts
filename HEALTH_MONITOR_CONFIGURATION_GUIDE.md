# Health Monitor Configuration Based on Your SiteSync Project

## Overview
This guide shows how to configure the health monitor script to match your actual SiteSync implementation.

## Configuration Changes Needed

### 1. MQTT Configuration

Your project uses `system.sitesync` MQTT functions with broker IDs and tenant IDs.

**In the health monitor script, verify these settings:**

```python
# MQTT Broker - Basic TCP check (KEEP THIS - IT WORKS!)
BROKER_HOST, BROKER_PORT = "localhost", 1883

# MQTT Transmission Status Tag
# Option A: If you have a Connected status tag, set its path:
MQTT_TX_STATUS_TAG = "[MQTT Transmission]Transmission Info/Connected"

# Option B: If you don't have this tag, set to None to skip:
MQTT_TX_STATUS_TAG = None  # Will use broker reachability instead
```

### 2. SiteSync API Configuration

Your project uses `system.sitesync.testJoinAPIImpl(tenantID)`.

**Current configuration is CORRECT:**
```python
SITESYNC_TENANT_ID = 1  # Change if your tenant ID is different
```

The health check function `_sitesync_api()` already uses:
```python
raw = _system.sitesync.testJoinAPIImpl(SITESYNC_TENANT_ID)
```

**Verify your tenant ID:**
```python
# In Designer Script Console:
js = system.sitesync.getJoinServerSettings(1)
if js:
    settings = json.loads(js)
    print("Tenant 1 Join Server: " + settings.get('serverUrl', 'Not configured'))
else:
    print("Tenant ID 1 not found - check your tenant IDs")
```

### 3. PI Adapter Configuration

Your project uses `system.piAdapter` module.

**Current configuration:**
```python
PI_ADAPTER_BASE = "https://pgwgen002923.mgroupnet.com:5590"
PI_ADAPTER_API_URL = "https://pgwgen002923.mgroupnet.com:5590/api/v1/configuration"
```

**Verify these URLs match your PI Adapter:**
```python
# In Designer Script Console:
import json
settings = system.piAdapter.getSettings("adapter")
if settings and settings != "null":
    s = json.loads(settings)
    print("Adapter URL: " + str(s))
```

### 4. PI Web API Configuration

**Current configuration:**
```python
PI_WEBAPI_BASE = "https://pgwgen002923.mgroupnet.com/piwebapi"
PI_WEBAPI_TOKEN = "Q29nbml0ZVBJRXh0cmFjdF9zdmM6U355TSZQRGpWQDRRUTU="
PI_WEBAPI_AUTH_SCHEME = "Basic"
```

**Verify credentials:**
```python
# In Designer Script Console:
import json
settings = system.piAdapter.getSettings("webAPI")
if settings and settings != "null":
    print("WebAPI configured: Yes")
    # Don't print actual credentials for security
```

### 5. ThingPark Inbound Configuration

**Current configuration:**
```python
DEVICES_ROOT = "[default]SiteSync/Devices"
TIMESTAMP_TAG_SUFFIX = "/LoRaMetrics/MesgTimeStamp"
```

**Verify device tag structure:**
```python
# In Designer Script Console:
results = system.tag.browse("[default]SiteSync/Devices", {"recursive": False})
print("Device folders found: " + str(len(results.getResults())))
for r in results.getResults():
    print("  - " + r['name'])
```

If you don't have devices under this path, you have two options:

**Option A: Update the path to match your structure**
```python
DEVICES_ROOT = "[default]YourActualDevicePath"
```

**Option B: Disable the ThingPark check temporarily**
```python
# In _ensure_base() function, comment out ThingPark_Inbound:
OVERALL_FOLDERS = [
    # "ThingPark_Inbound",  # ← Disabled until devices are configured
    "MQTT_Broker",
    "MQTT_Transmission",
    # ... rest of services
]
```

## Quick Configuration Test Script

Run this to verify all your settings:

```python
"""
Verify Health Monitor Configuration Against Actual SiteSync Setup
"""

import json

print("=" * 80)
print("HEALTH MONITOR CONFIGURATION VERIFICATION")
print("=" * 80)

# Test 1: SiteSync API Module
print("\n1. SiteSync API Module:")
try:
    tenantID = 1
    result = system.sitesync.testJoinAPIImpl(tenantID)
    if result:
        print("   [OK] system.sitesync.testJoinAPIImpl() works")
        print("   Result: " + str(result)[:100])
    else:
        print("   [WARN] No result from API test")
except Exception as e:
    print("   [ERROR] " + str(e))

# Test 2: PI Adapter Module
print("\n2. PI Adapter Settings:")
try:
    adapter_settings = system.piAdapter.getSettings("adapter")
    webapi_settings = system.piAdapter.getSettings("webAPI")

    if adapter_settings and adapter_settings != "null":
        print("   [OK] PI Adapter configured")
    else:
        print("   [WARN] PI Adapter not configured")

    if webapi_settings and webapi_settings != "null":
        print("   [OK] PI Web API configured")
    else:
        print("   [WARN] PI Web API not configured")

except Exception as e:
    print("   [ERROR] " + str(e))

# Test 3: MQTT Status Tag
print("\n3. MQTT Transmission Status Tag:")
mqtt_tag = "[MQTT Transmission]Transmission Info/Connected"
if system.tag.exists(mqtt_tag):
    qv = system.tag.readBlocking([mqtt_tag])[0]
    print("   [OK] Tag exists")
    print("   Value: " + str(qv.value))
    print("   Quality: " + str(qv.quality))
else:
    print("   [WARN] Tag not found: " + mqtt_tag)
    print("   Recommendation: Set MQTT_TX_STATUS_TAG = None in script")

# Test 4: Device Tags
print("\n4. Device Tags Structure:")
devices_root = "[default]SiteSync/Devices"
if system.tag.exists(devices_root):
    results = system.tag.browse(devices_root, {"recursive": False})
    count = len(results.getResults())
    print("   [OK] Devices folder exists")
    print("   Device count: " + str(count))
    if count == 0:
        print("   [WARN] No devices found")
else:
    print("   [ERROR] Devices folder not found: " + devices_root)
    print("   Recommendation: Update DEVICES_ROOT path or disable ThingPark check")

# Test 5: Tenant Settings
print("\n5. Tenant Configuration:")
try:
    for tid in [1, 2, 3]:
        js = system.sitesync.getJoinServerSettings(tid)
        if js and js != "null":
            settings = json.loads(js)
            print("   [OK] Tenant %d: %s" % (tid, settings.get('serverUrl', 'N/A')))
except Exception as e:
    print("   [ERROR] " + str(e))

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
```

## Recommended Configuration Changes

Based on typical SiteSync setups, here are the most common changes needed:

### Change 1: Disable Optional Services

If you don't use GeoEvent or Azure Functions:

```python
# Set URLs to empty string to skip
GEOEVENT_HEALTH_URL = ""
AZURE_HEALTH_URL = ""
```

### Change 2: Set MQTT Transmission Tag

If the specific transmission tag doesn't exist:

```python
# Option A: Use None to skip dedicated transmission check
MQTT_TX_STATUS_TAG = None

# Option B: Set correct path if tag exists elsewhere
MQTT_TX_STATUS_TAG = "[default]MQTT/Broker/Connected"
```

### Change 3: Adjust Device Scan Interval

If you have many devices, increase scan interval:

```python
TP_SCAN_MIN_MS = 60 * 1000  # Check devices max once per minute
```

## Next Steps

1. Run the configuration verification script above
2. Update the health monitor script based on results
3. Save and let timer script run
4. Check if all services now update properly
5. Monitor Gateway logs for any remaining errors

---

**Note**: Your SiteSync implementation uses proper API modules (`system.sitesync`, `system.piAdapter`), which means the health monitor should work correctly once configuration paths are verified!
