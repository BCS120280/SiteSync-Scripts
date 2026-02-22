def doGet(request, session):
	logger = system.util.getLogger("SiteSync.API.Devices")
	try:
		devices = SiteSync.Location.getAllDevices()
		
		# Optional filter: ?name=Cart  (partial match on folder name)
		nameFilter = request["params"].get("name", None)
		if nameFilter:
			devices = [d for d in devices if nameFilter.lower() in d.get("name", "").lower()]
		
		# Optional filter: ?online=true
		onlineOnly = request["params"].get("online", None)
		if onlineOnly and onlineOnly.lower() == "true":
			devices = [d for d in devices if d.get("online", False)]
		
		# Optional filter: ?moving=true
		movingOnly = request["params"].get("moving", None)
		if movingOnly and movingOnly.lower() == "true":
			devices = [d for d in devices if d.get("moving", "") == "true"]
		
		return {"json": {"devices": devices, "count": len(devices)}}
		
	except Exception as e:
		logger.error("Error in devices API: %s" % str(e))
		return {"json": {"error": str(e)}}