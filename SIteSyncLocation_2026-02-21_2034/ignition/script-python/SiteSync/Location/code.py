TAG_PROVIDER = "default"
BASE_FOLDER  = "GVL"

_logger = system.util.getLogger("SiteSync.GVL")

# In-memory cache: devEUI -> folder name  (rebuilt on cache miss)
_devEUI_cache = {}


def _buildDevEUICache():
	"""Scan all device folders and build a devEUI -> folderName lookup."""
	global _devEUI_cache
	basePath = "[%s]%s" % (TAG_PROVIDER, BASE_FOLDER)
	folders = system.tag.browse(basePath, filter={"recursive": False})
	
	cache = {}
	euiPaths = []
	folderNames = []
	
	for f in folders:
		folderNames.append(str(f["name"]))
		euiPaths.append("%s/metaData/devEUI" % str(f["fullPath"]))
	
	if euiPaths:
		readings = system.tag.readBlocking(euiPaths)
		for i, reading in enumerate(readings):
			if reading.quality.isGood() and reading.value:
				eui = str(reading.value).lower().strip()
				cache[eui] = folderNames[i]
	
	_devEUI_cache = cache
	_logger.debug("DevEUI cache rebuilt: %d devices" % len(cache))
	return cache


def _findDeviceFolder(devEUI):
	"""Find the tag folder name for a given devEUI. Returns None if not found."""
	devEUI = devEUI.lower().strip()
	
	if devEUI in _devEUI_cache:
		return _devEUI_cache[devEUI]
	
	# Cache miss — rebuild
	cache = _buildDevEUICache()
	return cache.get(devEUI, None)


def _getDevicePath(devEUI):
	"""Get the full tag path for a device by devEUI. Returns None if not found."""
	folderName = _findDeviceFolder(devEUI)
	if folderName is None:
		return None
	return "[%s]%s/%s" % (TAG_PROVIDER, BASE_FOLDER, folderName)


def _readSiteTempF():
	"""Read the site-wide TempF tag from the GVL root."""
	basePath = "[%s]%s" % (TAG_PROVIDER, BASE_FOLDER)
	reading = system.tag.readBlocking(["%s/TempF" % basePath])[0]
	return reading.value if reading.value is not None else 0.0


# ─── Parsing ────────────────────────────────────────────────────────────────

def parseThingParkUplink(payload):
	"""
	Parse a standard Actility ThingPark uplink message.
	Returns dict with devEUI, latitude, longitude, etc., or None.
	"""
	try:
		result = {
			"devEUI": None, "latitude": None, "longitude": None,
			"time": None, "rawPayload": "",
			"battery": None, "temperature": None,
			"positionType": "UNKNOWN"
		}
		
		uplink = payload
		if "DevEUI_uplink" in payload:
			uplink = payload["DevEUI_uplink"]
		
		# Extract DevEUI
		devEUI = None
		for key in ["DevEUI", "devEUI", "deviceEUI", "deveui"]:
			if key in uplink:
				devEUI = str(uplink[key]).lower().strip()
				break
		if devEUI is None:
			_logger.warn("No DevEUI found in uplink payload")
			return None
		result["devEUI"] = devEUI
		
		# Timestamp
		for key in ["Time", "time", "timestamp"]:
			if key in uplink and uplink[key]:
				try:
					result["time"] = system.date.parse(str(uplink[key]))
				except:
					result["time"] = system.date.now()
				break
		if result["time"] is None:
			result["time"] = system.date.now()
		
		# Raw payload hex
		for key in ["payload_hex", "PayloadHex", "payloadHex"]:
			if key in uplink:
				result["rawPayload"] = str(uplink[key])
				break
		
		# LoRa metadata
		for key in ["FPort", "Fport", "fport"]:
			if key in uplink:
				result["fport"] = int(uplink[key])
				break
		
		for key in ["FCntUp", "fcntup", "SequenceNumber"]:
			if key in uplink:
				result["sequenceNumber"] = int(uplink[key])
				break
		
		if "SpFact" in uplink:
			result["datarateID"] = str(uplink["SpFact"])
		
		# Gateway info
		if "Lrrs" in uplink and "Lrr" in uplink["Lrrs"]:
			lrrs = uplink["Lrrs"]["Lrr"]
			if isinstance(lrrs, list) and len(lrrs) > 0:
				lrr = lrrs[0]
				if "LrrRSSI" in lrr:
					result["rssi"] = float(lrr["LrrRSSI"])
				if "LrrSNR" in lrr:
					result["snr"] = float(lrr["LrrSNR"])
				if "LrrID" in lrr:
					result["lastGateway"] = str(lrr["LrrID"])
		
		if "LrrRSSI" in uplink:
			result["rssi"] = float(uplink["LrrRSSI"])
		if "LrrSNR" in uplink:
			result["snr"] = float(uplink["LrrSNR"])
		
		# Extract coordinates (priority order)
		coordsFound = False
		
		# 1. resolved_position (TPX LE inline)
		if "resolved_position" in uplink:
			rp = uplink["resolved_position"]
			if "lat" in rp and "lng" in rp:
				result["latitude"]  = float(rp["lat"])
				result["longitude"] = float(rp["lng"])
				result["positionType"] = "NETWORK"
				coordsFound = True
		
		# 2. CustomerData.loc
		if not coordsFound and "CustomerData" in uplink:
			cd = uplink["CustomerData"]
			if "loc" in cd:
				loc = cd["loc"]
				if "lat" in loc and "lon" in loc:
					result["latitude"]  = float(loc["lat"])
					result["longitude"] = float(loc["lon"])
					result["positionType"] = "NETWORK"
					coordsFound = True
		
		# 3. Gateway fallback
		if not coordsFound:
			if "LrrLAT" in uplink and "LrrLON" in uplink:
				result["latitude"]  = float(uplink["LrrLAT"])
				result["longitude"] = float(uplink["LrrLON"])
				result["positionType"] = "GATEWAY"
				coordsFound = True
		
		# 4. Direct lat/lng
		if not coordsFound:
			for latKey in ["latitude", "lat"]:
				for lngKey in ["longitude", "lng", "lon"]:
					if latKey in uplink and lngKey in uplink:
						result["latitude"]  = float(uplink[latKey])
						result["longitude"] = float(uplink[lngKey])
						result["positionType"] = "DEVICE"
						coordsFound = True
						break
				if coordsFound:
					break
		
		# Battery
		for key in ["batteryLevel", "battery_percentage", "battery"]:
			if key in uplink:
				result["battery"] = str(uplink[key])
				break
		
		# Battery voltage
		if "battery_voltage" in uplink:
			result["batteryVoltage"] = str(uplink["battery_voltage"])
		
		# Temperature
		if "temperature" in uplink:
			result["temperature"] = str(uplink["temperature"])
		
		return result
	except Exception as e:
		_logger.error("Error parsing ThingPark uplink: %s" % str(e))
		return None


def parseTPXLocation(payload):
	"""
	Parse a ThingPark X Location Engine resolved location callback.
	Returns dict with devEUI, latitude, longitude, etc., or None.
	"""
	try:
		result = {
			"devEUI": None, "latitude": None, "longitude": None,
			"time": None, "rawPayload": "", "positionType": "RESOLVED"
		}
		
		devEUI = None
		for key in ["deviceEUI", "DevEUI", "devEUI", "deveui"]:
			if key in payload:
				devEUI = str(payload[key]).lower().strip()
				break
		if devEUI is None:
			return None
		result["devEUI"] = devEUI
		
		if "coordinates" in payload:
			coords = payload["coordinates"]
			if len(coords) >= 2:
				result["longitude"] = float(coords[0])
				result["latitude"]  = float(coords[1])
		
		if result["latitude"] is None:
			if "latitude" in payload and "longitude" in payload:
				result["latitude"]  = float(payload["latitude"])
				result["longitude"] = float(payload["longitude"])
		
		for key in ["time", "Time", "timestamp"]:
			if key in payload and payload[key]:
				try:
					result["time"] = system.date.parse(str(payload[key]))
				except:
					result["time"] = system.date.now()
				break
		if result["time"] is None:
			result["time"] = system.date.now()
		
		return result
	except Exception as e:
		_logger.error("Error parsing TPX LE location: %s" % str(e))
		return None


# ─── Tag Writing ─────────────────────────────────────────────────────────────

def updateDeviceTags(devEUI, data):
	"""
	Write parsed uplink data into the EXISTING tag structure.
	Looks up device folder by devEUI via metaData/devEUI scan.
	"""
	devicePath = _getDevicePath(devEUI)
	
	if devicePath is None:
		_logger.warn("Device not found for devEUI %s — cannot write tags" % devEUI)
		return
	
	paths  = []
	values = []
	
	# Core position
	if data.get("latitude") is not None:
		paths.append("%s/latitude" % devicePath)
		values.append(float(data["latitude"]))
	if data.get("longitude") is not None:
		paths.append("%s/longitude" % devicePath)
		values.append(float(data["longitude"]))
	
	# Battery (stored as string in your tags)
	if data.get("battery") is not None:
		paths.append("%s/battery_percentage" % devicePath)
		values.append(str(data["battery"]))
	if data.get("batteryVoltage") is not None:
		paths.append("%s/battery_voltage" % devicePath)
		values.append(str(data["batteryVoltage"]))
	
	# Temperature
	if data.get("temperature") is not None:
		paths.append("%s/temperature" % devicePath)
		values.append(str(data["temperature"]))
	
	# LoRa Metrics
	if data.get("time") is not None:
		epochMs = system.date.toMillis(data["time"])
		paths.append("%s/LoRaMetrics/MesgTimeStamp" % devicePath)
		values.append(epochMs)
	
	if data.get("rawPayload"):
		paths.append("%s/LoRaMetrics/lastPayload" % devicePath)
		values.append(str(data["rawPayload"]))
	
	if data.get("rssi") is not None:
		paths.append("%s/LoRaMetrics/RSSI" % devicePath)
		values.append(float(data["rssi"]))
	
	if data.get("snr") is not None:
		paths.append("%s/LoRaMetrics/SNR" % devicePath)
		values.append(float(data["snr"]))
	
	if data.get("lastGateway") is not None:
		paths.append("%s/LoRaMetrics/LastGateway" % devicePath)
		values.append(str(data["lastGateway"]))
	
	if data.get("fport") is not None:
		paths.append("%s/LoRaMetrics/Port" % devicePath)
		values.append(int(data["fport"]))
	
	if data.get("sequenceNumber") is not None:
		paths.append("%s/LoRaMetrics/SequenceNumber" % devicePath)
		values.append(int(data["sequenceNumber"]))
	
	if data.get("datarateID") is not None:
		paths.append("%s/LoRaMetrics/DatarateID" % devicePath)
		values.append(str(data["datarateID"]))
	
	if len(paths) > 0:
		results = system.tag.writeBlocking(paths, values)
		errors = [str(r) for r in results if not r.isGood()]
		if errors:
			_logger.warn("Tag write errors for %s: %s" % (devEUI, str(errors)))
		else:
			_logger.debug("Updated %d tags for %s" % (len(paths), devEUI))


# ─── Reading ─────────────────────────────────────────────────────────────────

def getAllDevices():
	"""
	Read all tracker devices and return a list of dicts.
	"""
	basePath = "[%s]%s" % (TAG_PROVIDER, BASE_FOLDER)
	folders = system.tag.browse(basePath, filter={"recursive": False})
	
	# Read site-wide TempF once
	tempF = _readSiteTempF()
	
	readPaths = []
	folderNames = []
	for f in folders:
		fp = str(f["fullPath"])
		folderNames.append(str(f["name"]))
		readPaths.extend([
			"%s/latitude" % fp,                    # 0
			"%s/longitude" % fp,                   # 1
			"%s/metaData/devEUI" % fp,             # 2
			"%s/metaData/locationDescription" % fp, # 3
			"%s/battery_percentage" % fp,           # 4
			"%s/battery_voltage" % fp,              # 5
			"%s/temperature" % fp,                  # 6
			"%s/moving" % fp,                       # 7
			"%s/tracking_state" % fp,               # 8
			"%s/LoRaMetrics/MesgTimeStamp" % fp,   # 9
			"%s/LoRaMetrics/LastGateway" % fp,      # 10
			"%s/LoRaMetrics/RSSI" % fp,            # 11
		])
	
	if not readPaths:
		return []
	
	readings = system.tag.readBlocking(readPaths)
	TAGS_PER_DEVICE = 12
	devices = []
	
	for i, folderName in enumerate(folderNames):
		offset = i * TAGS_PER_DEVICE
		
		lat       = readings[offset + 0].value
		lng       = readings[offset + 1].value
		devEUI    = readings[offset + 2].value or ""
		locDesc   = readings[offset + 3].value or ""
		battPct   = readings[offset + 4].value or ""
		battV     = readings[offset + 5].value or ""
		temp      = readings[offset + 6].value or ""
		moving    = readings[offset + 7].value or ""
		tracking  = readings[offset + 8].value or ""
		mesgTs    = readings[offset + 9].value
		lastGw    = readings[offset + 10].value or ""
		rssi      = readings[offset + 11].value
		
		# Format lastSeen from epoch ms
		lastSeenStr = None
		if mesgTs is not None and mesgTs > 0:
			try:
				lastSeenDate = system.date.fromMillis(long(mesgTs))
				lastSeenStr = system.date.format(lastSeenDate, "yyyy-MM-dd'T'HH:mm:ss'Z'")
			except:
				pass
		
		# Determine online: has reported in last 30 minutes
		online = False
		if mesgTs is not None and mesgTs > 0:
			try:
				nowMs = system.date.toMillis(system.date.now())
				online = (nowMs - long(mesgTs)) < (30 * 60 * 1000)
			except:
				pass
		
		device = {
			"name":              folderName,
			"devEUI":            str(devEUI).lower().strip() if devEUI else "",
			"locationDescription": locDesc,
			"latitude":          lat if lat else 0.0,
			"longitude":         lng if lng else 0.0,
			"battery_percentage": str(battPct),
			"battery_voltage":   str(battV),
			"temperature":       str(temp),
			"tempF":             tempF,
			"moving":            str(moving),
			"tracking_state":    str(tracking),
			"lastSeen":          lastSeenStr,
			"lastGateway":       lastGw,
			"rssi":              rssi if rssi else 0.0,
			"online":            online
		}
		devices.append(device)
	
	return devices


def getDevice(devEUI):
	"""
	Read a single tracker device by DevEUI.
	Returns dict or None.
	"""
	devicePath = _getDevicePath(devEUI)
	if devicePath is None:
		return None
	
	folderName = _findDeviceFolder(devEUI)
	
	# Read site-wide TempF once
	tempF = _readSiteTempF()
	
	paths = [
		"%s/latitude" % devicePath,                     # 0
		"%s/longitude" % devicePath,                    # 1
		"%s/metaData/devEUI" % devicePath,              # 2
		"%s/metaData/locationDescription" % devicePath,  # 3
		"%s/battery_percentage" % devicePath,            # 4
		"%s/battery_voltage" % devicePath,               # 5
		"%s/temperature" % devicePath,                   # 6
		"%s/moving" % devicePath,                        # 7
		"%s/tracking_state" % devicePath,                # 8
		"%s/operating_mode" % devicePath,                # 9
		"%s/LoRaMetrics/MesgTimeStamp" % devicePath,    # 10
		"%s/LoRaMetrics/lastPayload" % devicePath,       # 11
		"%s/LoRaMetrics/RSSI" % devicePath,             # 12
		"%s/LoRaMetrics/SNR" % devicePath,              # 13
		"%s/LoRaMetrics/LastGateway" % devicePath,       # 14
		"%s/LoRaMetrics/Port" % devicePath,              # 15
		"%s/LoRaMetrics/SequenceNumber" % devicePath,    # 16
		"%s/LoRaMetrics/DatarateID" % devicePath,        # 17
		"%s/LoRaMetrics/RXCentralFrequency" % devicePath, # 18
	]
	
	readings = system.tag.readBlocking(paths)
	
	mesgTs = readings[10].value
	lastSeenStr = None
	online = False
	if mesgTs is not None and mesgTs > 0:
		try:
			lastSeenDate = system.date.fromMillis(long(mesgTs))
			lastSeenStr = system.date.format(lastSeenDate, "yyyy-MM-dd'T'HH:mm:ss'Z'")
			nowMs = system.date.toMillis(system.date.now())
			online = (nowMs - long(mesgTs)) < (30 * 60 * 1000)
		except:
			pass
	
	return {
		"name":                folderName,
		"devEUI":              devEUI.lower().strip(),
		"locationDescription": readings[3].value or "",
		"latitude":            readings[0].value if readings[0].value else 0.0,
		"longitude":           readings[1].value if readings[1].value else 0.0,
		"battery_percentage":  str(readings[4].value or ""),
		"battery_voltage":     str(readings[5].value or ""),
		"temperature":         str(readings[6].value or ""),
		"tempF":               tempF,
		"moving":              str(readings[7].value or ""),
		"tracking_state":      str(readings[8].value or ""),
		"operating_mode":      str(readings[9].value or ""),
		"lastSeen":            lastSeenStr,
		"online":              online,
		"LoRaMetrics": {
			"lastPayload":       str(readings[11].value or ""),
			"RSSI":              readings[12].value if readings[12].value else 0.0,
			"SNR":               readings[13].value if readings[13].value else 0.0,
			"LastGateway":       str(readings[14].value or ""),
			"Port":              readings[15].value if readings[15].value else 0,
			"SequenceNumber":    readings[16].value if readings[16].value else 0,
			"DatarateID":        str(readings[17].value or ""),
			"RXCentralFrequency": readings[18].value if readings[18].value else 0.0,
		}
	}


def getDeviceByName(folderName):
	"""
	Read a single tracker device by its tag folder name (e.g. 'Cart-72-SC-272322').
	Returns dict or None.
	"""
	basePath = "[%s]%s" % (TAG_PROVIDER, BASE_FOLDER)
	existing = system.tag.browse(basePath, filter={"name": folderName, "recursive": False})
	if len(existing) == 0:
		return None
	
	# Read devEUI first
	devEUIPath = "%s/%s/metaData/devEUI" % (basePath, folderName)
	qv = system.tag.readBlocking([devEUIPath])[0]
	devEUI = str(qv.value).lower().strip() if qv.value else ""
	
	if devEUI:
		return getDevice(devEUI)
	return None