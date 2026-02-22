import json

def saveUDT(udtID, udtName, content):
	udt = json.dumps({
	"name":udtName, 
	"content":content, 
	"id":udtID
	})
	result = system.sitesync.updateUDT(udt)
	
	return json.loads(result)
	
	
def listUDTs(tenantID):
	udt = system.sitesync.listUDTs(tenantID)
	return json.loads(udt)

def getUDT(udtID):
	udt = system.sitesync.getUDT(udtID)
	return json.loads(udt)
	
	
	
def generateUDT(decodedResult, udtName):
	results = system.sitesync.generateUDT( udtName, decodedResult)
	return json.loads(results)
	
def createUDT(udtName, tenantID):
	udt = json.dumps({
		"name":udtName, 
		"tenantID":tenantID
		})
	result = system.sitesync.createUDT(udt)
	
	return json.loads(result)