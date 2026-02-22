def getAttributesForTag(rootTagPath):
	tags = system.tag.browse(rootTagPath, filter={"recursive":True})
	return tags
	
	
def getMonitoredTags(monitoredPath):
	tags = system.tag.browse(monitoredPath, filter={"recursive":True, "tagType":"UdtInstance"})
	return tags
	
	
def getTagSourcePath(rootTagPath):
	#used for getting parent description to merge into descriptor
	sourcePath = system.tag.readBlocking(["{0}/parameters.tagPath".format(rootTagPath)])[0].value
	if sourcePath == None:
		##if not found, tag is the source
		return rootTagPath
	return sourcePath
	
def formatRequest(tagPath):
	#system.perspective.print("Formatting request")
	request = {}
	sourcePath = getTagSourcePath(tagPath)
	request["TagPath"] = tagPath
	request['sourceTagPath'] = sourcePath
	return request
	
def getMonitoredTagPath():
	return "[default]PI Integration"