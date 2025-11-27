"""
Ignition Designer Script Console Test Script
For Health Monitor Tag Structure Validation

Run this script in the Ignition Designer Script Console to:
1. Verify all required tags exist
2. Check tag data types
3. Validate alarm configurations
4. Test read/write operations
5. Display health monitor status

Instructions:
1. Open Ignition Designer
2. Go to Tools > Script Console
3. Copy and paste this entire script
4. Click "Run Script" button
5. Review output in console
"""

# =============================================================================
# CONFIGURATION
# =============================================================================
HEALTH_BASE = "[default]Health"
EXPECTED_SERVICES = [
    "ThingPark_Inbound",
    "MQTT_Broker",
    "MQTT_Transmission",
    "SiteSync_API",
    "PI_Adapter",
    "PI_Adapter_API",
    "PI_WebAPI",
    "GeoEvent",
    "Azure_Function",
    "Actility_API",
    "PI_Adapter_Link",
    "SiteSync_UI",
    "SiteSync_UI_External",
    "LDAP_Green",
    "Azure_EventHub_Dev",
    "Azure_EventHub_Prod"
]

EXPECTED_BASE_TAGS = [
    ("ENABLE_UNIFIED_MONITOR", "Boolean"),
    ("Overall_Healthy", "Boolean"),
    ("Fault_Summary", "String"),
    ("Last_Fault", "String"),
    ("Last_Fault_At", "DateTime"),
    ("_PipelinesAttached", "Boolean")
]

EXPECTED_SERVICE_TAGS = [
    ("IsHealthy", "Boolean"),
    ("Status", "String"),
    ("Message", "String"),
    ("LatencyMs", "Int4"),
    ("LastCheck", "DateTime"),
    ("LastOK", "DateTime")
]

# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)

def print_success(text):
    """Print success message"""
    print("[OK] " + text)

def print_error(text):
    """Print error message"""
    print("[ERROR] " + text)

def print_warning(text):
    """Print warning message"""
    print("[WARN] " + text)

def print_info(text):
    """Print info message"""
    print("[INFO] " + text)

def tag_exists(path):
    """Check if tag exists"""
    try:
        return system.tag.exists(path)
    except:
        return False

def get_tag_datatype(path):
    """Get tag data type"""
    try:
        cfg = system.tag.getConfiguration(path, False)
        if cfg and len(cfg) > 0:
            return str(cfg[0].get("dataType", "Unknown"))
        return "Unknown"
    except Exception as e:
        return "Error: " + str(e)

def get_tag_value(path):
    """Get tag value safely"""
    try:
        qv = system.tag.readBlocking([path])[0]
        if qv.quality.isGood():
            return qv.value
        else:
            return "BAD QUALITY: " + str(qv.quality)
    except Exception as e:
        return "Error: " + str(e)

def check_alarm_config(path, alarm_name="ConnDown"):
    """Check if tag has alarm configured"""
    try:
        cfg = system.tag.getConfiguration(path, True)
        if cfg and len(cfg) > 0:
            alarms = cfg[0].get("alarms", [])
            for alarm in alarms:
                if alarm.get("name") == alarm_name:
                    return True, alarm
            return False, None
        return False, None
    except Exception as e:
        return False, "Error: " + str(e)

# =============================================================================
# MAIN TEST EXECUTION
# =============================================================================

print_header("HEALTH MONITOR TAG STRUCTURE VALIDATION TEST")
print("Start Time: " + str(system.date.now()))
print("Testing Base Path: " + HEALTH_BASE)

# Test 1: Check if base Health folder exists
print_header("TEST 1: Base Folder Existence")
if tag_exists(HEALTH_BASE):
    print_success("Health base folder exists at: " + HEALTH_BASE)
else:
    print_error("Health base folder NOT FOUND at: " + HEALTH_BASE)
    print_info("Please import the Health_Tags_Template.json file first")

# Test 2: Check base-level tags
print_header("TEST 2: Base-Level Tags")
for tag_name, expected_type in EXPECTED_BASE_TAGS:
    tag_path = HEALTH_BASE + "/" + tag_name
    if tag_exists(tag_path):
        actual_type = get_tag_datatype(tag_path)
        if actual_type == expected_type:
            value = get_tag_value(tag_path)
            print_success("%s exists with correct type (%s), value: %s" % (tag_name, expected_type, str(value)))
        else:
            print_error("%s exists but wrong type (expected: %s, got: %s)" % (tag_name, expected_type, actual_type))
    else:
        print_error("%s NOT FOUND" % tag_name)

# Test 3: Check service folders and their tags
print_header("TEST 3: Service Folders and Tags")
missing_services = []
incomplete_services = []

for service in EXPECTED_SERVICES:
    service_path = HEALTH_BASE + "/" + service

    if not tag_exists(service_path):
        print_error("Service folder NOT FOUND: " + service)
        missing_services.append(service)
        continue

    print_info("Checking service: " + service)
    missing_tags = []

    for tag_name, expected_type in EXPECTED_SERVICE_TAGS:
        tag_path = service_path + "/" + tag_name

        if tag_exists(tag_path):
            actual_type = get_tag_datatype(tag_path)
            if actual_type == expected_type:
                print_success("  %s/%s - OK (%s)" % (service, tag_name, expected_type))
            else:
                print_error("  %s/%s - Wrong type (expected: %s, got: %s)" % (service, tag_name, expected_type, actual_type))
                missing_tags.append(tag_name)
        else:
            print_error("  %s/%s - NOT FOUND" % (service, tag_name))
            missing_tags.append(tag_name)

    # Check for service-specific tags
    if service == "ThingPark_Inbound":
        extra_tag = service_path + "/LastInboundMs"
        if tag_exists(extra_tag):
            print_success("  %s/LastInboundMs - OK (extra tag)" % service)
        else:
            print_warning("  %s/LastInboundMs - NOT FOUND (extra tag)" % service)

    if service == "MQTT_Broker":
        extra_tag = service_path + "/Clients"
        if tag_exists(extra_tag):
            print_success("  %s/Clients - OK (extra tag)" % service)
        else:
            print_warning("  %s/Clients - NOT FOUND (extra tag)" % service)

    if missing_tags:
        incomplete_services.append(service)

# Test 4: Check alarm configurations
print_header("TEST 4: Alarm Configurations")
alarm_check_count = 0
alarm_ok_count = 0

for service in EXPECTED_SERVICES:
    service_path = HEALTH_BASE + "/" + service
    isHealthy_path = service_path + "/IsHealthy"

    if tag_exists(isHealthy_path):
        has_alarm, alarm_cfg = check_alarm_config(isHealthy_path, "ConnDown")
        if has_alarm:
            print_success("%s/IsHealthy has ConnDown alarm configured" % service)
            alarm_ok_count += 1
        else:
            print_warning("%s/IsHealthy missing ConnDown alarm" % service)
        alarm_check_count += 1

# Test 5: Read current health status
print_header("TEST 5: Current Health Monitor Status")

# Read enable flag
enable_path = HEALTH_BASE + "/ENABLE_UNIFIED_MONITOR"
if tag_exists(enable_path):
    enabled = get_tag_value(enable_path)
    if enabled == True:
        print_success("Health Monitor is ENABLED")
    else:
        print_warning("Health Monitor is DISABLED")

# Read overall health
overall_path = HEALTH_BASE + "/Overall_Healthy"
if tag_exists(overall_path):
    overall_healthy = get_tag_value(overall_path)
    if overall_healthy == True:
        print_success("Overall System Health: HEALTHY")
    else:
        print_error("Overall System Health: UNHEALTHY")

# Read fault summary
fault_path = HEALTH_BASE + "/Fault_Summary"
if tag_exists(fault_path):
    fault_summary = get_tag_value(fault_path)
    if fault_summary and fault_summary != "All healthy" and fault_summary != "Initializing...":
        print_error("Fault Summary: " + str(fault_summary))
    else:
        print_info("Fault Summary: " + str(fault_summary))

# Display service health summary
print_header("TEST 6: Service Health Summary")
healthy_count = 0
unhealthy_count = 0
unknown_count = 0

for service in EXPECTED_SERVICES:
    service_path = HEALTH_BASE + "/" + service
    isHealthy_path = service_path + "/IsHealthy"
    status_path = service_path + "/Status"
    message_path = service_path + "/Message"
    lastcheck_path = service_path + "/LastCheck"

    if tag_exists(isHealthy_path):
        is_healthy = get_tag_value(isHealthy_path)
        status = get_tag_value(status_path) if tag_exists(status_path) else "N/A"
        message = get_tag_value(message_path) if tag_exists(message_path) else ""
        last_check = get_tag_value(lastcheck_path) if tag_exists(lastcheck_path) else "Never"

        if is_healthy == True:
            print_success("%s: HEALTHY [%s]" % (service.ljust(25), status))
            healthy_count += 1
        elif is_healthy == False:
            print_error("%s: UNHEALTHY [%s] - %s" % (service.ljust(25), status, str(message)[:50]))
            unhealthy_count += 1
        else:
            print_warning("%s: UNKNOWN" % service.ljust(25))
            unknown_count += 1
    else:
        print_warning("%s: TAG NOT FOUND" % service.ljust(25))
        unknown_count += 1

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print_header("TEST SUMMARY")

total_services = len(EXPECTED_SERVICES)
print("Total Services Expected: %d" % total_services)
print("  Healthy:   %d" % healthy_count)
print("  Unhealthy: %d" % unhealthy_count)
print("  Unknown:   %d" % unknown_count)
print("")

if missing_services:
    print_error("Missing Service Folders (%d): %s" % (len(missing_services), ", ".join(missing_services)))
else:
    print_success("All service folders found")

if incomplete_services:
    print_warning("Incomplete Services (%d): %s" % (len(incomplete_services), ", ".join(incomplete_services)))
else:
    print_success("All services have required tags")

print("")
print("Alarms Configured: %d/%d" % (alarm_ok_count, alarm_check_count))

print_header("RECOMMENDATIONS")

if missing_services or incomplete_services:
    print("1. Import Health_Tags_Template.json to create missing tags")
    print("2. Configure alarm pipeline 'ConnAlarm' if not already done")
    print("3. Enable the health monitor timer script")
else:
    print_success("Tag structure looks good!")
    print("1. Verify alarm pipeline 'ConnAlarm' is configured")
    print("2. Verify timer script is running (check ScriptHeartbeat updates)")
    print("3. Configure service endpoints in unified health monitor script")

print_header("TEST COMPLETE")
print("End Time: " + str(system.date.now()))
print("")
