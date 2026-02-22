def isResultSuccess(results):
	try:
		if 'messageType' in  results.keys():
			if results['messageType'].upper() == "SUCCESS":
				return True
			else:
				return False
		elif 'status' in results.keys():
			if results['status'].upper() == "SUCCESS":
				return True
			else:
				return False
		else:
			return False
	except Exception as e:
		system.perspective.print("Error determining status: " + str(e))
		return False
		
def getResultMessage(results):
	try:
		if 'message' in  results.keys():
			return results['message']
		else:
			return "Error getting results: " + json.dumps(results)
	except Exception as e:
		return "Error getting results: " + str(e)	
		
def createResults(isSuccessful, message):
	messageType = "SUCCESS"
	if not isSuccessful:
		messageType = "FAILURE"
	result = {'messageType':messageType, "message":message}
	return result