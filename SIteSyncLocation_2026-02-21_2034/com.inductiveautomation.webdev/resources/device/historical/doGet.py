def doGet(request, session):

	name = request["params"].get("name", None)
	devEUI = request["params"].get("id", None)
	start = request["params"].get("start", None)
	end = request["params"].get("end", None)
	
	if not name and not devEUI:
		return {"code": 400, "json": {"error": "Missing param: name or id"}}
	if not start or not end:
		return {"code": 400, "json": {"error": "Missing param: start and end (ISO format)"}}
	
	deviceName = name
	if devEUI and not name:
		deviceName = SiteSync.Location._findDeviceFolder(devEUI)
		if not deviceName:
			return {"code": 404, "json": {"error": "Device not found"}}
	
	basePath = "[default]Location/%s" % deviceName
	latPath = "%s/latitude" % basePath
	lngPath = "%s/longitude" % basePath
	
	try:
		startDate = system.date.parse(start)
		endDate = system.date.parse(end)
	except:
		return {"code": 400, "json": {"error": "Invalid date format. Use ISO: 2026-02-15T00:00:00Z"}}
	
	history = system.tag.queryTagHistory(
		paths=[latPath, lngPath],
		startDate=startDate,
		endDate=endDate,
		returnSize=-1,
		aggregationMode="LastValue",
		returnFormat="Wide"
	)
	
	points = []
	for row in range(history.getRowCount()):
		lat = history.getValueAt(row, 1)
		lng = history.getValueAt(row, 2)
		ts = history.getValueAt(row, 0)
		if lat is not None and lng is not None:
			points.append({
				"timestamp": str(ts),
				"latitude": float(lat),
				"longitude": float(lng)
			})
	
	return {"json": {"device": deviceName, "points": points, "count": len(points)}}