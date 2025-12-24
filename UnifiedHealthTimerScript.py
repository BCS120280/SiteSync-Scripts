# ==================================================================================================
# UnifiedHealthCheck - Ignition 8.1.x Gateway Timer Script
# - Fixes ACT_IDX_KEY NameError
# - TLS bypass is configurable (optional tags): SiteSyncBypassSSL, PIAdapterBypassSSL, ExtraURLBypassSSL
# - Fast ThingPark scan: NON-recursive browse + cached folders + throttling
# ==================================================================================================

def _entrypoint():
    import system
    import socket
    import traceback

    log = system.util.getLogger("UnifiedHealthCheck")
    g = system.util.getGlobals()

    HEALTH_ROOT = "[default]Health"
    CFG_ROOT    = HEALTH_ROOT + "/Config"
    DBG_ROOT    = HEALTH_ROOT + "/Debug"

    ENABLE_TAG        = HEALTH_ROOT + "/ENABLE_UNIFIED_MONITOR"
    ALARM_TEXT_TAG    = HEALTH_ROOT + "/AlarmDisplayText"
    HEARTBEAT_TAG     = HEALTH_ROOT + "/ScriptHeartbeat"
    TIMER_COUNTER_TAG = DBG_ROOT + "/TimerCounter"
    LAST_RUN_MS_TAG   = DBG_ROOT + "/LastRunMs"
    LAST_RUN_AT_TAG   = DBG_ROOT + "/LastRunAt"
    LAST_ERROR_TAG    = DBG_ROOT + "/LastError"

    OVERALL_SERVICES = [
        "SiteSync_API",
        "MQTT_Broker",
        "Azure_Function",
        "PI_Adapter",
        "Actility_API",
        "GeoEvent",
        "ThingPark_Inbound",
        "PI_WebAPI",
        "MQTT_Transmission",
    ]

    # Guard / budgets
    RUNNING_KEY = "UnifiedHealthCheck.running"
    RUNNING_SINCE_KEY = "UnifiedHealthCheck.runningSinceMs"
    GUARD_STALE_MS = 5 * 60 * 1000
    RUN_BUDGET_MS = 20 * 1000

    # ThingPark scan cache
    TP_CACHE_KEY = "UnifiedHealthCheck.tp.cache"  # dict: root, suffix, folders, refreshedMs
    TP_LAST_SCAN_KEY = "UnifiedHealthCheck.tp.lastScanMs"
    TP_LAST_AGE_KEY  = "UnifiedHealthCheck.tp.lastAgeMs"
    TP_FOLDER_REFRESH_MS = 10 * 60 * 1000
    TP_MAX_TS_READ = 5000
    TP_READ_CHUNK  = 500

    # ✅ FIX: Actility rotation key
    ACT_IDX_KEY = "UnifiedHealthCheck.act.idx"

    def now_dt():
        return system.date.now()

    def now_ms():
        return long(system.date.toMillis(now_dt()))

    def safe_str(x, default=""):
        try:
            if x is None:
                return default
            return str(x)
        except:
            return default

    def qv_value(qv, default=None):
        try:
            if qv is None:
                return default
            try:
                if qv.quality is not None and (not qv.quality.isGood()):
                    return default
            except:
                pass
            return qv.value
        except:
            return default

    def tag_exists(path):
        try:
            return bool(system.tag.exists(path))
        except:
            return False

    def read_tag(path, default=None):
        try:
            qv = system.tag.readBlocking([path])[0]
            v = qv_value(qv, default)
            return default if v is None else v
        except:
            return default

    def write_tags(paths, values):
        try:
            system.tag.writeBlocking(paths, values)
        except Exception as ex:
            try:
                log.warn("writeBlocking failed: %s" % safe_str(ex))
            except:
                pass

    def set_service(service, ok, status, msg, latency_ms=-1, last_inbound_ms=None, w_paths=None, w_vals=None):
        base = HEALTH_ROOT + "/" + service
        t = now_dt()
        if w_paths is None:
            w_paths = []
            w_vals = []

        w_paths.extend([
            base + "/IsHealthy",
            base + "/Status",
            base + "/Message",
            base + "/LatencyMs",
            base + "/LastCheck",
        ])
        w_vals.extend([
            bool(ok),
            safe_str(status),
            safe_str(msg)[:4000],
            int(latency_ms) if latency_ms is not None else -1,
            t,
        ])

        if ok:
            w_paths.append(base + "/LastOK")
            w_vals.append(t)

        if last_inbound_ms is not None:
            w_paths.append(base + "/LastInboundMs")
            w_vals.append(int(last_inbound_ms))

        return w_paths, w_vals

    def tcp_connect(host, port, timeout_ms):
        start = now_ms()
        try:
            h = safe_str(host).strip()
            p = int(port)
            if not h or p <= 0:
                return False, 0, "MISCONFIG (host/port)"

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.settimeout(max(0.2, float(timeout_ms) / 1000.0))
                s.connect((h, p))
            finally:
                try: s.close()
                except: pass

            return True, max(0, now_ms() - start), "TCP OK"
        except Exception as ex:
            return False, max(0, now_ms() - start), "TCP FAIL: %s" % safe_str(ex)

    def http_reach(url, timeout_ms, bypass_cert=True, headers=None, username=None, password=None):
        start = now_ms()
        try:
            u = safe_str(url).strip()
            if not u:
                return False, 0, "MISCONFIG (url)"

            system.net.httpGet(
                url=u,
                connectTimeout=int(timeout_ms),
                readTimeout=int(timeout_ms),
                bypassCertValidation=bool(bypass_cert),
                username=(username if username else ""),
                password=(password if password else ""),
                headerValues=(headers if headers else {}),
                throwOnError=False
            )
            return True, max(0, now_ms() - start), "HTTP reachable"
        except Exception as ex:
            return False, max(0, now_ms() - start), "HTTP FAIL: %s" % safe_str(ex)

    def normalize_url(base, endpoint):
        b = safe_str(base).strip()
        e = safe_str(endpoint).strip()
        if not b:
            return ""
        if not e:
            return b
        if not e.startswith("/"):
            e = "/" + e
        if b.endswith("/"):
            b = b[:-1]
        return b + e

    def json_list(v):
        try:
            if v is None:
                return []
            s = safe_str(v).strip()
            if not s:
                return []
            obj = system.util.jsonDecode(s)
            if isinstance(obj, list):
                out = []
                for x in obj:
                    xs = safe_str(x).strip()
                    if xs:
                        out.append(xs)
                return out
            return []
        except:
            return []

    def update_alarm_display():
        paths = [HEALTH_ROOT + "/" + s + "/IsHealthy" for s in OVERALL_SERVICES]
        bad = []
        try:
            qvs = system.tag.readBlocking(paths)
            for i, svc in enumerate(OVERALL_SERVICES):
                ok = False
                try:
                    ok = qvs[i].quality.isGood() and bool(qvs[i].value)
                except:
                    ok = False
                if not ok:
                    bad.append(svc)
        except:
            bad = list(OVERALL_SERVICES)

        txt = "Healthy" if not bad else ("BAD: " + ", ".join(bad))
        write_tags([ALARM_TEXT_TAG], [txt])
        return txt

    # start timing
    t_start = now_ms()
    deadline = t_start + RUN_BUDGET_MS

    # Always bump heartbeat + counter so you can SEE the timer firing
    try:
        write_tags([HEARTBEAT_TAG, LAST_RUN_AT_TAG], [now_dt(), now_dt()])
    except:
        pass
    try:
        cur = int(read_tag(TIMER_COUNTER_TAG, 0) or 0)
        write_tags([TIMER_COUNTER_TAG], [cur + 1])
    except:
        pass

    # Re-entrance guard
    if bool(g.get(RUNNING_KEY, False)):
        since = long(g.get(RUNNING_SINCE_KEY, 0) or 0)
        if (now_ms() - since) < GUARD_STALE_MS:
            try:
                if tag_exists(LAST_RUN_MS_TAG):
                    write_tags([LAST_RUN_MS_TAG], [0])
            except:
                pass
            return
        else:
            g[RUNNING_KEY] = False

    g[RUNNING_KEY] = True
    g[RUNNING_SINCE_KEY] = t_start

    try:
        enabled = bool(read_tag(ENABLE_TAG, True))
        if not enabled:
            write_tags([ALARM_TEXT_TAG], ["DISABLED"])
            return

        # Optional bypass knobs (create these tags if you want to turn warnings off)
        sitesync_bypass = bool(read_tag(CFG_ROOT + "/SiteSyncBypassSSL", True))
        piadapter_bypass = bool(read_tag(CFG_ROOT + "/PIAdapterBypassSSL", True))
        extraurl_bypass = bool(read_tag(CFG_ROOT + "/ExtraURLBypassSSL", True))

        # Bulk config read (missing tags => None)
        cfg_names = [
            "BrokerHost","BrokerPort","MQTTTxStatusTag",
            "SiteSyncUIHost","SiteSyncUIPort","SiteSyncUIExternalIP",
            "PIWebAPIBase","PIWebAPIEndpoint","PIWebAPIAuthScheme","PIWebAPIUser","PIWebAPIPassword","PIWebAPIToken","PIWebAPITimeoutMs","PIWebAPIInsecureOK",
            "PIAdapterAPIURL","PIAdapterBase",
            "DevicesRoot","TimestampSuffix","TPStaleMs","TPScanMinMs",
            "AzureHealthURL","GeoEventHealthURL",
            "ActilityHTTPSIPs","ActilityCloudfrontIPs","ActilityHTTPSPort","ActilityMQTTTLSPort","ActilityRequireBoth",
        ]
        cfg_paths = [CFG_ROOT + "/" + n for n in cfg_names]
        qvs = system.tag.readBlocking(cfg_paths)
        cfg = {}
        for i, n in enumerate(cfg_names):
            cfg[n] = qv_value(qvs[i], None)

        failures = []
        w_paths, w_vals = [], []

        # MQTT Broker (TCP)
        ok, lat, msg = tcp_connect(cfg.get("BrokerHost"), cfg.get("BrokerPort"), 1500)
        w_paths, w_vals = set_service("MQTT_Broker", ok, ("OK" if ok else "DOWN"), msg, lat, None, w_paths, w_vals)
        if not ok: failures.append("MQTT_Broker")

        # MQTT Transmission (connected tag + AGE from tag timestamp)
        tx_tag = safe_str(cfg.get("MQTTTxStatusTag")).strip()
        if tx_tag:
            try:
                qv = system.tag.readBlocking([tx_tag])[0]
                tx_ok = bool(qv.quality.isGood() and bool(qv.value))
                age = None
                try:
                    age = max(0, now_ms() - long(system.date.toMillis(qv.timestamp)))
                except:
                    age = None
                w_paths, w_vals = set_service("MQTT_Transmission", tx_ok, ("OK" if tx_ok else "DOWN"),
                                              ("Connected=%s" % ("True" if tx_ok else "False")),
                                              0, age, w_paths, w_vals)
                if not tx_ok: failures.append("MQTT_Transmission")
            except Exception as ex:
                w_paths, w_vals = set_service("MQTT_Transmission", False, "ERROR", safe_str(ex), -1, None, w_paths, w_vals)
                failures.append("MQTT_Transmission")
        else:
            w_paths, w_vals = set_service("MQTT_Transmission", False, "MISCONFIG", "MQTTTxStatusTag empty", 0, None, w_paths, w_vals)
            failures.append("MQTT_Transmission")

        # SiteSync API reachability (https then http)
        ss_host = safe_str(cfg.get("SiteSyncUIHost")).strip()
        ss_port = int(cfg.get("SiteSyncUIPort") or 0)
        if ss_host and ss_port > 0:
            ok1, lat1, msg1 = http_reach("https://%s:%d/" % (ss_host, ss_port), 2000, bypass_cert=sitesync_bypass)
            if ok1:
                ss_ok, ss_lat, ss_msg = True, lat1, msg1
            else:
                ok2, lat2, msg2 = http_reach("http://%s:%d/" % (ss_host, ss_port), 2000, bypass_cert=sitesync_bypass)
                ss_ok, ss_lat, ss_msg = ok2, lat2, ("HTTPS fail; " + msg2)
            w_paths, w_vals = set_service("SiteSync_API", ss_ok, ("OK" if ss_ok else "DOWN"), ss_msg, ss_lat, None, w_paths, w_vals)
            if not ss_ok: failures.append("SiteSync_API")
        else:
            w_paths, w_vals = set_service("SiteSync_API", False, "MISCONFIG", "SiteSyncUIHost/Port empty", 0, None, w_paths, w_vals)
            failures.append("SiteSync_API")

        # PI Web API
        pi_url = normalize_url(cfg.get("PIWebAPIBase"), cfg.get("PIWebAPIEndpoint"))
        pi_to = int(cfg.get("PIWebAPITimeoutMs") or 5000)
        pi_to = min(max(pi_to, 250), 5000)
        pi_insec = bool(cfg.get("PIWebAPIInsecureOK") or False)
        scheme = safe_str(cfg.get("PIWebAPIAuthScheme")).strip().lower()

        if pi_url and now_ms() < deadline:
            headers = {"Accept":"application/json"}
            user = None
            pw = None
            if scheme == "bearer":
                tok = safe_str(cfg.get("PIWebAPIToken")).strip()
                if tok:
                    headers["Authorization"] = "Bearer " + tok
            elif scheme == "basic":
                user = safe_str(cfg.get("PIWebAPIUser")).strip()
                pw   = safe_str(cfg.get("PIWebAPIPassword")).strip()

            ok, lat, msg = http_reach(pi_url, pi_to, bypass_cert=pi_insec, headers=headers, username=user, password=pw)
            w_paths, w_vals = set_service("PI_WebAPI", ok, ("OK" if ok else "DOWN"), msg, lat, None, w_paths, w_vals)
            if not ok: failures.append("PI_WebAPI")
        else:
            w_paths, w_vals = set_service("PI_WebAPI", False, "MISCONFIG", "PIWebAPIBase/Endpoint empty or budget", 0, None, w_paths, w_vals)
            failures.append("PI_WebAPI")

        # --- PI Adapter ---
        ad_url = safe_str(cfg.get("PIAdapterAPIURL")).strip()
        if (not ad_url):
            base = safe_str(cfg.get("PIAdapterBase")).strip()
            if base:
                ad_url = base.rstrip("/") + "/api/v1/configuration"
        if ad_url and now_ms() < deadline:
            ok, lat, msg = http_reach(ad_url, 3000, bypass_cert=piadapter_bypass, headers={"Accept":"application/json"})
            w_paths, w_vals = set_service("PI_Adapter", ok, ("OK" if ok else "DOWN"), msg, lat, None, w_paths, w_vals)
            if not ok: failures.append("PI_Adapter")
        else:
            w_paths, w_vals = set_service("PI_Adapter", False, "MISCONFIG", "PIAdapterAPIURL/Base empty or budget", 0, None, w_paths, w_vals)
            failures.append("PI_Adapter")

        # Optional URLs (Azure / GeoEvent)
        for svc, key in [("Azure_Function","AzureHealthURL"), ("GeoEvent","GeoEventHealthURL")]:
            u = safe_str(cfg.get(key)).strip()
            if u and now_ms() < deadline:
                ok, lat, msg = http_reach(u, 3000, bypass_cert=extraurl_bypass)
                w_paths, w_vals = set_service(svc, ok, ("OK" if ok else "DOWN"), msg, lat, None, w_paths, w_vals)
                if not ok: failures.append(svc)
            else:
                w_paths, w_vals = set_service(svc, True, "SKIP", "Not configured or budget", 0, None, w_paths, w_vals)

        # Actility (rotated IP probes; if none configured => SKIP healthy)
        if now_ms() < deadline:
            https_ips = json_list(cfg.get("ActilityHTTPSIPs"))
            cf_ips    = json_list(cfg.get("ActilityCloudfrontIPs"))
            https_port= int(cfg.get("ActilityHTTPSPort") or 443)
            mqtt_port = int(cfg.get("ActilityMQTTTLSPort") or 8883)
            require_both = bool(cfg.get("ActilityRequireBoth") or False)

            candidates = https_ips + cf_ips
            if not candidates and not https_ips:
                w_paths, w_vals = set_service("Actility_API", True, "SKIP", "No Actility IPs configured", 0, None, w_paths, w_vals)
            else:
                idx = int(g.get(ACT_IDX_KEY, 0) or 0)
                g[ACT_IDX_KEY] = idx + 2

                def probe_any(ips, port):
                    if not ips:
                        return (False, "No IPs")
                    for j in range(min(2, len(ips))):
                        ip = ips[(idx + j) % len(ips)]
                        ok, lat, msg = tcp_connect(ip, port, 1200)
                        if ok:
                            return (True, "TCP OK %s:%d" % (ip, port))
                    return (False, "All probes failed port %d" % port)

                https_ok, https_msg = probe_any(candidates, https_port)
                mqtt_ok, mqtt_msg   = probe_any(https_ips, mqtt_port) if https_ips else (False, "No MQTT IP list")

                act_ok = (https_ok and mqtt_ok) if require_both else (https_ok or mqtt_ok)
                act_msg = "HTTPS=%s; MQTT=%s" % (https_msg, mqtt_msg)
                w_paths, w_vals = set_service("Actility_API", act_ok, ("OK" if act_ok else "DOWN"), act_msg, 0, None, w_paths, w_vals)
                if not act_ok: failures.append("Actility_API")
        else:
            w_paths, w_vals = set_service("Actility_API", True, "SKIP", "Budget", 0, None, w_paths, w_vals)

        # ThingPark inbound (fast scan)
        if now_ms() < deadline:
            devices_root = safe_str(cfg.get("DevicesRoot")).strip()
            suffix = safe_str(cfg.get("TimestampSuffix")).strip()
            stale_ms = int(cfg.get("TPStaleMs") or 300000)
            scan_min_ms = int(cfg.get("TPScanMinMs") or 60000)

            if not devices_root or not suffix:
                w_paths, w_vals = set_service("ThingPark_Inbound", False, "MISCONFIG", "DevicesRoot/TimestampSuffix empty", 0, None, w_paths, w_vals)
                failures.append("ThingPark_Inbound")
            else:
                last_scan = long(g.get(TP_LAST_SCAN_KEY, 0) or 0)
                if (now_ms() - last_scan) < scan_min_ms:
                    cached_age = g.get(TP_LAST_AGE_KEY, None)
                    if cached_age is None:
                        w_paths, w_vals = set_service("ThingPark_Inbound", True, "SKIP", "Throttled (no cache yet)", 0, None, w_paths, w_vals)
                    else:
                        ok = (int(cached_age) <= stale_ms)
                        w_paths, w_vals = set_service("ThingPark_Inbound", ok, ("OK" if ok else "STALE"),
                                                      "Throttled cached age=%dms" % int(cached_age),
                                                      0, int(cached_age), w_paths, w_vals)
                        if not ok: failures.append("ThingPark_Inbound")
                else:
                    cache = g.get(TP_CACHE_KEY, None)
                    if not isinstance(cache, dict):
                        cache = {}

                    cache_root = cache.get("root", None)
                    cache_suf  = cache.get("suffix", None)
                    folders    = cache.get("folders", None)
                    refreshed  = long(cache.get("refreshedMs", 0) or 0)

                    if (folders is None) or (cache_root != devices_root) or (cache_suf != suffix) or ((now_ms() - refreshed) > TP_FOLDER_REFRESH_MS):
                        folders = []
                        br = system.tag.browse(devices_root)  # NON-recursive
                        for r in br.getResults():
                            try:
                                if bool(r.get("hasChildren", False)):
                                    fp = r.get("fullPath", None)
                                    if fp is not None:
                                        folders.append(fp.toString() if hasattr(fp, "toString") else str(fp))
                            except:
                                pass
                        cache = {"root": devices_root, "suffix": suffix, "folders": folders, "refreshedMs": now_ms()}
                        g[TP_CACHE_KEY] = cache

                    if not folders:
                        w_paths, w_vals = set_service("ThingPark_Inbound", False, "DOWN", "No device folders under DevicesRoot", 0, None, w_paths, w_vals)
                        failures.append("ThingPark_Inbound")
                    else:
                        suf = suffix[1:] if suffix.startswith("/") else suffix
                        ts_paths = [("%s/%s" % (f, suf)) for f in folders]
                        if len(ts_paths) > TP_MAX_TS_READ:
                            ts_paths = ts_paths[:TP_MAX_TS_READ]

                        newest = None
                        for i in range(0, len(ts_paths), TP_READ_CHUNK):
                            if now_ms() >= deadline:
                                break
                            chunk = ts_paths[i:i+TP_READ_CHUNK]
                            qvs2 = system.tag.readBlocking(chunk)
                            for qv2 in qvs2:
                                try:
                                    if (qv2 is None) or (not qv2.quality.isGood()) or (qv2.value is None):
                                        continue
                                    v = qv2.value
                                    if hasattr(v, "getTime"):
                                        tms = long(v.getTime())
                                    else:
                                        tms = long(v)
                                        if tms < 100000000000:
                                            tms *= 1000
                                    if newest is None or tms > newest:
                                        newest = tms
                                except:
                                    pass

                        g[TP_LAST_SCAN_KEY] = now_ms()

                        if newest is None:
                            w_paths, w_vals = set_service("ThingPark_Inbound", False, "STALE", "No valid timestamps found (check suffix)", 0, None, w_paths, w_vals)
                            failures.append("ThingPark_Inbound")
                        else:
                            age = max(0, now_ms() - newest)
                            g[TP_LAST_AGE_KEY] = int(age)
                            ok = (age <= stale_ms)
                            msg = "NewestAgeMs=%d (stale>%d)" % (int(age), int(stale_ms))
                            w_paths, w_vals = set_service("ThingPark_Inbound", ok, ("OK" if ok else "STALE"), msg, 0, int(age), w_paths, w_vals)
                            if not ok: failures.append("ThingPark_Inbound")
        else:
            w_paths, w_vals = set_service("ThingPark_Inbound", True, "SKIP", "Budget", 0, None, w_paths, w_vals)

        # Commit all service writes in one shot
        if w_paths:
            write_tags(w_paths, w_vals)

        # Update AlarmDisplayText from IsHealthy tags
        update_alarm_display()

        # Clear last error
        if tag_exists(LAST_ERROR_TAG):
            write_tags([LAST_ERROR_TAG], [""])

        # Runtime
        if tag_exists(LAST_RUN_MS_TAG):
            write_tags([LAST_RUN_MS_TAG], [int(now_ms() - t_start)])

    except Exception as ex:
        err = traceback.format_exc()
        try:
            log.error("UnifiedHealthCheck failed: %s" % safe_str(ex))
        except:
            pass
        if tag_exists(LAST_ERROR_TAG):
            write_tags([LAST_ERROR_TAG], [err[:3900]])
        write_tags([ALARM_TEXT_TAG], ["SCRIPT ERROR: %s" % safe_str(ex)])

    finally:
        try:
            if tag_exists(LAST_RUN_AT_TAG):
                write_tags([LAST_RUN_AT_TAG], [now_dt()])
        except:
            pass
        g[RUNNING_KEY] = False
        g[RUNNING_SINCE_KEY] = 0

_entrypoint()
