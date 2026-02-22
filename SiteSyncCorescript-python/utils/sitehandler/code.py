import json
def getSitesDropdown():
	options = []
	try:
		tenants = system.sitesync.listTenants()
		t = json.loads(tenants)
		
		
		for tenant in t:
			j = {"label":tenant['tenantName'], "value": tenant['id']}

			options.append(j)
	except Exception as e:
		system.perspective.print(e)
		
	return options
	
def getSites():
	tenants = system.sitesync.listTenants()
	if tenants != None:
		return json.loads(tenants)
	else:
		return []
	
def createSite():
	today = system.date.now()
	formattedDate = system.date.format(today, "yyyy-MM-dd_HHmmss")
	name = "newSite_" + formattedDate
	tenant = system.sitesync.createTenant(name)
	
	if tenant != None:
			import json
			tenant = json.loads(tenant)
			tenantID = tenant['id']
			return tenantID
	else:
		utils.messages.errors.showErrorMessage("Error creating new tenant")
	return False
	
def deleteSite(siteID):
	results = system.sitesync.removeTenant(int(siteID))
	if results != None:
		results = json.loads(results)
	else:
		results = utils.resultParser.createResults(False, "Update returned nothing, check that module is running")
	return results
	
	
def updateSite(siteID, notes, primaryRegion, name):
	t = json.dumps({
		  "id": siteID,
		  "isApplication": 0,
		  "notes": notes,
		  "primaryRegion": primaryRegion,
		  "tenantName": name
		})
	result = system.sitesync.updateTenant(t)
	if result != None:
		result = json.loads(result)
	else:
		result = utils.resultParser.createResults(False, "Update returned nothing, check that module is running")
		
	return result

def updateSiteRoles(siteID, rolesJSON):
	r = json.dumps(rolesJSON)
	system.sitesync.updateTenantRoles(r, int(siteID))