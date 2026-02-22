def showErrorMessage(errorText):
	system.perspective.openPopup("error", "Popups/error",  params = {"errorText":errorText})
	system.db.runNamedQuery(path= "createLog", parameters = {'message':errorText})
	
def hideErrorMessage(errorText):
	system.perspective.closePopup("error")