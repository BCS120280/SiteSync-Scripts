def showLoading(loadingID = "loading"):
	##shows the loading, defaultsID to loading if not specified
	system.perspective.openPopup(loadingID, "Popups/loading", showCloseIcon = False, modal=True )
	
def hideLoading(loadingID="loading"):
	##shows the loading, defaultsID to loading if not specified
	system.perspective.closePopup(loadingID)