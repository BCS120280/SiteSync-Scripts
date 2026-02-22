def doGet(request, session):

    TAG_ROOT = "[default]GVL"
    LAT_NAME = "latitude"
    LON_NAME = "longitude"

    def safe_float(v):
        try:
            return float(v)
        except:
            return None

    # Find all "latitude" tags under TAG_ROOT, then infer device folder = parent path.
    try:
        browse = system.tag.browse(TAG_ROOT, {"name": LAT_NAME, "recursive": True})
        results = browse.getResults() if hasattr(browse, "getResults") else browse
    except Exception as e:
        return {"json": {"ok": False, "error": "Browse failed: %s" % e}}

    device_paths = []
    for r in results:
        try:
            full = str(r["fullPath"])
            if full.endswith("/" + LAT_NAME):
                device_paths.append(full.rsplit("/", 1)[0])
        except:
            pass

    # De-dupe while preserving order
    seen = set()
    device_paths = [p for p in device_paths if not (p in seen or seen.add(p))]

    # Batch read
    read_paths = []
    for dev_path in device_paths:
        read_paths.extend([
            dev_path + "/" + LAT_NAME,
            dev_path + "/" + LON_NAME,
            dev_path + "/asset",
            dev_path + "/name",
        ])

    qvs = system.tag.readBlocking(read_paths) if read_paths else []
    devices = []

    for i, dev_path in enumerate(device_paths):
        lat_qv = qvs[i*4 + 0]
        lon_qv = qvs[i*4 + 1]
        asset_qv = qvs[i*4 + 2]
        name_qv = qvs[i*4 + 3]

        lat = safe_float(lat_qv.value)
        lon = safe_float(lon_qv.value)
        if lat is None or lon is None:
            continue

        dev_id = dev_path.split("/")[-1]
        last_seen = system.date.toMillis(lat_qv.timestamp)

        devices.append({
            "id": dev_id,
            "tagPath": dev_path,
            "name": (name_qv.value if name_qv.value not in [None, ""] else dev_id),
            "asset": (asset_qv.value if asset_qv.value not in [None, ""] else ""),
            "latitude": lat,
            "longitude": lon,
            "lastSeenMs": last_seen
        })

    return {"json": {"ok": True, "count": len(devices), "devices": devices}}