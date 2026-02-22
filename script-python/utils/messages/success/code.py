import time
def showSuccess(successMessage):

	system.perspective.openPopup("success", "Popups/success",  params = {"successText":successMessage})
	time.sleep(3)
	system.perspective.closePopup("success")
