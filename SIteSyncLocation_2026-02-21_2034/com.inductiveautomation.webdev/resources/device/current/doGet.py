def doGet(request, session):
	logger = system.util.getLogger("SiteSync.API.DeviceCurrent")
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