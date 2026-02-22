def updateLoRaMetricsParam(newParamValue, UDTName, attributeName):
	try:
		tags = system.tag.getConfiguration(UDTName +"/LoRaMetrics", True)
		
		o = 0
		for i in tags[0]['tags']:
			if i['name'] == attributeName:
				tags[0]['tags'][o]['value'] = newParamValue
			o += 1
			
		system.tag.configure( UDTName, tags, 'm')
	except Exception as e:
		system.perspective.print(str(e))
		system.perspective.print(attributeName)
	
	
def updateMetaDataParam(newParamValue, UDTName, attributeName):
	try:
		tags = system.tag.getConfiguration(UDTName +"/metaData", True)
		
		#system.perspective.print(UDTName)
		o = 0
		for i in tags[0]['tags']:
			if i['name'] == attributeName:
				tags[0]['tags'][o]['value'] = newParamValue
			o += 1
			
		res = system.tag.configure( UDTName, tags, 'm')
		
		system.perspective.print(res)
	except Exception as e:
		
		system.perspective.print(str(e))
		system.perspective.print(attributeName)
		
def updateMetaDataLimitedParam(newParamValue, UDTName, attributeName):
	try:
		system.perspective.print("Updating limited template: {0}".format(UDTName))
		tags = system.tag.getConfiguration(UDTName +"/metaData/sparkplug", True)
	
		o = 0
		system.perspective.print(tags[0]['tags'])
		for i in tags[0]['tags']:
			if i['name'] == attributeName:
				tags[0]['tags'][o]['value'] = newParamValue
				system.perspective.print("Updating limited template: {0}".format(newParamValue))
			o += 1
			

		system.tag.configure( UDTName + "/metaData", tags, 'm')

				
	except Exception as e:
		system.perspective.print(str(e))
		system.perspective.print(attributeName)
	
	
	
def modifyUDT(limitedTemplate, firmware, hardware, manufacturer, model, sensorType, expectedCheckin, UDTName):
	try:
		updateMetaDataParam(model, UDTName, 'model')
		updateMetaDataParam(manufacturer, UDTName, 'manufacturer')
		updateMetaDataParam(hardware, UDTName, 'hardware_version')
		updateMetaDataParam(firmware, UDTName, 'firmware_version')
		updateMetaDataParam(sensorType , UDTName,'sensorType' )
		system.perspective.print("Updating limited template: {0}".format(limitedTemplate))
		updateMetaDataLimitedParam( limitedTemplate, UDTName, 'template')
		updateLoRaMetricsParam(expectedCheckin, UDTName, 'expected_checkin_window')
	except Exception as e:
		system.perspective.print("Error updating UDT {0}".format(e))
