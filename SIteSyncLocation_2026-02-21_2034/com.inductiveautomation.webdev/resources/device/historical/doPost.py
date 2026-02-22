def doPost(request, session):

    logger = system.util.getLogger("SiteSync.API.DeviceHistory")
    
    try:
        data = request["data"]
        devEUI = data.get("id") or data.get("devEUI")
        name = data.get("name")
        
        if not devEUI and not name:
            return {"code": 400, "json": {"error": "Missing device id or name"}}
        
        dates = data.get("reportDates", {})
        startStr = dates.get("startDate")
        endStr   = dates.get("endDate")
        
        if not startStr or not endStr:
            return {"code": 400, "json": {"error": "Missing startDate or endDate"}}
        
        startDate = system.date.parse(startStr)
        endDate   = system.date.parse(endStr)
        
        if system.date.daysBetween(startDate, endDate) > 7:
            return {"json": {"error": "Date range exceeds 7 days"}}
        
        # Find device by name or devEUI
        deviceName = name
        if devEUI and not name:
            deviceName = SiteSync.Location._findDeviceFolder(devEUI)
        
        if not deviceName:
            return {"code": 404, "json": {"error": "Device not found"}}
        
        devicePath = "[default]Location/%s" % deviceName
        
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
        
        return {"json": {"device": deviceName, "points": points, "count": len(points)}}
        
    except Exception as e:
        logger.error("Error in device/historical API: %s" % str(e))
        return {"json": {"error": str(e)}}