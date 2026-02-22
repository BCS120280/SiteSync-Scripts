folderSource = "[default]" 
tagProvider = '[default]' #"[MQTT Engine]"

#folderSource = "[MQTT Engine]Edge Nodes/Chevron_Data" ##sarah and asonya, remove hashtag to activate
import json
def getDeviceName(tagPath):
	##get the tag path name 
	newTagPath = tagPath.split("/metaData")[0].split("/")[-1]
	
	return newTagPath
	
def getTagPath(deviceName, tagPath):
	newPath = tagPath.split("/" + deviceName)[0]
	return newPath 
	
	

def getDevicesMakeAndModel():
	##gets all device names in folder Edge Node ID, returns array for dropdown with device name, tagPath
	
	tags = system.tag.browse(folderSource,{"recursive":True, "name":"model"})	
	dropDown = []
	items = {}
	mfgItems = {}
	productTypes = {}
	for i in tags.getResults():
		model = str(i['value'].value)
		if model != "None":
			if model in items.keys():
				continue
			else:
				items[model] = model
				mfgPath = str(i['fullPath']).replace('model', 'manufacturer')
				mfg = system.tag.readBlocking([mfgPath])[0].value
	
				if mfg != None:
					try:
						formattedModel = {"label":model,
											"value":model}
						if mfg in mfgItems.keys():
							
							mfgItems[mfg].append(formattedModel)
						else:
							mfgItems[mfg] = []
							mfgItems[mfg].append(formattedModel)
					except Exception as e:
						print e
						
				prdPath = str(i['fullPath']).replace('model', 'sensorType')
				prd = system.tag.readBlocking([prdPath])[0].value
	
				if prd != None:
					try:
						formattedPrd = {"label":prd,
											"value":prd}
						if prd in productTypes.keys():
							
							productTypes[prd].append(formattedModel)
						else:
							productTypes[prd] = []
							productTypes[prd].append(formattedModel)
					except Exception as e:
						print e
					
	return mfgItems, items.keys(), productTypes.keys()
		


def getTagsByType(deviceType):
	allTags  = system.tag.browse(folderSource, {"recursive":True, "name":"sensorType"}).results
	items = {}
	for i in allTags:
		tagPath = str(i["fullPath"])
		print tagPath
		if '_types_' in str(tagPath):
		    print("UDT")
		else:
			if i['value'].value == deviceType or deviceType == "ALL":
				deviceName = getDeviceName(tagPath)
				deviceRootPath = getTagPath(deviceName, tagPath) + "/" + deviceName
				print "DEVICE " +  deviceName  + " is type" + deviceType
				items[deviceName] = deviceRootPath
	return items


def getTagsByModel(deviceType):
	allTags  = system.tag.browse(folderSource, {"recursive":True, "name":"model"}).results
	items = {}
	for i in allTags:
		tagPath = str(i["fullPath"])
		print tagPath
		if '_types_' in str(tagPath):
		    print("UDT")
		else:
			if i['value'].value == deviceType:
				deviceName = getDeviceName(tagPath)
				deviceRootPath = getTagPath(deviceName, tagPath) + "/" + deviceName
				items[deviceName] = deviceRootPath
	return items
			
	
def getAllTrackedTags(sensorBase):
	
	listOfTrackedTags = {}
	system.perspective.print(sensorBase)
	tags = system.tag.browse(sensorBase, {"recursive":True}).results
	for t in tags:
		try:
			if "Tag" in str(t['tagType']) and "history" in t["attributes"]:
				tagName = t["name"]	
				listOfTrackedTags[tagName] = str(t['fullPath'])
		except Exception as e:
			system.perspective.print("cant process tag:" + t)
	return listOfTrackedTags

def getSensorBase(deviceType):

	if deviceType == "PRESSURE":
		return  tagProvider + "_types_/SiteSync/PressureSensor"
	elif deviceType == "VALVEPOSITION":
		return tagProvider + "_types_/SiteSync/ValvePositionSensor"
	elif deviceType == "CURRENT":
		return tagProvider + "_types_/SiteSync/CurrentSensor"
	elif deviceType == "VOLTAGE":
		return tagProvider + "_types_/SiteSync/VoltageSensor"
	else:
		return  tagProvider + "_types_/SiteSync/" + deviceType
		
def getModelBase(deviceType):

	return tagProvider + "_types_/SiteSync/" + deviceType

def getSimpleTags(deviceType):
	print "getting simple tags"
	print deviceType
	modelMapper = {"TEPressure":"PRESSURE", 
				"PDS2-L - Differential Pressure":"PRESSURE", 
				"TWTGPressure":"PRESSURE", 
				"SushiPressure":"PRESSURE", 
				"AloxyValvePosition":"VALVE POSITION",
				"HotDrop-Direct":"AMPERAGE",
				"HotDrop-Cloud":"AMPERAGE", 
				"HotDrop":"AMPERAGE", 
				"VoltDrop":"VOLTAGE"
				}
	if deviceType in modelMapper.keys():
		##convert model to type
		system.perspective.print("product title in models")
		deviceType = modelMapper[deviceType]
		system.perspective.print("New model:  " + deviceType)
	cols = {}
	if deviceType == "PRESSURE":
		cols["pressure"] =  tagProvider + "_types_/SiteSync/PressureSensor/Measurements/pressure"
		cols["temperature"] =  tagProvider + "_types_/SiteSync/PressureSensor/Measurements/temperature"
	elif deviceType == "VALVEPOSITION":
		cols["logicalPosition"] =  tagProvider + "_types_/SiteSync/ValvePositionSensor/Measurements/logicalPosition"
		cols["isOpen"] =  tagProvider + "_types_/SiteSync/ValvePositionSensor/Measurements/isOpen"
	elif deviceType == "AMPERAGE":
		cols["averageCurrent_Ampere"] =  tagProvider + "_types_/SiteSync/CurrentSensor/Measurements/averageCurrent_Ampere"
		cols["temperature_Celsius"] =  tagProvider + "_types_/SiteSync/CurrentSensor/Measurements/temperature_Celsius"
	elif deviceType == "VOLTAGE":
		cols["phaseAVoltage_Volt"] =  tagProvider + "_types_/SiteSync/VoltageSensor/Measurements/phaseAVoltage_Volt"
		cols["phaseBVoltage_Volt"] =  tagProvider + "_types_/SiteSync/VoltageSensor/Measurements/phaseBVoltage_Volt"
	elif deviceType == "ALL":
		cols["reportedValue"] = tagProvider + "_types_/SiteSync/metaData/valueToDisplay"
		
	return cols

	
	
def getDevicesProductType(deviceType, viewType):
	deviceTagPaths = getTagsByType(deviceType)
	staticColumns = getTableColumns(viewType)
	if viewType == "Simple":
		
		system.perspective.print("Getting simple tags")
		trackedColumns = getSimpleTags(deviceType).keys()

	else:
		print "Getting full tags"
		trackedColumns = getAllTrackedTags(getSensorBase(deviceType)).keys()
	rows = []
	for deviceName, device in deviceTagPaths.items():

		items = rowFormatterSimple(device, deviceName, trackedColumns, staticColumns, viewType)							
		rows.append(items)
			
	return rows
	
	
def rowFormatterSimple(device, deviceName,trackedColumns, staticColumns, viewType):
	'''accepts tag row, returns formatted table row'''
	items = {}
	try:
		allTags  = system.tag.browse(device, {"recursive":True}).results
		for tag in allTags:
			tagTitle = str(tag["fullPath"]).split('/')[-1]
			if tag["tagType"] != "Folder":
				# deviceName = str(tag["fullPath"]).split(']')[1].split('/')[0]
				items["Name"] = deviceName
				#items["tagPath"] =  str(tag["fullPath"]).split(deviceName)[0] + "/" + deviceName
				
				if "/LoRaMetrics/" + tagTitle  in staticColumns:
									
					tagName = str(tag["fullPath"]).split('/')[-1]
					if tagName == "MesgTimeStamp":
						tagName = "Last Reported"
						tagValue = timeFormatter(tag["value"].value)
					elif  tagName == "battery":
						tagName = "Battery"
						tagValue = str(tag["value"].value)
					else:
						tagValue = str(tag["value"].value)
					items[tagName] = tagValue
					
					
				
				elif "/metaData/" + tagTitle  in staticColumns or tagTitle in trackedColumns:
					tagName = str(tag["fullPath"]).split('/')[-1]
					try:
						tagValue = str(tag["value"].value)
					except:
						system.perspective.print("Not able to find value: " + str(tag))
						tagValue = "None"
					if "customAttributes" in tagTitle:
						print "meta: " + tagValue 
						tagName = "Notes"
						tagValue = metaDataFormatter(tagValue)
						
					if "model" in tagTitle:
						tagName = "Product"
					elif "devEUI" in tagTitle:
						tagName = "DevEUI"
						
					items[tagName] = tagValue
					
	#				if viewType != "Simple" and tagTitle in trackedColumns and "/metaData/" + tagTitle not in staticColumns:
	#					print "Getting setpoints for " + str(tag["fullPath"])
	#					tagP = getHiLow( str(tag["fullPath"]))
	#					engUnits = system.tag.readBlocking(tagP)
	#					items[tagName + "High"] = engUnits[0].value
	#					items[tagName + "Low"] = engUnits[1].value
						
	except:
		items = None
					
	return items
	
def getDevicesbyModel(deviceType, viewType):
	deviceTagPaths = getTagsByModel(deviceType)
	staticColumns = getTableColumns(viewType)
	if viewType == "Simple":
		system.perspective.print("Getting simple tags")
		trackedColumns = getSimpleTags(deviceType).keys()

	else:
		print "Getting full tags"
		trackedColumns = getAllTrackedTags(getModelBase(deviceType)).keys()
	print "TRACKED COLUMNS"
	print trackedColumns
	rows = []
	for deviceName, device in deviceTagPaths.items():
		
		items = rowFormatter(device, deviceName, trackedColumns, staticColumns, viewType)					
		rows.append(items)
	return rows
	
	
def getRows(deviceType, viewType,  deviceTagPaths, trackedColumns, staticColumns):
#	staticColumns = getTableColumns(viewType)
#	if viewType == "Simple":
#		system.perspective.print("simple tags")	
#		trackedColumns = getSimpleTags(deviceType).keys()
#	else:
#		system.perspective.print("full tags")
#		firstInstance = deviceTagPaths.values()[0]
#		trackedColumns = getAllTrackedTags(firstInstance).keys()
		
	rows = []
	for deviceName, device in deviceTagPaths.items():
		#system.perspective.print(deviceName)
		items = rowFormatterSimple(device, deviceName, trackedColumns, staticColumns, viewType)
		if items != None:					
			rows.append(items)
	return rows


def getTrackedColumns(deviceType, viewType):
	if viewType == "Simple":
		#system.perspective.print("simple tags")	
		trackedColumns = getSimpleTags(deviceType).keys()
	else:
		#system.perspective.print("full tags")
		firstInstance = deviceTagPaths.values()[0]
		trackedColumns = getAllTrackedTags(firstInstance).keys()
	return trackedColumns
	

def timeFormatter(t): 		
	# Get the current datetime

	days = system.date.daysBetween(t, system.date.now())
	#system.perspective.print(days)
	if days > 0:
		if days > 1:
			return str(days) + " days ago"
		else:
			return str(days) + " days ago"
	else:
		hours = system.date.hoursBetween(t, system.date.now())
		if hours > 0:
			if hours > 1:
				return str(hours) + " hours ago"
			else:
				return str(hours) + " hour ago"
		else:
			minutes = system.date.minutesBetween(t, system.date.now())
			if minutes > 0:
				if minutes > 1:
					return str(minutes) + " minutes ago"
				else:
					return str(minutes) + " minute ago"
			else:
				seconds = system.date.secondsBetween(t, system.date.now())
				if seconds > 1:
					return str(seconds) + " seconds ago"
				else:
					return str(seconds) + " second ago"
				


def getHiLow(tagPath):
	'''accepts tag path, returns array with hgih low paths'''
	paths = []
	paths.append(tagPath + ".EngHigh")
	paths.append(tagPath + ".EngLow")
	return paths

def rowFormatter(device, deviceName,trackedColumns, staticColumns, viewType):
	'''accepts tag row, returns formatted table row'''
	items = {}
	allTags  = system.tag.browse(device, {"recursive":True}).results
	for tag in allTags:
		tagTitle = str(tag["fullPath"]).split('/')[-1]
		if tag["tagType"] != "Folder":
			# deviceName = str(tag["fullPath"]).split(']')[1].split('/')[0]
			items["Name"] = deviceName
			items["tagPath"] =  str(tag["fullPath"]).split(deviceName)[0] + "/" + deviceName

			if "/LoRaMetrics/" + tagTitle  in staticColumns:
				
				tagName = str(tag["fullPath"]).split('/')[-1]
				if tagName == "MesgTimeStamp":
					tagName = "Last Reported"
					tagValue = timeFormatter(tag["value"].value)
				else:
					tagValue = str(tag["value"].value)
				items[tagName] = tagValue
			
			elif "/metaData/" + tagTitle  in staticColumns or tagTitle in trackedColumns:
			
				tagName = str(tag["fullPath"]).split('/')[-1]
				try:
					tagValue = str(tag["value"].value)
				except:
					#system.perspective.print("Not able to find value: " + str(tag))
					tagValue = "None"
				if "customAttributes" in tagTitle:
					print "meta: " + tagValue 
					tagName = "Notes"
					tagValue = metaDataFormatter(tagValue)
					
				if "model" in tagTitle:
					tagName = "Product"
					
				
				if "battery" in tagTitle and "LoRaMerics" in str(tag["fullPath"]):		
					tagName = "None"
				
				if tagTitle in trackedColumns and viewType != "Simple":
					#print "Getting setpoints for " + str(tag["fullPath"])
				#	tagP = getHiLow( str(tag["fullPath"]))
					#engUnits = system.tag.readBlocking(tagP)
					items[tagName + "High"] = engUnits[0].value
					items[tagName + "Low"] = engUnits[1].value
					
					
					
				#if tagTitle in trackedColumns and viewType == "Setpoint":
				#	items[tagName] = tagValue
				if tagName != "None":
					items[tagName] = tagValue
	return items
	
	
def staticColumnOrder(deviceType, firstRow):

	#system.perspective.print("setting static columns")	
	startingCols = ["DevEUI", "Name", "Last Reported"]
		
	endingCols = ["Battery", "RSSI", "Product"]
	columns = []
	

	for key in startingCols:
	
		d = getColumnTemplate(key, False)
		columns.append(d)



	sensorCols = []
	
	modelMapper = {"TEPressure":"PRESSURE", 
				"PDS2-L - Differential Pressure":"PRESSURE", 
				"TWTGPressure":"PRESSURE", 
				"SushiPressure":"PRESSURE", 
				"AloxyValvePosition":"VALVE POSITION",
				"HotDrop-Direct":"CURRENT",
				"HotDrop-Cloud":"CURRENT"
				}
	if deviceType in modelMapper.keys():
		##convert model to type
	#	system.perspective.print("product title in models")
		deviceType = modelMapper[deviceType]
	#	system.perspective.print("New model:  " + deviceType)
	
	if deviceType == "PRESSURE":
		sensorCols = ["pressure", "temperature"]
	elif deviceType == "VALVEPOSITION":
		sensorCols = ["isOpen", "logicalPosition"]
	elif deviceType == "ALL":
		sensorCols = ["isOpen", "logicalPosition"]

	elif deviceType == "AMPERAGE":
		sensorCols = ["valueToDisplay"]
	
	for key in firstRow.keys():
		if key in startingCols:
			#dont worry about it
			print "moving on"
		elif key in endingCols:
			print "moving on"
		elif key in sensorCols:
			#only add dynamic middle columns
		#	system.perspective.print("adding dynamic column:" + key )
			d = getColumnTemplate(key, False)
			columns.append(d)

			
	
	

	for key in endingCols:
		d = getColumnTemplate(key, False)
		columns.append(d)
		
	return columns
		
	
def getDeviceColumnOrder(firstRow, selectedSetpoints):
	counter = 0
	keyHolder = {}
	columns = []
	startingCols = ["DevEUI", "Name", "Last Reported"]
	
	endingCols = ["Battery", "RSSI", "Product", "firmware_version", "Notes"]
	##first set standard columns
	
	for key in startingCols:
		keyHolder[key] = counter
		d = getColumnTemplate(key, False)
		columns.append(d)
		counter += 1 
	
	middleCols = {}
	dynamicKeys = []
	
	for key in firstRow.keys():
		if key in keyHolder.keys():
			#dont worry about it
			print "moving on"
		elif key in endingCols:
			print "moving on"
		else:
			#only add dynamic middle columns
			#system.perspective.print("adding dynamic column:" + key )
			keyHolder[key] = counter
			editable = False
			if key in selectedSetpoints:
				system.perspective.print("showing setpoint" + key)
				d = getColumnTemplate(key, editable)
				middleCols[key] = d
				dynamicKeys.append(key)
				counter += 1 
			elif key.replace("Low", "") in selectedSetpoints:
				system.perspective.print("showing setpoint" + key)
				system.perspective.print("showing setpoint " + key + "Low")
				d = getColumnTemplate(key, editable)
				middleCols[key] = d
				dynamicKeys.append(key)
				counter += 1 
			elif  key.replace("High", "") in selectedSetpoints:
				system.perspective.print("showing setpoint" + key)
				d = getColumnTemplate(key, editable)
				middleCols[key] = d
				dynamicKeys.append(key)
				counter += 1 
			else:
				
				if "High" in key or "Low" in key:
					system.perspective.print("Hiding setpoint " + key)
					d = getColumnTemplateHidden(key, editable)
					middleCols[key] = d
					dynamicKeys.append(key)
					counter += 1 
				else:
				
					d = getColumnTemplate(key, editable)
					middleCols[key] = d
					dynamicKeys.append(key)
					counter += 1 
	
	dynamicKeys.sort()
	
	
	
	for m in dynamicKeys:
										
		columns.append(middleCols[m])	
						
	for key in endingCols:
		keyHolder[key] = counter
		editable = False
	
		d = getColumnTemplate(key, False)
		columns.append(d)
		counter += 1 
			
					
				

			
	return columns
			
	
	## then loop through and add dynamic columns
	
def metaDataFormatter(metaData):
	##loops through metadata, creates multiline notes
	note = ""
	print "Starting metaFormatter"
	print metaData
	d = json.loads(metaData)
	
	try:
		for key, value in d.items():
			print key
			note += key + ": " + value + "\n"
		return note
	except:
		return ""
	
				
def getColumnTemplateHidden(fieldName, editable):
				j = {
				  "field": fieldName,
				  "visible": False,
				  "editable": editable,
				  "render": "auto",
				  "justify": "auto",
				  "align": "center",
				  "resizable": True,
				  "sortable": True,
				  "sort": "none",
				  "filter": {
				    "enabled": False,
				    "visible": "on-hover",
				    "string": {
				      "condition": "",
				      "value": ""
				    },
				    "number": {
				      "condition": "",
				      "value": ""
				    },
				    "boolean": {
				      "condition": ""
				    },
				    "date": {
				      "condition": "",
				      "value": ""
				    }
				  },
				  "viewPath": "",
				  "viewParams": {},
				  "boolean": "checkbox",
				  "number": "value",
				  "progressBar": {
				    "max": 100,
				    "min": 0,
				    "bar": {
				      "color": "",
				      "style": {
				        "classes": ""
				      }
				    },
				    "track": {
				      "color": "",
				      "style": {
				        "classes": ""
				      }
				    },
				    "value": {
				      "enabled": False,
				      "format": "0,0.##",
				      "justify": "center",
				      "style": {
				        "classes": ""
				      }
				    }
				  },
				  "toggleSwitch": {
				    "color": {
				      "selected": "",
				      "unselected": ""
				    }
				  },
				  "nullFormat": {
				    "includeNullStrings": False,
				    "strict": False,
				    "nullFormatValue": ""
				  },
				  "numberFormat": "0,0.##",
				  "dateFormat": "MM/DD/YYYY",
				  "width": "",
				  "strictWidth": False,
				  "style": {
				    "classes": ""
				  },
				  "header": {
				    "title": "",
				    "justify": "left",
				    "align": "center",
				    "style": {
				      "classes": ""
				    }
				  },
				  "footer": {
				    "title": "",
				    "justify": "left",
				    "align": "center",
				    "style": {
				      "classes": ""
				    }
				  }
				}	
				return j
							
		
def getColumnTemplate(fieldName, editable):
	j = {
	  "field": fieldName,
	  "visible": True,
	  "editable": editable,
	  "render": "auto",
	  "justify": "auto",
	  "align": "center",
	  "resizable": True,
	  "sortable": True,
	  "sort": "none",
	  "filter": {
	    "enabled": False,
	    "visible": "on-hover",
	    "string": {
	      "condition": "",
	      "value": ""
	    },
	    "number": {
	      "condition": "",
	      "value": ""
	    },
	    "boolean": {
	      "condition": ""
	    },
	    "date": {
	      "condition": "",
	      "value": ""
	    }
	  },
	  "viewPath": "",
	  "viewParams": {},
	  "boolean": "checkbox",
	  "number": "value",
	  "progressBar": {
	    "max": 100,
	    "min": 0,
	    "bar": {
	      "color": "",
	      "style": {
	        "classes": ""
	      }
	    },
	    "track": {
	      "color": "",
	      "style": {
	        "classes": ""
	      }
	    },
	    "value": {
	      "enabled": True,
	      "format": "0,0.##",
	      "justify": "center",
	      "style": {
	        "classes": ""
	      }
	    }
	  },
	  "toggleSwitch": {
	    "color": {
	      "selected": "",
	      "unselected": ""
	    }
	  },
	  "nullFormat": {
	    "includeNullStrings": False,
	    "strict": False,
	    "nullFormatValue": ""
	  },
	  "numberFormat": "0,0.##",
	  "dateFormat": "MM/DD/YYYY",
	  "width": "",
	  "strictWidth": False,
	  "style": {
	    "classes": ""
	  },
	  "header": {
	    "title": "",
	    "justify": "left",
	    "align": "center",
	    "style": {
	      "classes": ""
	    }
	  },
	  "footer": {
	    "title": "",
	    "justify": "left",
	    "align": "center",
	    "style": {
	      "classes": ""
	    }
	  }
	}	
	return j
	
	
	
def getHistoricalData(paths, timeFrame):
	endTime = system.date.now()
	startTime = system.date.addDays(endTime, -14)
	history = system.tag.queryTagHistory(paths, startDate=startTime, endDate=endTime)
	return history
	
def getTableColumns(viewType):
	#fields needed in every table, along side the tracked values
	if viewType == "Simple":
		defaultFields = ["/metaData/devEUI", "/LoRaMetrics/MesgTimeStamp",  "/LoRaMetrics/battery", "/LoRaMetrics/RSSI", "/metaData/model"]
	else:
		defaultFields = ["/metaData/devEUI", "/LoRaMetrics/MesgTimeStamp", "/metaData/firmware_version", "/metaData/customAttributes", 
				   "/LoRaMetrics/RSSI", "/LoRaMetrics/battery", "/metaData/model", "/metaData/equipmentMonitoring"]
	return defaultFields
	