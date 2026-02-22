def doPost(request, session):
	logger = system.util.getLogger("SiteSync.ThingPark.Webhook")
	
	try:
		payload = request["data"]
		
		if payload is None:
			return {"code": 400, "json": {"error": "Empty request body"}}
		
		logger.debug("Received ThingPark webhook: %s" % str(payload)[:500])
		
		data = None
		
		# Standard ThingPark uplink
		if "DevEUI_uplink" in payload or "DevEUI" in payload or "devEUI" in payload:
			data = SiteSync.Location.parseThingParkUplink(payload)
		
		# TPX Location Engine callback
		elif "coordinates" in payload and "deviceEUI" in payload:
			data = SiteSync.Location.parseTPXLocation(payload)
		
		# Generic lat/lng payload
		elif "latitude" in payload or "lat" in payload:
			data = SiteSync.Location.parseThingParkUplink(payload)
		
		# Batch array of uplinks
		elif isinstance(payload, list):
			results = []
			for item in payload:
				itemData = SiteSync.Location.parseThingParkUplink(item)
				if itemData and itemData.get("devEUI"):
					SiteSync.Location.updateDeviceTags(itemData["devEUI"], itemData)
					results.append(itemData["devEUI"])
			return {"code": 200, "json": {"status": "ok", "processed": len(results)}}
		
		else:
			logger.warn("Unrecognized payload format")
			return {"code": 400, "json": {"error": "Unrecognized payload format"}}
		
		if data is None or data.get("devEUI") is None:
			return {"code": 400, "json": {"error": "Could not parse DevEUI"}}
		
		SiteSync.Location.updateDeviceTags(data["devEUI"], data)
		
		logger.info("Processed uplink for %s: lat=%s, lng=%s" % (
			data["devEUI"], data.get("latitude"), data.get("longitude")))
		
		return {"code": 200, "json": {
			"status":       "ok",
			"devEUI":       data["devEUI"],
			"latitude":     data.get("latitude"),
			"longitude":    data.get("longitude")
		}}
		
	except Exception as e:
		logger.error("Webhook error: %s" % str(e))
		return {"code": 500, "json": {"error": str(e)}}