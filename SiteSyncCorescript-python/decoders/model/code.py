import json

	
	
def listDeviceProfiles(tenantID):
	items = system.sitesync.listDeviceProfiles(tenantID)
	##format into option/value combos, and mfg model relationships
	if items != None:	
		return json.loads(items)
	else:
		return []
	
	
def findModelIDByName(models, name):
	#{u'external_device_profile_id': u'', u'device_type': u'Pressure', u'decoderID': 1, u'firmware_version': u'v1', u'hardware_version': u'v1', u'manufacturer': u'TESolution', u'model_name': u'TEPressure', u'tenantID': 0,
	#u'device_class': u'CLASS_A', u'id': 1, u'udtID': 1}
	
	for model in models:
		if model['model_name'] == name:
			return model['id']
			
	return -1
	
def findModelNameByID(models, selectedID):
	#{u'external_device_profile_id': u'', u'device_type': u'Pressure', u'decoderID': 1, u'firmware_version': u'v1', u'hardware_version': u'v1', u'manufacturer': u'TESolution', u'model_name': u'TEPressure', u'tenantID': 0,
	#u'device_class': u'CLASS_A', u'id': 1, u'udtID': 1}
	
	for model in models:
		if model['id'] == selectedID:
			return model['model_name']
			
	return -1
	
def getModel(modelID):
	model = system.sitesync.getDeviceProfile(modelID)	
	return json.loads(model)
	
def addModel(tenantID, modelName):

	model = system.sitesync.createDeviceProfile(modelName, tenantID)
	if model != None:	
		return json.loads(model)
	else:
		return None

def copyModel(modelID, modelName):

	model = system.sitesync.copyDeviceProfile(modelID, modelName)
	if model != None:	
		return json.loads(model)
	else:
		return None
	
def updateModel(model):
	m = json.dumps(model)
	results = system.sitesync.updateDeviceProfile(m)
	return json.loads(results)
	
def deleteModel(modelID):
	results = system.sitesync.deleteDeviceProfile(modelID)
	return json.loads(results)
	
	
def getModels(tenantID):
	modelList = system.sitesync.getModels(tenantID)
	if modelList != None:
		return json.loads(modelList)
	else:	
		return []

	