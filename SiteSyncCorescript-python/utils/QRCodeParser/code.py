
def parse( data):
	qrFormat = getQRType(data)
	
	if qrFormat == "LORAALIANCE":
		results = parseLoRa(data)
	elif qrFormat == "SITESYNC":
	    results =parseSiteSync(data)
	elif qrFormat == "VEGA":
		results =parseVega(data)
	else:
		if validateDevEUI(data) == True:
			results = {
						"name":data, 
						"devEUI": data.lower(), 
						"joinEUI":"", 
						"appKey":"", 
						"description":"", 
						"deviceType":"",
						"scanType":"EUI Only"
					}
		else:
			results = {
						"name":"Unknown", 
						"devEUI": "", 
						"joinEUI":"", 
						"appKey":"", 
						"description":data, 
						"deviceType":"",
						"scanType":"Unknown format"
					}
	return results

def setName(devEUI, deviceType):
	if len(devEUI) == 16:
		##set name as sensorType, last 4 characters of devEUI
		return deviceType + "-" + devEUI[-4:]	
	else:
		return devEUI
	

def parseSiteSync(data):
	qrData = data.split(':')
	appKey = qrData[0]
	devEUI = qrData[1]
	deviceType = getDeviceType(qrData[2])
	appEUI = "0000000000000000"
	if len(qrData) > 3:
		appEUI = qrData[3]
		
	j = {
			"name":setName(devEUI, deviceType), 
			"devEUI": devEUI.lower(),
			"joinEUI":appEUI, 
			"appKey":appKey, 
			"description":"", 
			"deviceType":deviceType,
			"scanType":"SiteSync"
		}
	return j
	
	
def parseLoRa(data):
	##parse lora standard
	qrData = data
	qrData = qrData.replace("L0:D0:", "").split(':')
	appEUI = qrData[0]
	devEUI = qrData[1]
	
	j = {
				"name":setName(devEUI, ""), 
				"devEUI": devEUI.lower(), 
				"joinEUI":appEUI, 
				"appKey":"", 
				"description":"", 
				"deviceType":"", 
				"scanType":"LoRa Alliance Standard"
		}
	return j
			
	
def getQRType(data):
	if ":" in data:
		if "L0:D0" in data:
			if data.count(':') > 4:
				return "VEGA"
			else:
				return "LORAALIANCE"
		if data.count(':') >= 2:
			return "SITESYNC"
		
		else:
			return "DEVEUI"
	else:
		return "DEVEUI"	
	
	def parseVega(data):
	##parse lora standard
		qrData = data
		qrData = qrData.replace("L0:D0:", "").split(':')
		appEUI = qrData[0]
		devEUI = qrData[1]
		appKey = qrData[-1]
		
		j = {
					"name":setName(devEUI, ""), 
					"devEUI": devEUI.lower(), 
					"joinEUI":appEUI, 
					"appKey":appKey, 
					"description":"", 
					"deviceType":"",
					"scanType":"Vega"
			}
		return j
	
def validateDevEUI(data):
	if len(data) == 16:
		return True
	else:
		return False

def determineQRContentType(data):
	if ":" in data:
		if "L0:D0" in data:
			if data.count(':') > 4:
				return "VEGA"
			else:
				return "LORAALIANCE"
		else:
			return "SITESYNC"
	else:
		return "DEVEUI"

	
def getDeviceType( decoderString):
	decoderMap = {	'A101' : 'Laird RS191 V2',
						'A102' : 'LoRa Gateway Config',
						'A103' : 'LoRaWAN Network',
						'A104' : 'LoRaWAN Sensor Config',
						'A105' : 'RadioBridge4-20ma',
						'A106' : 'RadioBridgeLevel',
						'A107' : 'SushiPressure',
						'A108' : 'SushiTemperature',
						'A109' : 'SushiVibration',
						'A110' : 'TektelicTracker',
						'A111' : 'TektelicTundra',
						'A113' : 'VoBoGP-1',
						'A112' : 'VegaAir',
						'A100' : 'Abeeway',
						'A000' : 'RadioBridge',
						'A004' : 'Aloxy',
						'A003' : 'Adeunis', 
						'A0111':'TE', 
						"TWTG-Vibration-V3":"TWTGVibration",
						'A115':'RadioBridgeTemperature'
						}
	if decoderString in decoderMap.keys():
				
		decoderString = decoderMap[str(decoderString)]

	return decoderString


def processQRCode(content):
	qr = QRCodeParser()
	qr.parse(content)
	return qr.getParsedData()