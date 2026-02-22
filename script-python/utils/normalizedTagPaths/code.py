import json

def updateNormalizedTagPath(pathID, path, tenantID=1):
	tagPathObject = json.dumps({
				"id":pathID,
		        "tagPathBase": path,
		        "tenantID": tenantID
		    })

	results = system.sitesync.updateStandardizedTagPath(tagPathObject)
	result = json.loads(results)
	return result
	
def createNewTag(tenantID=1):
	tagPathObject = json.dumps({		      
		        "tagPathBase": "",
		        "tenantID": tenantID
		    })

	results = system.sitesync.createStandardizedTagPath(tagPathObject)
	result = json.loads(results)
	return result

def getAllTagPaths():

	results = system.sitesync.listAllStandardizedTagPaths()
	result = json.loads(results)
	return result
	
	
def getTagPathsForTenant(tenantID=1):

	
	results = system.sitesync.listApplicationsByTenant(tenantID)
	result = json.loads(results)
	return result
	
def deleteTagPath(pathID):
	results = system.sitesync.deleteStandardizedTagPath(pathID)
	result = json.loads(results)
	return result
	
	