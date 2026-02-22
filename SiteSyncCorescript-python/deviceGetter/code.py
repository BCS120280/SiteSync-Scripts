folderName =  "[default]" 


def getDeviceName(tagPath):
	##get the tag path name 
	newTagPath = tagPath.split("/LoRaMetrics")[0].split("/")[-1]
	if ']' in newTagPath:
		newTagPath = newTagPath.split(']')[1]
	
	return newTagPath
def getTagPath(deviceName, tagPath):
	newPath = tagPath.split(deviceName + "/")[0]
	return newPath + deviceName

def getDevices():
	##gets all device names in folder Edge Node ID, returns array for dropdown with device name, tagPath
	
	tags = system.tag.browse(folderName,{"recursive":True})	
	dropDown = []
	items = {}
	for i in tags.getResults():
		tagPath = str(i['fullPath'])
		if "LoRaMetrics" in tagPath and "_types_/" not in tagPath:
			deviceName = getDeviceName(tagPath)
			deviceRootPath = getTagPath(deviceName, tagPath)
			items[deviceName] = deviceRootPath
			
		
	for item, value in items.items():
		instance = {}
		instance["label"] = item
		instance["value"] = value
		dropDown.append(instance)
		
	return dropDown
	
def getDevEUI(tagPathBase):
	
	devEUI = system.tag.readBlocking([tagPathBase+ "/LoRaMetrics/DevEUI"]).value
	return devEUI