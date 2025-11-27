# Health Monitor Setup and Testing Guide

## Overview
This guide helps you set up and test the SiteSync Health Monitor system in Ignition.

## Files in This Repository

1. **unifiedconnectionhealthmonitor script** - Main health monitoring script (Gateway Timer)
2. **Timer Script 11272025.py** - Alternative health monitoring script
3. **Health_Tags_Template.json** - Tag structure export for Ignition
4. **Health_Monitor_Test_Script.py** - Validation test script for Designer Script Console

## Setup Instructions

### Step 1: Import Tags into Ignition

1. Open Ignition Designer
2. Navigate to Tag Browser
3. Right-click on `[default]` provider
4. Select **Tags > Import Tags...**
5. Choose `Health_Tags_Template.json`
6. Select import mode: **Merge** (recommended) or **Overwrite**
7. Click **Import**

### Step 2: Configure Gateway Timer Script

1. Open Ignition Designer
2. Go to **Gateway Event Scripts** (Project > Scripts)
3. Create a new **Gateway Timer Script** or use existing
4. Set execution rate: **60000 ms** (1 minute recommended)
5. Copy contents of `unifiedconnectionhealthmonitor script` into the script editor
6. **IMPORTANT**: Review and update configuration section (lines 30-94):
   - Update IP addresses
   - Update credentials (PI_WEBAPI_TOKEN)
   - Configure service URLs
   - Set provider name if not using `[default]`

### Step 3: Configure Alarm Pipeline

1. In Ignition Designer, go to **Alarms > Notification**
2. Create a new alarm pipeline named: **ConnAlarm**
3. Configure notification settings:
   - Email notifications
   - SMS notifications
   - Database logging
   - Custom scripts
4. Save the pipeline

### Step 4: Run Validation Test

1. Open Ignition Designer
2. Go to **Tools > Script Console**
3. Open `Health_Monitor_Test_Script.py`
4. Copy entire contents
5. Paste into Script Console
6. Click **Run Script**
7. Review output for errors

## Tag Structure

### Base Tags (under `[default]Health/`)

| Tag Name | Data Type | Purpose |
|----------|-----------|---------|
| ENABLE_UNIFIED_MONITOR | Boolean | Enable/disable the monitor |
| Overall_Healthy | Boolean | Overall system health status |
| Fault_Summary | String | Summary of all faults |
| Last_Fault | String | Most recent fault |
| Last_Fault_At | DateTime | Timestamp of last fault |
| _PipelinesAttached | Boolean | Internal flag for pipeline config |

### Service Folders

Each service has a folder with these tags:

| Tag Name | Data Type | Purpose |
|----------|-----------|---------|
| IsHealthy | Boolean | Service health status (has alarm) |
| Status | String | Status code (OK, ERROR, etc.) |
| Message | String | Detailed status message |
| LatencyMs | Int4 | Response time in milliseconds |
| LastCheck | DateTime | Last health check time |
| LastOK | DateTime | Last successful check time |

### Monitored Services

1. **ThingPark_Inbound** - LoRaWAN device data freshness
   - Extra tag: `LastInboundMs` (Int8)
2. **MQTT_Broker** - MQTT broker connectivity
   - Extra tag: `Clients` (Int4)
3. **MQTT_Transmission** - MQTT transmission status
4. **SiteSync_API** - SiteSync API health
5. **PI_Adapter** - PI Adapter status endpoint
6. **PI_Adapter_API** - PI Adapter API configuration
7. **PI_WebAPI** - PI Web API connectivity
8. **GeoEvent** - GeoEvent service (optional)
9. **Azure_Function** - Azure Function (optional)
10. **Actility_API** - Actility cloud connectivity
11. **PI_Adapter_Link** - DMZ MQTT listener
12. **SiteSync_UI** - Internal UI accessibility
13. **SiteSync_UI_External** - External UI accessibility
14. **LDAP_Green** - Green DC LDAP connectivity
15. **Azure_EventHub_Dev** - Azure Event Hub (Dev)
16. **Azure_EventHub_Prod** - Azure Event Hub (Prod)

## Troubleshooting

### Script Not Running

**Error**: "global name 'system' is not defined"
- **Solution**: Make sure you're using the FIXED version of the script from this repository
- The script should have `_system = system` at line 14

**Error**: Tags not updating
- Check that timer script is enabled
- Verify `ENABLE_UNIFIED_MONITOR` tag is `true`
- Check Gateway > Status > Scripting for errors

### Tag Issues

**Missing Tags**
1. Re-import `Health_Tags_Template.json`
2. Use merge mode to avoid overwriting existing values
3. Run test script to identify specific missing tags

**Alarm Not Triggering**
1. Verify alarm pipeline "ConnAlarm" exists
2. Check alarm is enabled on `IsHealthy` tags
3. Review alarm configuration on individual tags
4. Check Gateway > Status > Alarm Notification

### Service-Specific Issues

**ThingPark_Inbound Always Unhealthy**
- Verify `DEVICES_ROOT` path is correct (default: `[default]SiteSync/Devices`)
- Check that device tags have timestamp suffix (default: `/LoRaMetrics/MesgTimeStamp`)
- Adjust `TP_STALE_MS` threshold if needed (default: 5 minutes)

**PI WebAPI Connection Failed**
- Update `PI_WEBAPI_BASE` URL
- Update `PI_WEBAPI_TOKEN` with correct Base64 credentials
- Set `PI_WEBAPI_INSECURE_OK = True` if using self-signed certificates

**MQTT Broker Unreachable**
- Verify `BROKER_HOST` and `BROKER_PORT`
- Check network connectivity from Ignition server
- Verify MQTT broker is running

## Testing the Monitor

### Manual Test via Script Console

```python
# Read current health status
health_path = "[default]Health"
qv = system.tag.readBlocking([
    health_path + "/Overall_Healthy",
    health_path + "/Fault_Summary"
])

print("Overall Healthy: " + str(qv[0].value))
print("Fault Summary: " + str(qv[1].value))

# Check individual services
services = ["MQTT_Broker", "SiteSync_API", "PI_WebAPI"]
for svc in services:
    path = health_path + "/" + svc + "/IsHealthy"
    val = system.tag.readBlocking([path])[0].value
    print("%s: %s" % (svc, "HEALTHY" if val else "UNHEALTHY"))
```

### Monitor Timer Execution

Check `ScriptHeartbeat` tag updates:
```python
heartbeat_path = "[default]Health/ScriptHeartbeat"
qv = system.tag.readBlocking([heartbeat_path])[0]
print("Last heartbeat: " + str(qv.value))
print("Quality: " + str(qv.quality))
```

### View Active Alarms

```python
alarms = system.alarm.queryStatus(
    priority=["High"],
    state=["ActiveUnacked", "ActiveAcked"]
)
for alarm in alarms:
    print("ALARM: " + alarm.displayPath + " - " + alarm.label)
```

## Configuration Tips

### Adjust Check Intervals

Edit script constants:
- `TP_STALE_MS` - ThingPark data freshness (default: 5 min)
- `TP_SCAN_MIN_MS` - Minimum rescan interval (default: 30 sec)
- Timer script execution rate - Overall check frequency

### Disable Optional Services

If you don't use certain services, you can:

1. Set URL to empty string:
```python
GEOEVENT_HEALTH_URL = ""  # Service will be skipped
AZURE_HEALTH_URL = ""     # Service will be skipped
```

2. Or remove from `OVERALL_FOLDERS` list to exclude from rollup

### Custom Alarm Priorities

Edit alarm configuration in `_ensure_base()` function:
```python
alarms = [{
    "name": "ConnDown",
    "enabled": True,
    "priority": "Critical",  # Change from "High"
    "alarmMode": "Equal",
    "setpointA": False,
    "activePipeline": PIPELINE_NAME
}]
```

## Support

For issues or questions:
1. Review Ignition Gateway logs
2. Run the test script to identify configuration issues
3. Check this guide for troubleshooting steps
4. Verify all configuration constants match your environment

## Version History

- **2025-11-27**: Initial release with fixed 'system' reference error
  - Added `_system = system` capture for gateway timer context
  - Created comprehensive tag structure template
  - Added validation test script
