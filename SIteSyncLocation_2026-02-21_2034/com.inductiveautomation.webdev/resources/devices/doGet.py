def doGet(request, session):
	logger = system.util.getLogger("SiteSync.API.Devices")
	try:
		devices = SiteSync.Location.getAllDevices()
		
		# Optional filter: ?asset=Forklift
		assetFilter = request["params"].get("asset", None)
		if assetFilter:
			devices = [d for d in devices if d.get("asset", "").lower() == assetFilter.lower()]
		
		# Optional filter: ?online=true
		onlineOnly = request["params"].get("online", None)
		if onlineOnly and onlineOnly.lower() == "true":
			devices = [d for d in devices if d.get("online", False)]
		
		return {"json": {"devices": devices, "count": len(devices)}}
		
	except Exception as e:
		logger.error("Error in devices API: %s" % str(e))
		return {"json": {"error": str(e)}}