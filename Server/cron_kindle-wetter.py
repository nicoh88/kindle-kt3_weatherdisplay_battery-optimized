#!/usr/bin/python3

#######################################################
### Autor: Nico Hartung <nicohartung1@googlemail.com> #
#######################################################

# Weather Underground API Changes
# https://apicommunity.wunderground.com/weatherapi/topics/weather-underground-api-changes

##############
# Bibliotheken
import logging
import time
import os
import datetime
import locale
import codecs
import urllib.request
import json
import untangle
import MySQLdb


######################
# Deutsches Zeitformat
locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")


###########
# Variablen
WEATHER_URL = "https://api.darksky.net/forecast"
WEATHER_KEY = "aabbccddeeff11223344556677889900"
CITY = "Münchberg, Bayern, DE"
LATITUDE = "50.192900"
LONGTITUDE = "11.8035702"

PATH = "/root/Scripts"
LOG = "log/cron_kindle-wetter.log"
OUTPUT = "/var/www/html/kindle-weather/weatherdata.png"
SVG_FILE = "%s/cron_kindle-wetter_preprocess.svg" % PATH
SVG_OUTPUT = "%s/cron_kindle-wetter_output.svg" % PATH
TMP_OUTPUT = "%s/cron_kindle-wetter_tmp.png" % PATH

ROOMS = ["Bad", "Wohnzimmer"]

HOMEMATICIP = "192.168.1.66"
DEVICES = 2390,2465,7404 # Wohnzimmer (Temp), Bad (Temp), Garten (Wettersensor)

SQLHOST = "localhost"
SQLUSER = "weatherdata"
SQLPW = "weatherdata"
SQLDB = "weatherdata"
SQLTAB = "homematic"


#################
# Protokollierung
logging.basicConfig(
	 filename=PATH + '/' + LOG,
	 level=logging.INFO,
	 #level=logging.WARNING,
	 format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
	 #datefmt='%H:%M:%S'
)
console = logging.StreamHandler()
console.setLevel(logging.ERROR)
logging.getLogger('').addHandler(console)
logger = logging.getLogger(__name__)
logging.info("SCRIPT START")


############
# Funktionen
def _exec(cmd):
	rc = os.system(cmd)
	if (rc != 0):
		print("`%s` failed with error %d" % (cmd, rc))
		exit(rc)

def asInteger(output, id, data, addi):
	output = output.replace(id, str('%.0f%s' % (float(data), addi)))
	return(output)

def asIntegerTenOrMinusTen(output, id, data, addi):
	if float(data) <= -10 or float(data) >= 10:
		output = output.replace(id, str('%.0f%s' % (float(data), addi)))
	else:
		output = output.replace(id, str('%s%s' % (data, addi)))
	return(output)

def replace_daily(output, id, dataday, dataicon, datalow, datahigh, datawind, datarain, datarainint):
	output = output.replace("$D" + id, str(dataday + "."))
	output = output.replace("$I" + id, str(dataicon))
	output = output.replace("$L" + id, str('%.0f%s' % (float(datalow), "°")))
	output = output.replace("$H" + id, str('%.0f%s' % (float(datahigh), "°")))
	output = output.replace("$W" + id, str('%.0f' % (float(datawind))))
	#output = output.replace("$P" + id, str('%.2d' % (float(datarain))))
	output = output.replace("$P" + id, str('%.0f' % (float(datarain))))
	output = output.replace("$M" + id, str('%.1f' % (float(datarainint))))
	return(output)

def replace_hourly(output, id, datatime, dataicon, datarain, datatemp):
	output = output.replace("$K" + id, str(datatime))
	output = output.replace("$J" + id, str(dataicon))
	output = output.replace("$T" + id, str('%.0f%s' % (float(datatemp), "°")))
	if datarain >= 30 or dataicon == "rain":
		output = output.replace("$R" + id, str('%.0f%s' % (float(datarain), "%")))
	else:
		output = output.replace("$R" + id, str(""))
	return(output)

def sqlinsert(cursor, DEVICE, datapoint, datapointid, value):
	sql = "INSERT INTO %s (deviceid, datapointid, datapoint, value) VALUES ('%s', '%s', '%s', '%s')" % (SQLTAB, DEVICE, datapointid, datapoint, value)
	cursor.execute(sql)
	db.commit()

def sqlminmax(cursor, datapointid, sort, decimal):
	cursor.execute(
		"SELECT value FROM %s WHERE datapointid = %s AND DATE(timestamp) = DATE(NOW()) ORDER BY value + 0 %s LIMIT 1" %
		(SQLTAB, datapointid, sort))
	for select in cursor.fetchall():
		#return('%.%sf' % (float(select[0]), decimal))
		return('%.{0}f'.format(decimal) % select[0])


#####################
# API-Abfrage
# https://api.darksky.net/forecast/aabbccddeeff11223344556677889900/50.192900,11.8035702?&units=ca&lang=de
tries = 0
max_tries = 5
while tries < max_tries:
	try:
		apidata = urllib.request.urlopen(
			"%s/%s/%s,%s?&units=ca&lang=de" %
			(WEATHER_URL, WEATHER_KEY, LATITUDE, LONGTITUDE))
		json_apidata = apidata.read().decode('utf-8')
		parsed_apidata = json.loads(json_apidata)
		logging.info("OK | dark sky api quest successfully")


		# Now
		weatherdata_now_text = parsed_apidata['currently']['summary'][:20] + (parsed_apidata['currently']['summary'][20:] and '...')
		weatherdata_now_icon = parsed_apidata['currently']['icon']
		logging.info("- weatherdata_now | summary: %s" % (weatherdata_now_text))
		logging.info("- weatherdata_now | icon: %s" % (weatherdata_now_icon))


		# Astronomie
		astronomy_today_sunrise = datetime.datetime.fromtimestamp(int(parsed_apidata['daily']['data'][0]['sunriseTime'])).strftime("%H:%M")
		astronomy_today_sunset = datetime.datetime.fromtimestamp(int(parsed_apidata['daily']['data'][0]['sunsetTime'])).strftime("%H:%M")
		astronomy_today_moonphase = parsed_apidata['daily']['data'][0]['moonPhase']*100

		if float(astronomy_today_moonphase) <= 2 or float(astronomy_today_moonphase) >= 98:
			astronomy_today_moonphase_icon = "moon-0"
		if float(astronomy_today_moonphase) >= 3 and float(astronomy_today_moonphase) <= 17:
			astronomy_today_moonphase_icon = "moon-waxing-25"
		if float(astronomy_today_moonphase) >= 18 and float(astronomy_today_moonphase) <= 32:
			astronomy_today_moonphase_icon = "moon-waxing-50"
		if float(astronomy_today_moonphase) >= 33 and float(astronomy_today_moonphase) <= 47:
			astronomy_today_moonphase_icon = "moon-waxing-75"
		if float(astronomy_today_moonphase) >= 48 and float(astronomy_today_moonphase) <= 52:
			astronomy_today_moonphase_icon = "moon-100"
		if float(astronomy_today_moonphase) >= 53 and float(astronomy_today_moonphase) <= 67:
			astronomy_today_moonphase_icon = "moon-waning-75"
		if float(astronomy_today_moonphase) >= 68 and float(astronomy_today_moonphase) <= 82:
			astronomy_today_moonphase_icon = "moon-waning-50"
		if float(astronomy_today_moonphase) >= 83 and float(astronomy_today_moonphase) <= 97:
			astronomy_today_moonphase_icon = "moon-waning-25"

		logging.info("- astronomy_today | sunrise: %s, sunset %s" % (astronomy_today_sunrise, astronomy_today_sunset))
		logging.info("- astronomy_today | moonphase_icon: %s, moonphase: %s%%" % (astronomy_today_moonphase_icon, astronomy_today_moonphase))


		# Forecast Daily
		weatherdata_forecast_date = []
		weatherdata_forecast_weekday = []
		weatherdata_forecast_icon = []
		weatherdata_forecast_temphigh = []
		weatherdata_forecast_templow = []
		weatherdata_forecast_wind = []
		weatherdata_forecast_rain = []
		weatherdata_forecast_rainint= []
		for i in range(0, 3):
			weatherdata_forecast_date.append(datetime.datetime.fromtimestamp(int(parsed_apidata['daily']['data'][i]['time'])).strftime("%d.%m."))
			weatherdata_forecast_weekday.append(datetime.datetime.fromtimestamp(int(parsed_apidata['daily']['data'][i]['time'])).strftime("%a"))
			weatherdata_forecast_icon.append(parsed_apidata['daily']['data'][i]['icon'])
			weatherdata_forecast_temphigh.append(parsed_apidata['daily']['data'][i]['temperatureHigh'])
			weatherdata_forecast_templow.append(parsed_apidata['daily']['data'][i]['temperatureLow'])
			weatherdata_forecast_wind.append(parsed_apidata['daily']['data'][i]['windGust'])
			weatherdata_forecast_rain.append(parsed_apidata['daily']['data'][i]['precipProbability']*100)
			weatherdata_forecast_rainint.append(parsed_apidata['daily']['data'][i]['precipIntensityMax'])
			logging.info("- forecast_daily | today: %s, %s, icon: %s, high: %s, low: %s, wind: %s km/h, pop: %s%%, rain: %s mm" % (weatherdata_forecast_weekday[i], weatherdata_forecast_date[i], weatherdata_forecast_icon[i], weatherdata_forecast_temphigh[i], weatherdata_forecast_templow[i], weatherdata_forecast_wind[i], weatherdata_forecast_rain[i], weatherdata_forecast_rainint[i]))


		# Forecast Hourly
		weatherdata_hourly_time = []
		weatherdata_hourly_icon = []
		weatherdata_hourly_temp = []
		weatherdata_hourly_wind = []
		weatherdata_hourly_rain = []
		for i in range(0, 24):
			weatherdata_hourly_time.append(datetime.datetime.fromtimestamp(int(parsed_apidata['hourly']['data'][i]['time'])).strftime("%H"))
			weatherdata_hourly_icon.append(parsed_apidata['hourly']['data'][i]['icon'])
			weatherdata_hourly_temp.append(parsed_apidata['hourly']['data'][i]['temperature'])
			weatherdata_hourly_wind.append(parsed_apidata['hourly']['data'][i]['windGust'])
			weatherdata_hourly_rain.append(parsed_apidata['hourly']['data'][i]['precipProbability']*100)
			logging.info("- weatherdata_hourly | hour: %s, icon: %s, temp: %s, wind: %s km/h, pop: %s%%" % (weatherdata_hourly_time[i], weatherdata_hourly_icon[i], weatherdata_hourly_temp[i], weatherdata_hourly_wind[i], weatherdata_hourly_rain[i]))

	except urllib.error.HTTPError as e:
		tries = tries + 1
		logging.warn("WARN | dark sky api quest not successfully - error <%s> on trial no %s" % (e.code, tries))
		time.sleep(10)
		continue

	else:
		break

else:
	logging.error("FAIL |  dark sky api quest failed")


################
# Homematic CCU2
# http://192.168.1.66/addons/xmlapi/state.cgi?device_id=2390,2465
db = MySQLdb.connect(
	SQLHOST,
	SQLUSER,
	SQLPW,
	SQLDB)
cursor = db.cursor()

for DEVICE in DEVICES:

	xmldoc = untangle.parse(
		"http://%s/addons/xmlapi/state.cgi?device_id=%s" %
		(HOMEMATICIP, DEVICE))

	for ITEMS in xmldoc.state.device.channel:
		if ITEMS.get_elements('datapoint'):
			for DATA in ITEMS.datapoint:
				datapointname = DATA['name']

				### Temperatur
				if datapointname.endswith('.ACTUAL_TEMPERATURE'):
					datapointid = DATA['ise_id']
					datapoint = DATA['name']
					value = DATA['value']

					sqlinsert(cursor, DEVICE, datapoint, datapointid, value)

					# WZ
					if DEVICE == 2390:
						wzt = '%.1f' % float(value)
						wth = sqlminmax(cursor, datapointid, "DESC", 1)
						wtl = sqlminmax(cursor, datapointid, "ASC", 1)

					# Bad
					if DEVICE == 2465:
						bat = '%.1f' % float(value)
						bth = sqlminmax(cursor, datapointid, "DESC", 1)
						btl = sqlminmax(cursor, datapointid, "ASC", 1)

					# Garten
					if DEVICE == 7404:
						gtt = '%.1f' % float(value)
						gth = sqlminmax(cursor, datapointid, "DESC", 1)
						gtl = sqlminmax(cursor, datapointid, "ASC", 1)

				### Luftfeuchtigkeit
				if datapointname.endswith('.HUMIDITY'):
					datapointid = DATA['ise_id']
					datapoint = DATA['name']
					value = DATA['value']

					sqlinsert(cursor, DEVICE, datapoint, datapointid, value)

					# WZ
					if DEVICE == 2390:
						wzh = '%.0f' % float(value)
						whh = sqlminmax(cursor, datapointid, "DESC", 0)
						whl = sqlminmax(cursor, datapointid, "ASC", 0)

					# Bad
					if DEVICE == 2465:
						bah = '%.0f' % float(value)
						bhh = sqlminmax(cursor, datapointid, "DESC", 0)
						bhl = sqlminmax(cursor, datapointid, "ASC", 0)

					# Garten
					if DEVICE == 7404:
						gah = '%.0f' % float(value)
						ghh = sqlminmax(cursor, datapointid, "DESC", 0)
						ghl = sqlminmax(cursor, datapointid, "ASC", 0)

				### Niederschlagsmenge
				# Ohne "Reset" wird die Niederschlagsmenge immer zum letzten Wert addiert - wächst immer weiter an, wird nicht auf 0 gesetzt.
				if datapointname.endswith('.RAIN_COUNTER'):
					datapointid = DATA['ise_id']
					datapoint = DATA['name']
					value = DATA['value']

					sqlinsert(cursor, DEVICE, datapoint, datapointid, value)

					# Garten
					if DEVICE == 7404:
						cursor.execute(
							"SELECT maxi-mini FROM (SELECT MIN(value) mini, MAX(value) maxi FROM (SELECT value FROM %s WHERE datapointid = %s AND timestamp >= NOW() - INTERVAL 1 DAY ) mm1) mm2" %
								(SQLTAB, datapointid))
						for select in cursor.fetchall():
							grr = '%.1f' % float(select[0])

				### Windrichtung
				if datapointname.endswith('.WIND_DIR'):
					datapointid = DATA['ise_id']
					datapoint = DATA['name']
					value = DATA['value']

					sqlinsert(cursor, DEVICE, datapoint, datapointid, value)

					# Garten
					if DEVICE == 7404:
						gwdtemp = '%.1f' % float(value)

						if 0 <= float(gwdtemp) <= 22.4:
							gwd = "N"
						elif 22.5 <= float(gwdtemp) <= 67.4:
							gwd = "NO"
						elif 67.5 <= float(gwdtemp) <= 112.4:
							gwd = "O"
						elif 112.5 <= float(gwdtemp) <= 157.4:
							gwd = "SO"
						elif 157.5 <= float(gwdtemp) <= 202.4:
							gwd = "S"
						elif 202.5 <= float(gwdtemp) <= 247.4:
							gwd = "SW"
						elif 247.5 <= float(gwdtemp) <= 292.4:
							gwd = "W"
						elif 292.5 <= float(gwdtemp) <= 337.4:
							gwd = "NW"
						elif 337.5 <= float(gwdtemp) <= 360:
							gwd = "N"

				### Windgeschwindigkeit
				if datapointname.endswith('.WIND_SPEED'):
					datapointid = DATA['ise_id']
					datapoint = DATA['name']
					value = DATA['value']

					sqlinsert(cursor, DEVICE, datapoint, datapointid, value)

					# Garten
					if DEVICE == 7404:
						gws = '%.1f' % float(value)

						cursor.execute(
							"SELECT value FROM %s WHERE datapointid = %s AND DATE(timestamp) = DATE(NOW()) ORDER BY value + 0 DESC LIMIT 1" %
							(SQLTAB, datapointid))
						for select in cursor.fetchall():
							gwh = '%.0f' % float(select[0])


############################################################
# SVG einlesen, Output zusammensuchen und SVG/PNG generieren
### http://www.svgminify.com > then copy/paste "defs"

for ROOM in ROOMS:

	OUTPUT = "/var/www/html/kindle-weather/weatherdata-%s.png" % (ROOM.lower())
	ROOM1 = "Innen (%s)" % (ROOM)

	output = codecs.open(SVG_FILE, "r", encoding="utf-8").read()

	output = output.replace("$TEXT", str(weatherdata_now_text))
	output = output.replace("$I0", str(weatherdata_now_icon))
	output = asInteger(output, "$CT", gtt, "°")
	output = output.replace("$CHH", str(gth + "°"))
	output = output.replace("$CHL", str(gtl + "°"))
	output = output.replace("$CL", str(gah + ""))
	output = output.replace("$CAH", str(ghh + ""))
	output = output.replace("$CAL", str(ghl + ""))
	output = asInteger(output, "$CW", gws, "")
	output = output.replace("$CD", str(gwd))
	output = output.replace("$CHW", str(gwh))
	output = output.replace("$CR", str(grr))
	output = output.replace("$sunrise", str(astronomy_today_sunrise))
	output = output.replace("$sunset", str(astronomy_today_sunset))
	output = output.replace("$MO", str('%.2d' % (float(astronomy_today_moonphase))))
	output = output.replace("$MI", str(astronomy_today_moonphase_icon))

	output = output.replace("$AQ", str("1234"))
	output = output.replace("$QL", str("546"))
	output = output.replace("$QH", str("2345"))

	output = output.replace("$TIME", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
	output = output.replace("$LOC", str(CITY))

	for i in range(0, 3):
		output = replace_daily(output, str(i+1), weatherdata_forecast_weekday[i], weatherdata_forecast_icon[i], weatherdata_forecast_templow[i], weatherdata_forecast_temphigh[i], weatherdata_forecast_wind[i], weatherdata_forecast_rain[i], weatherdata_forecast_rainint[i])

	for i in range(0, 24):
		output = replace_hourly(output, str(i+1).zfill(2), weatherdata_hourly_time[i], weatherdata_hourly_icon[i], weatherdata_hourly_rain[i], weatherdata_hourly_temp[i])

	if ROOM == "Bad":
		ROOM2 = "Wohnzimmer"
		output = output.replace("$ROOM1", str(ROOM1))
		output = output.replace("$ROOM2", str(ROOM2))
		output = output.replace("$BT", str(bat + "°"))
		output = output.replace("$BSL", str(btl + "°"))
		output = output.replace("$BSH", str(bth + "°"))
		#output = asIntegerTenOrMinusTen(output, "$BSL", btl, "°")
		#output = asIntegerTenOrMinusTen(output, "$BSH", bth, "°")
		output = output.replace("$BH", str(bah + ""))
		output = output.replace("$BBH", str(bhh + ""))
		output = output.replace("$BBL", str(bhl + ""))

	if ROOM == "Wohnzimmer":
		ROOM2 = ""
		output = output.replace("$ROOM1", str(ROOM1))
		output = output.replace("$ROOM2", str(ROOM2))
		output = output.replace("$BT", str(wzt + "°"))
		output = output.replace("$BSL", str(wtl + "°"))
		output = output.replace("$BSH", str(wth + "°"))
		#output = asIntegerTenOrMinusTen(output, "$BSL", wtl, "°")
		#output = asIntegerTenOrMinusTen(output, "$BSH", wth, "°")
		output = output.replace("$BH", str(wzh + ""))
		output = output.replace("$BBH", str(whh + ""))
		output = output.replace("$BBL", str(whl + ""))

	codecs.open(SVG_OUTPUT, "w", encoding="utf-8").write(output)
	#_exec("rsvg-convert --background-color=white -o %s %s" % (TMP_OUTPUT, SVG_OUTPUT))
	_exec("inkscape --without-gui --export-width 600 --export-height 800 --export-background=WHITE --export-png %s %s 1>/dev/null 2>&1" % (TMP_OUTPUT, SVG_OUTPUT))
	_exec("pngcrush -c 0 -ow %s 1>/dev/null 2>&1" % TMP_OUTPUT)
	_exec("mv -f '%s' '%s'" % (TMP_OUTPUT, OUTPUT))
	_exec("rm -f '%s'" % SVG_OUTPUT)

logging.info("SCRIPT END\n")
