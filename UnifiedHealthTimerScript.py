# Ignition 8.1.x - Gateway Timer Script
# Name: SiteSyncStatus/health.unified
#  Dedicated thread, Fixed Delay, 60,000ms

import socket, time, traceback

# Bind system safely
try:
    import system as SYS
except:
    import system
    SYS = system

LOG = None
try:
    LOG = SYS.util.getLogger("health.unified")
except:
    LOG = None

PROVIDER    = "[default]"
HEALTH_BASE = PROVIDER + "Health"
CFG_BASE    = HEALTH_BASE + "/Config"
DBG_BASE    = HEALTH_BASE + "/Debug"

SERVICES = [
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

# Time / globals
now_dt = SYS.date.now()
now_ms = long(SYS.date.toMillis(now_dt))

g = SYS.util.getGlobals()
GUARD_KEY = "health.unified.running"
GUARD_TS  = "health.unified.runningTs"
GUARD_STALE_MS = 120000  # 2 min

# --- Always bump heartbeat + counter
try:
    SYS.tag.writeBlocking(
        [HEALTH_BASE + "/ScriptHeartbeat", DBG_BASE + "/LastRunAt"],
        [now_dt, now_dt]
    )
except:
    pass

try:
    q = SYS.tag.readBlocking([DBG_BASE + "/TimerCounter"])[0]
    cur = 0
    if q is not None and q.quality.isGood() and q.value is not None:
        cur = int(q.value)
    SYS.tag.writeBlocking([DBG_BASE + "/TimerCounter"], [cur + 1])
except:
    pass

# Re-entrance guard (skip overlaps, but don’t “kill” future runs)
do_work = True
try:
    if bool(g.get(GUARD_KEY, False)):
        last = long(g.get(GUARD_TS, 0) or 0)
        if (now_ms - last) < GUARD_STALE_MS:
            do_work = False
        else:
            # stale guard, clear it and proceed
            g[GUARD_KEY] = False
except:
    pass

if not do_work:
    # show “skip” as 0ms runtime so you can spot it in Gateway Scripts status
    try:
        SYS.tag.writeBlocking([DBG_BASE + "/LastRunMs"], [0])
    except:
        pass
else:
    start_ms = now_ms
    g[GUARD_KEY] = True
    g[GUARD_TS]  = now_ms

    last_error = ""

    # Collect service updates; write them at the end in one bulk write.
    svc_results = {}  # svc -> dict(ok, msg, latency, lastInboundMs(optional))

    try:
        # CONFIG READS (safe defaults)
        # Helper inline: read first good tag value from a list
        def _read_first(paths, default):
            try:
                qvs = SYS.tag.readBlocking(paths)
                for q in qvs:
                    try:
                        if q is not None and q.quality.isGood() and q.value is not None:
                            return q.value
                    except:
                        pass
            except:
                pass
            return default

        broker_host = _read_first([CFG_BASE + "/BrokerHost", CFG_BASE + "/MQTTBrokerHost"], "localhost")
        broker_port = int(_read_first([CFG_BASE + "/BrokerPort", CFG_BASE + "/MQTTBrokerPort"], 1883))

        mqtt_tx_tag = _read_first(
            [CFG_BASE + "/MQTTTxConnectedTag", CFG_BASE + "/MQTTTransmissionConnectedTag"],
            "[MQTT Transmission]Transmission Info/Connected"
        )

        sitesync_tenant_id = int(_read_first([CFG_BASE + "/SiteSyncTenantId"], 1))
        sitesync_ui_host   = _read_first([CFG_BASE + "/SiteSyncUIHost"], None)
        sitesync_ui_port   = int(_read_first([CFG_BASE + "/SiteSyncUIPort"], 8043))
        sitesync_ui_path   = str(_read_first([CFG_BASE + "/SiteSyncUIPath"], "/") or "/")
        sitesync_ui_insec  = bool(_read_first([CFG_BASE + "/SiteSyncUIBypassSSL"], False))

        pi_webapi_base     = _read_first([CFG_BASE + "/PIWebAPIBase"], None)
        pi_webapi_endpoint = str(_read_first([CFG_BASE + "/PIWebAPIEndpoint"], "/system") or "/system")
        pi_webapi_scheme   = str(_read_first([CFG_BASE + "/PIWebAPIAuthScheme"], "Bearer") or "Bearer")
        pi_webapi_token    = _read_first([CFG_BASE + "/PIWebAPIToken"], None)
        pi_webapi_user     = _read_first([CFG_BASE + "/PIWebAPIUsername"], None)
        pi_webapi_pass     = _read_first([CFG_BASE + "/PIWebAPIPassword"], None)
        pi_webapi_timeout  = int(_read_first([CFG_BASE + "/PIWebAPITimeoutMs"], 5000))
        pi_webapi_insec    = bool(_read_first([CFG_BASE + "/PIWebAPIBypassSSL"], False))

        pi_adapter_url     = _read_first([CFG_BASE + "/PIAdapterHealthURL", CFG_BASE + "/PIAdapterBase"], None)
        pi_adapter_timeout = int(_read_first([CFG_BASE + "/PIAdapterTimeoutMs"], 4000))
        pi_adapter_insec   = bool(_read_first([CFG_BASE + "/PIAdapterBypassSSL"], True))

        tp_devices_root    = _read_first([CFG_BASE + "/DevicesRoot", CFG_BASE + "/ThingParkDevicesRoot"], None)
        tp_suffix          = _read_first([CFG_BASE + "/TimestampSuffix", CFG_BASE + "/ThingParkTimestampSuffix"], None)
        tp_stale_ms        = long(_read_first([CFG_BASE + "/TPStaleMs", CFG_BASE + "/ThingParkStaleMs"], 300000))
        tp_scan_min_ms     = long(_read_first([CFG_BASE + "/TPScanMinMs", CFG_BASE + "/ThingParkScanMinMs"], 30000))

        azure_url    = _read_first([CFG_BASE + "/Azure_Function_URL", CFG_BASE + "/AzureFunctionURL"], None)
        geo_url      = _read_first([CFG_BASE + "/GeoEvent_URL", CFG_BASE + "/GeoEventURL"], None)
        actility_url = _read_first([CFG_BASE + "/Actility_API_URL", CFG_BASE + "/ActilityURL"], None)

        # HTTP CLIENT (safe create)
        def _client(insecure):
            try:
                return SYS.net.httpClient(bypassCertValidation=bool(insecure))
            except:
                return SYS.net.httpClient()

        # MQTT TRANSMISSION
        try:
            q = SYS.tag.readBlocking([mqtt_tx_tag])[0]
            ok = bool(q.quality.isGood() and bool(q.value))
            # age since the Connected tag last changed
            age_ms = -1
            try:
                age_ms = long(now_ms - long(SYS.date.toMillis(q.timestamp)))
            except:
                pass
            svc_results["MQTT_Transmission"] = {"ok": ok, "msg": ("" if ok else "Connected tag is False/Bad"), "lat": -1, "inb": age_ms}
        except Exception as ex:
            svc_results["MQTT_Transmission"] = {"ok": False, "msg": str(ex), "lat": -1, "inb": -1}

        # MQTT BROKER TCP CONNECT
        try:
            t0 = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            try:
                s.connect((str(broker_host), int(broker_port)))
                ok = True
                msg = ""
            except Exception as ex:
                ok = False
                msg = "TCP connect failed to %s:%s (%s)" % (broker_host, broker_port, ex)
            try:
                s.close()
            except:
                pass
            lat = int((time.time() - t0) * 1000.0)
            svc_results["MQTT_Broker"] = {"ok": ok, "msg": msg, "lat": lat}
        except Exception as ex:
            svc_results["MQTT_Broker"] = {"ok": False, "msg": str(ex), "lat": -1}

        # SiteSync API (module call)
        try:
            t0 = SYS.date.now()
            raw = SYS.sitesync.testJoinAPIImpl(int(sitesync_tenant_id))
            ms = int(SYS.date.millisBetween(t0, SYS.date.now()))
            txt = "" if raw is None else str(raw)
            ok = bool(raw) and ("error" not in txt.lower())
            svc_results["SiteSync_API"] = {"ok": ok, "msg": ("" if ok else txt[:4000]), "lat": ms}
        except Exception as ex:
            svc_results["SiteSync_API"] = {"ok": False, "msg": "SiteSync API check failed: %s" % ex, "lat": -1}

        # ---- PI WEB API ----
        if pi_webapi_base:
            try:
                url = str(pi_webapi_base).rstrip("/") + (pi_webapi_endpoint if pi_webapi_endpoint.startswith("/") else ("/" + pi_webapi_endpoint))
                headers = {}
                if pi_webapi_token:
                    headers["Authorization"] = "%s %s" % (pi_webapi_scheme.strip(), str(pi_webapi_token))
                t0 = SYS.date.now()
                resp = _client(pi_webapi_insec).get(
                    url,
                    connectTimeout=pi_webapi_timeout,
                    readTimeout=pi_webapi_timeout,
                    headers=(headers if headers else None),
                    username=pi_webapi_user,
                    password=pi_webapi_pass
                )
                ms = int(SYS.date.millisBetween(t0, SYS.date.now()))
                code = int(resp.getStatusCode())
                ok = (200 <= code < 300)
                svc_results["PI_WebAPI"] = {"ok": ok, "msg": ("" if ok else ("HTTP %d" % code)), "lat": ms}
            except Exception as ex:
                svc_results["PI_WebAPI"] = {"ok": False, "msg": str(ex), "lat": -1}
        else:
            svc_results["PI_WebAPI"] = {"ok": True, "msg": "Skipped: PIWebAPIBase not set", "lat": -1}

        # ---- PI ADAPTER ----
        if pi_adapter_url:
            try:
                url = str(pi_adapter_url).strip()
                # if they give a base, add a common status path
                if url.lower().startswith("http") and ("/" in url[8:]):
                    full = url
                else:
                    full = url.rstrip("/") + "/system/status"
                t0 = SYS.date.now()
                resp = _client(pi_adapter_insec).get(
                    full,
                    connectTimeout=pi_adapter_timeout,
                    readTimeout=pi_adapter_timeout
                )
                ms = int(SYS.date.millisBetween(t0, SYS.date.now()))
                code = int(resp.getStatusCode())
                ok = (200 <= code < 300)
                svc_results["PI_Adapter"] = {"ok": ok, "msg": ("" if ok else ("HTTP %d" % code)), "lat": ms}
            except Exception as ex:
                svc_results["PI_Adapter"] = {"ok": False, "msg": str(ex), "lat": -1}
        else:
            svc_results["PI_Adapter"] = {"ok": True, "msg": "Skipped: PIAdapterHealthURL/Base not set", "lat": -1}

        # ---- ThingPark inbound (browse + newest timestamp age, cached) ----
        if tp_devices_root and tp_suffix:
            try:
                cache_t  = long(g.get("tp.cache.t", 0) or 0)
                cache_ms = g.get("tp.cache.newest", None)
                cache_ct = int(g.get("tp.cache.count", 0) or 0)

                newest = None
                count = 0

                if (now_ms - cache_t) < tp_scan_min_ms and cache_ms is not None:
                    newest = long(cache_ms)
                    count = cache_ct
                else:
                    res = SYS.tag.browse(str(tp_devices_root), {"recursive": True})
                    paths = []
                    for r in res.getResults():
                        fp = ""
                        try:
                            fp = str(r["fullPath"])
                        except:
                            try:
                                fp = str(r.get("fullPath"))
                            except:
                                fp = str(getattr(r, "fullPath", ""))
                        if fp.endswith(str(tp_suffix)):
                            paths.append(fp)

                    count = len(paths)
                    newest = None
                    if paths:
                        qvs = SYS.tag.readBlocking(paths)
                        for q in qvs:
                            try:
                                if q is not None and q.quality.isGood() and q.value is not None:
                                    ts = long(SYS.date.toMillis(q.value))
                                    if newest is None or ts > newest:
                                        newest = ts
                            except:
                                pass

                    g["tp.cache.t"] = now_ms
                    g["tp.cache.newest"] = newest
                    g["tp.cache.count"] = count

                if newest is None:
                    svc_results["ThingPark_Inbound"] = {"ok": False, "msg": "No timestamp tags found (root=%s suffix=%s)" % (tp_devices_root, tp_suffix), "lat": -1, "inb": -1}
                else:
                    age = long(now_ms - newest)
                    ok = (age <= tp_stale_ms)
                    msg = "%d devices; newest age=%dms; stale>%dms" % (count, age, tp_stale_ms)
                    svc_results["ThingPark_Inbound"] = {"ok": ok, "msg": ("" if ok else msg), "lat": -1, "inb": age}
            except Exception as ex:
                svc_results["ThingPark_Inbound"] = {"ok": False, "msg": str(ex), "lat": -1, "inb": -1}
        else:
            svc_results["ThingPark_Inbound"] = {"ok": True, "msg": "Skipped: DevicesRoot/TimestampSuffix not set", "lat": -1, "inb": -1}

        # Optional URL checks
        def _url_check(url, insecure=True):
            try:
                t0 = SYS.date.now()
                resp = _client(insecure).get(str(url), connectTimeout=4000, readTimeout=4000)
                ms = int(SYS.date.millisBetween(t0, SYS.date.now()))
                code = int(resp.getStatusCode())
                ok = (200 <= code < 300)
                return ok, ms, ("" if ok else ("HTTP %d" % code))
            except Exception as ex:
                return False, -1, str(ex)

        if azure_url:
            ok, ms, msg = _url_check(azure_url, True)
            svc_results["Azure_Function"] = {"ok": ok, "msg": msg, "lat": ms}
        else:
            svc_results["Azure_Function"] = {"ok": True, "msg": "Skipped: Azure_Function_URL not set", "lat": -1}

        if geo_url:
            ok, ms, msg = _url_check(geo_url, True)
            svc_results["GeoEvent"] = {"ok": ok, "msg": msg, "lat": ms}
        else:
            svc_results["GeoEvent"] = {"ok": True, "msg": "Skipped: GeoEvent_URL not set", "lat": -1}

        if actility_url:
            ok, ms, msg = _url_check(actility_url, True)
            svc_results["Actility_API"] = {"ok": ok, "msg": msg, "lat": ms}
        else:
            svc_results["Actility_API"] = {"ok": True, "msg": "Skipped: Actility_API_URL not set", "lat": -1}

        # BULK WRITE ALL SERVICE TAGS
        write_paths = []
        write_vals  = []

        for svc in SERVICES:
            base = HEALTH_BASE + "/" + svc
            r = svc_results.get(svc, {"ok": False, "msg": "No result (script logic)", "lat": -1})
            ok = bool(r.get("ok", False))
            msg = str(r.get("msg", "") or "")
            lat = int(r.get("lat", -1))
            write_paths += [
                base + "/IsHealthy",
                base + "/Status",
                base + "/Message",
                base + "/LatencyMs",
                base + "/LastCheck",
            ]
            write_vals += [
                ok,
                ("OK" if ok else "BAD"),
                msg[:4000],
                lat,
                now_dt,
            ]
            if ok:
                write_paths.append(base + "/LastOK")
                write_vals.append(now_dt)

            if "inb" in r:
                try:
                    write_paths.append(base + "/LastInboundMs")
                    write_vals.append(long(r.get("inb", -1)))
                except:
                    pass

        try:
            SYS.tag.writeBlocking(write_paths, write_vals)
        except Exception as ex:
            last_error = "writeBlocking(service tags) failed: %s" % ex

        # Overall display strings (based on IsHealthy tags)
        bad = []
        try:
            is_paths = [HEALTH_BASE + "/" + s + "/IsHealthy" for s in SERVICES]
            qvs = SYS.tag.readBlocking(is_paths)
            for i in range(len(qvs)):
                ok = False
                try:
                    ok = qvs[i].quality.isGood() and bool(qvs[i].value)
                except:
                    ok = False
                if not ok:
                    bad.append(SERVICES[i])
        except:
            bad = list(SERVICES)

        summary = "OK" if not bad else ("BAD: " + ", ".join(bad))

        try:
            SYS.tag.writeBlocking(
                [HEALTH_BASE + "/AlarmDisplayText", HEALTH_BASE + "/Fault_Summary"],
                [summary, summary]
            )
        except:
            pass

        # latch last fault
        if bad:
            try:
                prev = SYS.tag.readBlocking([HEALTH_BASE + "/Last_Fault"])[0]
                prev_val = "" if (prev is None or (not prev.quality.isGood())) else str(prev.value or "")
                if prev_val != summary:
                    SYS.tag.writeBlocking(
                        [HEALTH_BASE + "/Last_Fault", HEALTH_BASE + "/Last_Fault_At"],
                        [summary, now_dt]
                    )
            except:
                pass

    except Exception as ex:
        last_error = "%s\n%s" % (ex, traceback.format_exc())
        if LOG:
            try: LOG.error("health.unified failed: %s" % ex)
            except: pass

    finally:
        end_dt = SYS.date.now()
        end_ms = long(SYS.date.toMillis(end_dt))
        dur = int(end_ms - start_ms)

        try:
            SYS.tag.writeBlocking(
                [DBG_BASE + "/LastRunMs", DBG_BASE + "/LastError"],
                [dur, (last_error or "")]
            )
        except:
            pass

        try:
            g[GUARD_KEY] = False
        except:
            pass