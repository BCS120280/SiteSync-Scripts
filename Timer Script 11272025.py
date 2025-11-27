# SiteSync_Health_Timer - Complete health monitoring
# Gateway script version - system module provided by Ignition

from __future__ import print_function
from java.lang import String
from java.net import Socket
from java.io import IOException

# =============================================================================
# CAPTURE SYSTEM REFERENCE - Will be initialized in main block
# This allows functions to access the Ignition 'system' object
# =============================================================================
_system = None

# =============================================================================
# CONFIGURATION
# =============================================================================
PROVIDER = "default"
BASE = "[%s]Health" % PROVIDER
CONFIG_BASE = "[%s]Config/Health" % PROVIDER
SERVICES = ["MQTT_Broker","MQTT_Transmission","SiteSync_API","PI_WebAPI","PI_Adapter",
            "ThingPark_Inbound","Azure_Function","GeoEvent","Actility_API"]

# =============================================================================
# UTILITY FUNCTIONS - Must be defined before use
# =============================================================================

def safe_str(x, n=400):
    """Safe string conversion"""
    try: 
        s = str(x)
    except:
        try: 
            s = String.valueOf(x)
        except: 
            s = "<?>"
    return s if len(s)<=n else s[:n-3]+"..."


def ensure_folder(path):
    """Recursively create folder structure if it doesn't exist"""
    if _system.tag.exists(path): 
        return
    i = path.find("]")
    prov = path[1:i]
    rem = path[i+1:].strip("/")
    parent = "[%s]" % prov
    for seg in (rem.split("/") if rem else []):
        cur = parent + (seg if parent.endswith("]") else "/" + seg)
        if not _system.tag.exists(cur):
            _system.tag.configure(parent, [{"name":seg,"tagType":"Folder"}], "m")
        parent = cur


def ensure_mem_tag(parent, name, dtype, default=None):
    """Create memory tag if it doesn't exist"""
    ensure_folder(parent)
    full = parent + "/" + name
    if _system.tag.exists(full):
        return
    td = {"name":name,"tagType":"AtomicTag","valueSource":"memory","dataType":dtype}
    if default is not None:
        td["value"] = default
    _system.tag.configure(parent, [td], "m")


def read_config(service, param, default=None):
    """Read configuration parameter for a service"""
    try:
        path = "%s/%s/%s" % (CONFIG_BASE, service, param)
        if _system.tag.exists(path):
            qv = _system.tag.readBlocking([path])[0]
            return qv.value if qv.quality.isGood() else default
        return default
    except:
        return default


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

def check_mqtt_broker():
    """Check MQTT broker connectivity via TCP socket"""
    host = read_config("MQTT_Broker", "Host", "localhost")
    port = read_config("MQTT_Broker", "Port", 1883)
    timeout_ms = read_config("MQTT_Broker", "TimeoutMs", 3000)
    
    start = _system.date.now()
    try:
        sock = Socket()
        sock.connect(java.net.InetSocketAddress(host, int(port)), int(timeout_ms))
        sock.close()
        latency = _system.date.secondsBetween(start, _system.date.now()) * 1000
        return True, int(latency), "Connected to %s:%s" % (host, port), "OK"
    except IOException as e:
        latency = _system.date.secondsBetween(start, _system.date.now()) * 1000
        return False, int(latency), "Failed: %s" % safe_str(e, 100), "ERROR"
    except Exception as e:
        return False, 0, "Exception: %s" % safe_str(e, 100), "ERROR"


def check_mqtt_transmission():
    """Check MQTT transmission by reading Connected tag"""
    connected_path = read_config("MQTT_Transmission", "ConnectedTagPath", 
                                  "[default]MQTT/Connected")
    stale_threshold_ms = read_config("MQTT_Transmission", "StaleThresholdMs", 300000)
    
    try:
        qv = _system.tag.readBlocking([connected_path])[0]
        if not qv.quality.isGood():
            return False, 0, "Tag quality bad: %s" % qv.quality, "ERROR"
        
        is_connected = bool(qv.value)
        timestamp = qv.timestamp
        age_ms = _system.date.secondsBetween(timestamp, _system.date.now()) * 1000
        
        if not is_connected:
            return False, int(age_ms), "MQTT disconnected", "DISCONNECTED"
        elif age_ms > stale_threshold_ms:
            return False, int(age_ms), "Data stale (%d ms)" % int(age_ms), "STALE"
        else:
            return True, int(age_ms), "Connected, fresh data", "OK"
    except Exception as e:
        return False, 0, "Exception: %s" % safe_str(e, 100), "ERROR"


def check_http_service(service_name, default_url):
    """Generic HTTP/HTTPS health check"""
    url = read_config(service_name, "HealthURL", default_url)
    timeout_ms = read_config(service_name, "TimeoutMs", 5000)
    bypass_ssl = read_config(service_name, "BypassSSL", True)
    auth_type = read_config(service_name, "AuthType", "None")
    
    if not url or url == "":
        return False, 0, "No URL configured", "NOT_CONFIGURED"
    
    start = _system.date.now()
    try:
        username = None
        password = None
        header_values = {}
        
        if auth_type == "Basic":
            username = read_config(service_name, "Username", "")
            password = read_config(service_name, "Password", "")
        elif auth_type == "Bearer":
            token = read_config(service_name, "BearerToken", "")
            if token:
                header_values["Authorization"] = "Bearer %s" % token
        
        response = _system.net.httpClient(
            url=url,
            timeout=int(timeout_ms),
            username=username,
            password=password,
            headerValues=header_values,
            bypassCertValidation=bypass_ssl
        )
        
        latency = _system.date.secondsBetween(start, _system.date.now()) * 1000
        
        if response.statusCode >= 200 and response.statusCode < 300:
            return True, int(latency), "HTTP %d" % response.statusCode, "OK"
        else:
            return False, int(latency), "HTTP %d" % response.statusCode, "HTTP_ERROR"
            
    except Exception as e:
        latency = _system.date.secondsBetween(start, _system.date.now()) * 1000
        if url.startswith("https://"):
            try:
                http_url = url.replace("https://", "http://")
                response = _system.net.httpClient(
                    url=http_url,
                    timeout=int(timeout_ms),
                    username=username,
                    password=password,
                    headerValues=header_values
                )
                latency = _system.date.secondsBetween(start, _system.date.now()) * 1000
                if response.statusCode >= 200 and response.statusCode < 300:
                    return True, int(latency), "HTTP %d (fallback)" % response.statusCode, "OK"
            except:
                pass
        
        return False, int(latency), "Failed: %s" % safe_str(e, 100), "ERROR"


def check_thingpark_inbound():
    """Check ThingPark device data freshness"""
    devices_root = read_config("ThingPark_Inbound", "DevicesRoot", "[default]Devices")
    timestamp_suffix = read_config("ThingPark_Inbound", "TimestampSuffix", "Timestamp")
    stale_threshold_ms = read_config("ThingPark_Inbound", "StaleThresholdMs", 3600000)
    scan_min_interval_ms = read_config("ThingPark_Inbound", "ScanMinMs", 60000)
    
    last_scan_path = BASE + "/ThingPark_Inbound/LastScanMs"
    ensure_mem_tag(BASE + "/ThingPark_Inbound", "LastScanMs", "Int8", 0)
    
    try:
        last_scan_ms = _system.tag.readBlocking([last_scan_path])[0].value
        now_ms = _system.date.toMillis(_system.date.now())
        
        if (now_ms - last_scan_ms) < scan_min_interval_ms:
            cached_healthy = _system.tag.readBlocking([BASE + "/ThingPark_Inbound/IsHealthy"])[0].value
            cached_latency = _system.tag.readBlocking([BASE + "/ThingPark_Inbound/LatencyMs"])[0].value
            cached_msg = _system.tag.readBlocking([BASE + "/ThingPark_Inbound/Message"])[0].value
            cached_status = _system.tag.readBlocking([BASE + "/ThingPark_Inbound/Status"])[0].value
            return cached_healthy, cached_latency, cached_msg, cached_status
        
        start = _system.date.now()
        browse_results = _system.tag.browse(devices_root, {"recursive": True, "tagType": "AtomicTag"})
        results = browse_results.getResults()

        timestamp_tags = []
        for result in results:
            if result['name'].endswith(timestamp_suffix):
                timestamp_tags.append(result['fullPath'])
        
        if len(timestamp_tags) == 0:
            return False, 0, "No timestamp tags found", "NO_DATA"
        
        qvs = _system.tag.readBlocking(timestamp_tags)
        now = _system.date.now()
        min_age_ms = None
        stale_count = 0
        
        for qv in qvs:
            if qv.quality.isGood() and qv.value is not None:
                age_ms = _system.date.secondsBetween(qv.value, now) * 1000
                if min_age_ms is None or age_ms < min_age_ms:
                    min_age_ms = age_ms
                if age_ms > stale_threshold_ms:
                    stale_count += 1
        
        latency = _system.date.secondsBetween(start, _system.date.now()) * 1000
        _system.tag.writeBlocking([last_scan_path], [now_ms])
        
        if min_age_ms is None:
            return False, int(latency), "No valid timestamps", "NO_DATA"
        elif stale_count > 0:
            return False, int(min_age_ms), "%d/%d devices stale" % (stale_count, len(timestamp_tags)), "STALE"
        else:
            return True, int(min_age_ms), "All devices fresh (%d checked)" % len(timestamp_tags), "OK"
            
    except Exception as e:
        return False, 0, "Exception: %s" % safe_str(e, 100), "ERROR"


# =============================================================================
# MAIN EXECUTION STARTS HERE
# =============================================================================

try:
    # Initialize system reference - must be first in try block
    global _system
    _system = system

    log = _system.util.getLogger("SiteSync.HealthTimer")
    g = _system.util.getGlobals()

    # Check for re-entrance
    if g.get("_SS_HEALTH_RUNNING", False):
        log.warn("Previous cycle still running; skipping.")
    else:
        # Mark as running
        g["_SS_HEALTH_RUNNING"] = True

        try:
            # Ensure base structure exists
            ensure_folder(BASE)
            ensure_folder(CONFIG_BASE)
            ensure_mem_tag(BASE, "ScriptHeartbeat", "DateTime")
            ensure_mem_tag(BASE, "AlarmDisplayText", "String", "Healthy")

            now = _system.date.now()
            _system.tag.writeBlocking([BASE + "/ScriptHeartbeat"], [now])

            # Process each service
            for service in SERVICES:
                service_path = BASE + "/" + service

                # Ensure all required tags exist
                ensure_mem_tag(service_path, "LastCheck", "DateTime")
                ensure_mem_tag(service_path, "LastOK", "DateTime")
                ensure_mem_tag(service_path, "LatencyMs", "Int4", 0)
                ensure_mem_tag(service_path, "Message", "String", "Initializing...")
                ensure_mem_tag(service_path, "Status", "String", "INIT")
                ensure_mem_tag(service_path, "IsHealthy", "Boolean", True)

                # Perform health check
                try:
                    if service == "MQTT_Broker":
                        is_healthy, latency, message, status = check_mqtt_broker()
                    elif service == "MQTT_Transmission":
                        is_healthy, latency, message, status = check_mqtt_transmission()
                    elif service == "SiteSync_API":
                        is_healthy, latency, message, status = check_http_service(service, "https://localhost:8088/")
                    elif service == "PI_WebAPI":
                        is_healthy, latency, message, status = check_http_service(service, "https://pi-server/piwebapi/")
                    elif service == "PI_Adapter":
                        is_healthy, latency, message, status = check_http_service(service, "https://localhost:5460/")
                    elif service == "ThingPark_Inbound":
                        is_healthy, latency, message, status = check_thingpark_inbound()
                    elif service == "Azure_Function":
                        is_healthy, latency, message, status = check_http_service(service, "")
                    elif service == "GeoEvent":
                        is_healthy, latency, message, status = check_http_service(service, "")
                    elif service == "Actility_API":
                        is_healthy, latency, message, status = check_http_service(service, "")
                    else:
                        is_healthy, latency, message, status = False, 0, "Unknown service", "UNKNOWN"

                    # Build write paths and values
                    paths = [
                        service_path + "/LastCheck",
                        service_path + "/LatencyMs",
                        service_path + "/Message",
                        service_path + "/Status",
                        service_path + "/IsHealthy"
                    ]

                    values = [now, int(latency), message, status, is_healthy]

                    # Add LastOK if healthy
                    if is_healthy:
                        paths.append(service_path + "/LastOK")
                        values.append(now)

                    # Write all tags
                    _system.tag.writeBlocking(paths, values)
                    log.debug("%s: %s - %s" % (service, "HEALTHY" if is_healthy else "UNHEALTHY", message))

                except Exception as e:
                    error_msg = "Check failed: %s" % safe_str(e, 150)
                    log.error("%s: %s" % (service, error_msg))
                    _system.tag.writeBlocking(
                        [service_path + "/LastCheck", service_path + "/Message",
                         service_path + "/Status", service_path + "/IsHealthy"],
                        [now, error_msg, "EXCEPTION", False]
                    )

            # Update overall alarm display text
            try:
                rows = _system.alarm.queryStatus(sourcePath=BASE + "/Overall_Healthy*")
                if rows and len(rows) > 0 and hasattr(rows[0], "displayPath"):
                    txt = rows[0].displayPath
                elif rows == []:
                    txt = "Healthy"
                else:
                    txt = "Overall Health"
                _system.tag.writeBlocking([BASE + "/AlarmDisplayText"], [txt])
            except Exception as e:
                log.warn("AlarmDisplayText update: " + safe_str(e))

            # Update debug counter if exists
            debug_counter_path = BASE + "/Debug/TimerCounter"
            if _system.tag.exists(debug_counter_path):
                try:
                    current = _system.tag.readBlocking([debug_counter_path])[0].value
                    _system.tag.writeBlocking([debug_counter_path], [current + 1])
                except:
                    pass

            log.info("Health check cycle completed successfully")

        except Exception as e:
            log.error("Top-level failure: " + safe_str(e))

        finally:
            # Always clear the running flag
            g["_SS_HEALTH_RUNNING"] = False

except Exception as e:
    # Handle case where _system is not available at module initialization
    pass