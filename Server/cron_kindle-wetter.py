#!/usr/bin/python3

#######################################################
### Autor: Nico Hartung <nicohartung1@googlemail.com> #
#######################################################

##############
# Bibliotheken
import os
import datetime
import codecs
import urllib.request  
import json
import untangle
import MySQLdb


###########
# Variablen
WEATHER_URL = "http://api.wunderground.com/api/"
WEATHER_KEY = "abcdef0123456789" # 500 quests per day
CITY = "Münchberg, Bayern, DE"
LATITUDE = "50.192900"
LONGTITUDE = "11.8035702"

PATH = "/root/Scripts"
OUTPUT = "/var/www/html/kindle-weather/weatherdata.png"
SVG_FILE = "%s/cron_kindle-wetter_preprocess.svg" % PATH
SVG_OUTPUT = "%s/cron_kindle-wetter_output.svg" % PATH
TMP_OUTPUT = "%s/cron_kindle-wetter_tmp.png" % PATH

ROOMS = ["Bad", "Wohnzimmer"]

HOMEMATICIP = "192.168.1.66"
DEVICES = 2390,2465,2541 # Wohnzimmer (Temp), Bad (Temp), Garten (Wettersensor)

SQLHOST = "localhost"
SQLUSER = "weatherdata"
SQLPW = "weatherdata"
SQLDB = "weatherdata"
SQLTAB = "homematic"


############
# Funktionen
def _exec(cmd):
    rc = os.system(cmd)
    if (rc != 0):
        print("`%s` failed with error %d" % (cmd, rc))
        exit(rc)

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
# Aktuelle Wetterlage
# http://api.wunderground.com/api/abcdef0123456789/conditions/q/50.192900,11.8035702.json
conditions = urllib.request.urlopen(
    "%s/%s/conditions/q/%s,%s.json" %
    (WEATHER_URL, WEATHER_KEY, LATITUDE, LONGTITUDE))
json_conditions = conditions.read().decode('utf-8')
parsed_conditions = json.loads(json_conditions)


############
# Astronomie
# http://api.wunderground.com/api/abcdef0123456789/astronomy/q/50.192900,11.8035702.json
astronomy = urllib.request.urlopen(
    "%s/%s/astronomy/q/%s,%s.json" %
    (WEATHER_URL, WEATHER_KEY, LATITUDE, LONGTITUDE))
json_astronomy = astronomy.read().decode('utf-8')
parsed_astronomy = json.loads(json_astronomy)


##################
# Wettervorhersage
# http://api.wunderground.com/api/abcdef0123456789/forecast/q/50.192900,11.8035702.json
forecast = urllib.request.urlopen(
    "%s/%s/forecast/q/%s,%s.json" %
    (WEATHER_URL, WEATHER_KEY, LATITUDE, LONGTITUDE))
json_forecast = forecast.read().decode('utf-8')
parsed_forecast = json.loads(json_forecast)
forecast_list = []
for forecast_data in parsed_forecast['forecast']['simpleforecast']['forecastday']: 
    forecast_perday = [ 
        forecast_data['date']['weekday']
            .replace('Monday', 'Montag')
            .replace('Tuesday', 'Dienstag')
            .replace('Wednesday', 'Mittwoch')
            .replace('Thursday', 'Donnerstag')
            .replace('Friday', 'Freitag')
            .replace('Saturday', 'Samstag')
            .replace('Sunday', 'Sonntag'), 
        forecast_data['icon'], 
        forecast_data['high']['celsius'], 
        forecast_data['low']['celsius'] 
    ]
    forecast_list.append(forecast_perday)
    # # 0=today, 1=tomorrow, etc. 
    # forecast_list[1][2] = temp high for tomorrow


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
                    if DEVICE == 2541:
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
                    if DEVICE == 2541:
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
                    if DEVICE == 2541:
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
                    if DEVICE == 2541:
                        gwdtemp = '%.1f' % float(value)

                        if 337.5 <= float(gwdtemp) <= 22.4:
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

                ### Windgeschwindigkeit
                if datapointname.endswith('.WIND_SPEED'):
                    datapointid = DATA['ise_id']
                    datapoint = DATA['name']
                    value = DATA['value']

                    sqlinsert(cursor, DEVICE, datapoint, datapointid, value)

                    # Garten
                    if DEVICE == 2541:
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

    output = output.replace("$TIME", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    output = output.replace("$LOC", str(CITY))
    output = output.replace("$I0", str(parsed_conditions['current_observation']['icon']))
    output = output.replace("$CT", str(gtt))
    output = output.replace("$CHH", str(gth))
    output = output.replace("$CHL", str(gtl))
    output = output.replace("$CL", str(gah))
    output = output.replace("$CAH", str(ghh))
    output = output.replace("$CAL", str(ghl))
    output = output.replace("$CW", str(gws))
    output = output.replace("$CD", str(gwd))
    output = output.replace("$CHW", str(gwh))
    output = output.replace("$AQ", str("1234"))
    output = output.replace("$QL", str("546"))
    output = output.replace("$QH", str("2345"))
    output = output.replace("$CR", str(grr))
    output = output.replace("$D1", str("Heute"))
    output = output.replace("$I1", str(forecast_list[0][1]))
    output = output.replace("$L1", str(forecast_list[0][3]))
    output = output.replace("$H1", str(forecast_list[0][2]))
    output = output.replace("$D2", str("Morgen"))
    output = output.replace("$I2", str(forecast_list[1][1]))
    output = output.replace("$L2", str(forecast_list[1][3]))
    output = output.replace("$H2", str(forecast_list[1][2]))
    output = output.replace("$D3", str(forecast_list[2][0]))
    output = output.replace("$I3", str(forecast_list[2][1]))
    output = output.replace("$L3", str(forecast_list[2][3]))
    output = output.replace("$H3", str(forecast_list[2][2]))
    output = output.replace("$sunrise", str("%s:%s" % (parsed_astronomy['sun_phase']['sunrise']['hour'], parsed_astronomy['sun_phase']['sunrise']['minute'])))
    output = output.replace("$sunset", str("%s:%s" % (parsed_astronomy['sun_phase']['sunset']['hour'], parsed_astronomy['sun_phase']['sunset']['minute'])))

    if ROOM == "Bad":
        ROOM2 = "Wohnzimmer"
        output = output.replace("$ROOM1", str(ROOM1))
        output = output.replace("$ROOM2", str(ROOM2))
        output = output.replace("$BT", str(bat))
        output = output.replace("$BSL", str(btl))
        output = output.replace("$BSH", str(bth))
        output = output.replace("$BH", str(bah))
        output = output.replace("$BBH", str(bhh))
        output = output.replace("$BBL", str(bhl))

    if ROOM == "Wohnzimmer":
        ROOM2 = ""
        output = output.replace("$ROOM1", str(ROOM1))
        output = output.replace("$ROOM2", str(ROOM2))
        output = output.replace("$BT", str(wzt))
        output = output.replace("$BSL", str(wtl))
        output = output.replace("$BSH", str(wth))
        output = output.replace("$BH", str(wzh))
        output = output.replace("$BBH", str(whh))
        output = output.replace("$BBL", str(whl))

    codecs.open(SVG_OUTPUT, "w", encoding="utf-8").write(output)
    _exec("rsvg-convert --background-color=white -o %s %s" % (TMP_OUTPUT, SVG_OUTPUT))
    _exec("pngcrush -c 0 -ow %s 1>/dev/null 2>&1" % TMP_OUTPUT)
    _exec("mv -f '%s' '%s'" % (TMP_OUTPUT, OUTPUT))
    _exec("rm -f '%s'" % SVG_OUTPUT)
