def getTagProviders():
	tags=system.tag.browse(filter={"tagType":"Provider"}).results
	a=[]
	notSyncable = ["SiteSync", "MQTT Engine", "MQTT Transmission", "System"]
	for result in tags:
		tagProvider = str(result['fullPath']).replace("]", "").replace("[", "")
		if tagProvider in notSyncable:
			continue
		else:
			providers={"label":tagProvider, "value":tagProvider}
			a.append(providers)
	return a 
	
