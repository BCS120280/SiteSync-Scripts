def doGet(request, session):

	
	# Build device data directly from tags
	basePath = "[default]GVL"
	folders = system.tag.browse(basePath, filter={"recursive": False})
	
	readPaths = []
	folderNames = []
	for f in folders:
		fp = str(f["fullPath"])
		folderNames.append(str(f["name"]))
		readPaths.extend([
			"%s/latitude" % fp,
			"%s/longitude" % fp,
			"%s/metaData/locationDescription" % fp,
			"%s/battery_percentage" % fp,
			"%s/moving" % fp,
			"%s/LoRaMetrics/MesgTimeStamp" % fp,
			"%s/LoRaMetrics/LastGateway" % fp,
			"%s/TempF" % fp,
		])
	
	deviceJson = "[]"
	if readPaths:
		readings = system.tag.readBlocking(readPaths)
		TAGS_PER = 8  # Changed from 7 to 8 to include TempF
		nowMs = system.date.toMillis(system.date.now())
		STALE_MS = 30 * 60 * 1000
		
		devices = []
		for i, name in enumerate(folderNames):
			o = i * TAGS_PER
			lat     = readings[o + 0].value
			lng     = readings[o + 1].value
			locDesc = readings[o + 2].value or ""
			battPct = readings[o + 3].value or ""
			moving  = readings[o + 4].value or ""
			mesgTs  = readings[o + 5].value
			lastGw  = readings[o + 6].value or ""
			tempF   = readings[o + 7].value  # Added TempF
			
			if lat is None or lng is None:
				continue
			if lat == 0.0 and lng == 0.0:
				continue
			
			lngVal = float(lng)
			if lngVal > 0:
				lngVal = lngVal * -1.0
			
			online = False
			if mesgTs is not None:
				try:
					if hasattr(mesgTs, 'getTime'):
						tsMs = mesgTs.getTime()
					else:
						tsMs = long(mesgTs)
					if tsMs > 0:
						online = (nowMs - tsMs) < STALE_MS
				except:
					pass
			
			devices.append({
				"name": name,
				"lat": float(lat),
				"lng": lngVal,
				"locDesc": locDesc,
				"battery": str(battPct),
				"moving": str(moving).lower() == "true",
				"online": online,
				"gateway": lastGw,
				"tempF": tempF  # Added to device data
			})
		
		import json
		deviceJson = json.dumps(devices)
	
	html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SiteSync Tracker Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, sans-serif; height: 100vh; display: flex; flex-direction: column; }
  
  /* ── Company Header ── */
  .company-header {
    background: linear-gradient(to bottom, #ffffff 0%, #f8f8f8 100%);
    border-bottom: 4px solid #003DA5;
    padding: 15px 30px;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    flex-shrink: 0;
  }
  
  .company-name {
    font-size: 32px;
    font-weight: bold;
    color: #cc0000;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
  }
  
  /* ── Map Container ── */
  #map { 
    flex: 1;
    width: 100%;
    position: relative;
  }
  
  .tracker-popup b { font-size: 14px; }
  .tracker-popup { font-size: 12px; line-height: 1.6; }
  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    color: white;
    font-size: 11px;
    font-weight: bold;
  }
  .status-online { background: #4CAF50; }
  .status-moving { background: #4CAF50; }
  .status-offline { background: #F44336; }
  .legend {
    background: white;
    padding: 10px 14px;
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    font-size: 12px;
    line-height: 2;
  }
  .legend-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
  }
  .info-box {
    background: white;
    padding: 8px 14px;
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    font-size: 13px;
  }
  .refresh-btn {
    background: white;
    border: none;
    padding: 8px 14px;
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    font-size: 13px;
    cursor: pointer;
    font-weight: bold;
  }
  .refresh-btn:hover { background: #f0f0f0; }
</style>
</head>
<body>

<!-- Company Header -->
<div class="company-header">
  <div class="company-name">Garyville Refinery</div>
</div>

<div id="map"></div>
<script>
var devices = DEVICE_DATA_PLACEHOLDER;

// ── Base Layers ──
var worldTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri', maxZoom: 19
});
var worldStreet = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri', maxZoom: 19
});
var worldImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri', maxZoom: 19
});
var worldTerrain = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri', maxZoom: 13
});
var worldShadedRelief = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri', maxZoom: 13
});
var natGeo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri/NatGeo', maxZoom: 16
});
var worldLightGray = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri', maxZoom: 16
});

var baseLayers = {
  "World Topo": worldTopo,
  "World Street": worldStreet,
  "Satellite": worldImagery,
  "Terrain": worldTerrain,
  "Shaded Relief": worldShadedRelief,
  "NatGeo": natGeo,
  "Light Gray": worldLightGray
};

// ── Create Map ──
var map = L.map('map', {
  center: [30.068, -90.600],
  zoom: 15,
  layers: [worldTopo]
});

// ── Layer Control ──
L.control.layers(baseLayers, null, {position: 'topright', collapsed: false}).addTo(map);

// ── Legend ──
var legend = L.control({position: 'bottomright'});
legend.onAdd = function(map) {
  var div = L.DomUtil.create('div', 'legend');
  div.innerHTML = '<b>Tracker Status</b><br>' +
    '<span class="legend-dot" style="background:#4CAF50"></span> Online / Moving<br>' +
    '<span class="legend-dot" style="background:#F44336"></span> Offline';
  return div;
};
legend.addTo(map);

// ── Device Count ──
var onlineCount = devices.filter(function(d) { return d.online; }).length;
var info = L.control({position: 'topleft'});
info.onAdd = function(map) {
  var div = L.DomUtil.create('div', 'info-box');
  div.innerHTML = '<b>' + devices.length + ' Trackers</b><br>' +
    '<span style="color:#4CAF50">' + onlineCount + ' Online</span> &bull; ' +
    '<span style="color:#F44336">' + (devices.length - onlineCount) + ' Offline</span>';
  return div;
};
info.addTo(map);

// ── Refresh Button ──
var refreshCtrl = L.control({position: 'bottomleft'});
refreshCtrl.onAdd = function(map) {
  var btn = L.DomUtil.create('button', 'refresh-btn');
  btn.innerHTML = '&#x21bb; Refresh';
  btn.title = 'Reload tracker positions';
  btn.onclick = function(e) {
    e.stopPropagation();
    window.location.reload();
  };
  return btn;
};
refreshCtrl.addTo(map);

// ── Add Markers ──
var markers = [];
devices.forEach(function(d) {
  var color, statusText, statusClass;
  
  if (!d.online) {
    color = '#F44336';
    statusText = 'Offline';
    statusClass = 'status-offline';
  } else if (d.moving) {
    color = '#4CAF50';
    statusText = 'Moving';
    statusClass = 'status-moving';
  } else {
    color = '#4CAF50';
    statusText = 'Online';
    statusClass = 'status-online';
  }
  
  var icon = L.divIcon({
    html: '<svg width="28" height="36" viewBox="0 0 24 36">' +
      '<path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24C24 5.4 18.6 0 12 0z" ' +
      'fill="' + color + '" stroke="white" stroke-width="1.5"/>' +
      '<circle cx="12" cy="11" r="5" fill="white" opacity="0.9"/></svg>',
    className: '',
    iconSize: [28, 36],
    iconAnchor: [14, 36],
    popupAnchor: [0, -36]
  });
  
  // Build temperature string
  var tempStr = '';
  if (d.tempF !== null && d.tempF !== undefined && d.tempF !== '') {
    tempStr = 'Temp: ' + parseFloat(d.tempF).toFixed(1) + '&deg;F<br>';
  }
  
  var popup = '<div class="tracker-popup">' +
    '<b>' + d.name + '</b><br>' +
    (d.locDesc ? d.locDesc + '<br>' : '') +
    '<span class="status-badge ' + statusClass + '">' + statusText + '</span>' +
    (d.moving ? ' &#x1F6D2;' : '') + '<br>' +
    (d.battery ? 'Battery: ' + d.battery + '%<br>' : '') +
    tempStr +  // Added temperature line here
    (d.gateway ? 'Gateway: ' + d.gateway + '<br>' : '') +
    '<small>Lat: ' + d.lat.toFixed(6) + ', Lng: ' + d.lng.toFixed(6) + '</small>' +
    '</div>';
  
  var marker = L.marker([d.lat, d.lng], {icon: icon})
    .bindPopup(popup)
    .bindTooltip(d.name, {direction: 'top', offset: [0, -36]})
    .addTo(map);
  
  markers.push(marker);
});

// ── Fit map to show all markers ──
if (markers.length > 0) {
  var group = L.featureGroup(markers);
  map.fitBounds(group.getBounds().pad(0.1));
}
</script>
</body>
</html>"""
	
	html = html.replace("DEVICE_DATA_PLACEHOLDER", deviceJson)
	
	return {
		"html": html,
		"contentType": "text/html"
	}