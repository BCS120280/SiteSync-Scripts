def doPost(request, session):

    logger = system.util.getLogger("SiteSync.API.DeviceHistory")
    basePath = "[default]GVL"

    try:
        data = request["data"]
        devEUI = data.get("id") or data.get("devEUI")
        name   = data.get("name")

        # Find the device path
        devicePath = None

        if devEUI:
            devicePath = SiteSync.Location._getDevicePath(devEUI)
        elif name:
            existing = system.tag.browse(basePath, filter={"name": name, "recursive": False})
            if len(existing) > 0:
                devicePath = str(existing[0]["fullPath"])

        if devicePath is None:
            return {"code": 404, "json": {"error": "Device not found"}}

        dates = data.get("reportDates", {})
        startStr = dates.get("startDate")
        endStr   = dates.get("endDate")

        if not startStr or not endStr:
            return {"code": 400, "json": {"error": "Missing startDate or endDate"}}

        startDate = system.date.parse(startStr)
        endDate   = system.date.parse(endStr)

        if system.date.daysBetween(startDate, endDate) > 7:
            return {"json": {"error": "Date range exceeds 7 days"}}

        queryPaths = [
            "%s/latitude" % devicePath,
            "%s/longitude" % devicePath
        ]

        dataset = system.tag.queryTagHistory(
            paths=queryPaths,
            startDate=startDate,
            endDate=endDate,
            returnSize=-1,
            aggregationMode="LastValue",
            noInterpolation=True,
            includeBoundingValues=True
        )

        points = []
        for row in range(dataset.getRowCount()):
            ts  = dataset.getValueAt(row, "t_stamp")
            lat = dataset.getValueAt(row, 0)
            lng = dataset.getValueAt(row, 1)

            if lat is not None and lng is not None and lat != 0.0:
                points.append({
                    "timestamp": system.date.format(ts, "yyyy-MM-dd'T'HH:mm:ss'Z'"),
                    "latitude":  lat,
                    "longitude": lng
                })

        return {"json": {"device": devicePath.split("/")[-1], "points": points, "count": len(points)}}

    except Exception as e:
        logger.error("Error in device/historical API: %s" % str(e))
        return {"json": {"error": str(e)}}


def doGet(request, session):
    logger = system.util.getLogger("SiteSync.API.DeviceCurrent")
    basePath = "[default]GVL"

    try:
        # Support lookup by devEUI or by name
        devEUI = request["params"].get("id", None)
        name   = request["params"].get("name", None)

        device = None

        if devEUI:
            device = SiteSync.Location.getDevice(devEUI)
        elif name:
            device = SiteSync.Location.getDeviceByName(name)
        else:
            return {"code": 400, "json": {"error": "Missing param: id (devEUI) or name"}}

        if device is None:
            return {"code": 404, "json": {"error": "Device not found"}}

        return {"json": device}

    except Exception as e:
        logger.error("Error in device/current API: %s" % str(e))
        return {"json": {"error": str(e)}}