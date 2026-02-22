"""
Stub file for device module.
This module is provided by the Ignition platform at runtime.
This stub is only for IDE type checking and autocomplete support.
"""


class createDevice:
    """Device creation operations"""

    @staticmethod
    def createDevice(deviceRequest):
        """Create a device"""
        pass

    @staticmethod
    def saveDevice(devEUI, appEUI, appKey, name, serialNumber, deviceTypeID, lat, lon, description, tagProvider, tagPath, param11, param12, appID, tenantID):
        """Save a device"""
        pass

    @staticmethod
    def formatAddDeviceRequest(devEUI, appEUI, appKey, name, serialNumber, tenantID, modelID, lat, lon, description, appID):
        """Format device request"""
        pass


class tagOperations:
    """Tag operations"""

    @staticmethod
    def saveTagPathForDevice(devEUI, tagProvider, tagPath, name):
        """Save tag path for device"""
        pass

    @staticmethod
    def assembleFullPath(tagProvider, tagPath, name):
        """Assemble full tag path"""
        pass

    @staticmethod
    def updateMetaData(tagPathBase, meta):
        """Update metadata"""
        pass


class updateDevice:
    """Device update operations"""

    @staticmethod
    def updateDeviceMetaData(meta, devEUI):
        """Update device metadata"""
        pass
