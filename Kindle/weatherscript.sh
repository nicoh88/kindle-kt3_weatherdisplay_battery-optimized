#!/bin/sh

#######################################################
### Autor: Nico Hartung <nicohartung1@googlemail.com> #
#######################################################

###########
### Install
## mkdir /mnt/us/scripts
## chmod 700 /mnt/us/scripts/weatherscript.sh
## mntroot rw
## cp /mnt/us/scripts/weather.conf /etc/upstart/

###########
# Variables
NAME=weatherscript
SCRIPTDIR="/mnt/us/scripts"
LOG="${SCRIPTDIR}/${NAME}.log"
SUSPENDFOR=900                          # Default, flexibel by F5INTWORKDAY and F5INTWEEKEND
NET="wlan0"

LIMG="${SCRIPTDIR}/weatherdata.png"
LIMGBATT="${SCRIPTDIR}/weatherbattery.png"
LIMGERR="${SCRIPTDIR}/weathererror_image.png"
LIMGERRWLAN="${SCRIPTDIR}/weathererror_wlan.png"
LIMGERRNET="${SCRIPTDIR}/weathererror_network.png"

RSRV="192.168.1.10"
RIMG="${RSRV}/kindle-weather/weatherdata.png"
RSH="${RSRV}/kindle-weather/${NAME}.sh"
RPATH="/var/www/html/kindle-weather"

ROUTERIP="192.168.1.1"                # Workaround, forget default gateway after STR

F5INTWORKDAY="\
06,07,08,15,16,17,18,19|900
05,09,10,11,12,13,14,20,21|1800
22,23,00,01,02,03,04|3600"                  # Refreshintervall for workdays = 57 Refreshes per workday

F5INTWEEKEND="\
06,07,08,15,16,17,18,19|900
05,09,10,11,12,13,14,20,21|1800
22,23,00,01,02,03,04|3600"                   # Refreshintervall for weekends = 57 Refreshes per weekend day

SMSACTIV=1
PLAYSMSUSER="admin"
PLAYSMSPW="00998877665544332211ffeeddccbbaa"
PLAYSMSURL="http://192.168.1.10/playsms/index.php"

CONTACTPAGERS="\
0049123456789|Nico
0049987654321|Michele"


##############
### Funktionen
kill_kindle() {
  initctl stop framework    > /dev/null 2>&1      # "powerd_test -p" doesnt work, other command found
  initctl stop cmd          > /dev/null 2>&1
  initctl stop phd          > /dev/null 2>&1
  initctl stop volumd       > /dev/null 2>&1
  initctl stop tmd          > /dev/null 2>&1
  initctl stop webreader    > /dev/null 2>&1
  killall lipc-wait-event   > /dev/null 2>&1
  #initctl stop powerd      > /dev/null 2>&1      # battery state doesnt work
  #initctl stop lab126      > /dev/null 2>&1      # wlan interface doesnt work
  #initctl stop browserd    > /dev/null 2>&1      # not exist 5.9.4
  #initctl stop pmond       > /dev/null 2>&1      # not exist 5.9.4
}

wait_wlan() {
  return `lipc-get-prop com.lab126.wifid cmState | grep CONNECTED | wc -l`
}

send_sms () {
  for LINE in ${CONTACTPAGERS}; do
    CONTACTPAGER=`echo ${LINE} | awk -F\| '{print $1}'`
    CONTACTPAGERNAME=`echo ${LINE} | awk -F\| '{print $2}'`

    SMSTEST=`echo ${MESSAGE} | sed 's/ /%20/g'`
    #curl --silent --insecure "${PLAYSMSURL}?app=ws&u=${PLAYSMSUSER}&h=${PLAYSMSPW}&op=pv&to=${CONTACTPAGER}&msg=${SMSTEST}" > /dev/null
    curl --silent "${PLAYSMSURL}?app=ws&u=${PLAYSMSUSER}&h=${PLAYSMSPW}&op=pv&to=${CONTACTPAGER}&msg=${SMSTEST}" > /dev/null
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | SMS an ${CONTACTPAGERNAME} versendet!" >> ${LOG} 2>&1
  done
}


##########
### Skript

### Variables for IFs
NOTIFYBATTERY=0
REFRESHCOUNTER=0

IP=`ifconfig ${NET} | grep "inet addr" | cut -d':' -f2 | awk '{print $1}'`
HOSTNAME=`nslookup ${IP} | grep Address | grep ${IP} | awk '{print $4}' | awk -F. '{print $1}'`
if [ -z "${HOSTNAME}" ]; then
  HOSTNAME="recently-reboot"
fi

### Kill Kindle processes
kill_kindle

### Loop
while true; do

  ### Start
  echo "================================================" >> ${LOG} 2>&1

  ### Enable CPU Powersave
  CHECKCPUMODE=`cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor | grep -i "powersave"`
  if [ ${CHECKCPUMODE} -eq 0 ]; then
    echo powersave > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | CPU runtergetaktet." >> ${LOG} 2>&1
  fi

  ### Disable Screensaver, no energysaving by powerd
  # powerd buggy since 5.4.5 - https://www.mobileread.com/forums/showthread.php?t=235821
  CHECKSAVER=`lipc-get-prop com.lab126.powerd status | grep -i "prevent_screen_saver:0"`
  if [ ${CHECKSAVER} -eq 0 ]; then
    lipc-set-prop com.lab126.powerd preventScreenSaver 1 >> ${LOG} 2>&1
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Standard Energiesparmodus deaktiviert." >> ${LOG} 2>&1
  fi

  ### Check Batterystate
  CHECKBATTERY=`gasgauge-info -s`
  echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Batteriezustand: ${CHECKBATTERY}%" >> ${LOG} 2>&1
  if [ ${CHECKBATTERY} -gt 80 ]; then
    NOTIFYBATTERY=0
  fi
  if [ ${CHECKBATTERY} -le 1 ]; then
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Batteriezustand 1%, statisches Batteriezustandsbild gesetzt, WLAN deaktivert, Ruhezustand!" >> ${LOG} 2>&1
    eips -f -g "${LIMGBATT}"
    lipc-set-prop com.lab126.wifid enable 0
    echo 0 > /sys/class/rtc/rtc0/wakealarm
    echo "mem" > /sys/power/state
  fi

  ### Set SUSPENDFOR
  # no regex in if with /bin/sh
  DAYOFWEEK=`date +%u`  # 1=Monday
  HOURNOW=`date +%H`    # Hour
  # Workdays
  if [ ${DAYOFWEEK} -ge 1 ] && [ ${DAYOFWEEK} -le 5 ]; then
    for LINE in ${F5INTWORKDAY}; do
      HOURS=`echo ${LINE} | awk -F\| '{print $1}'`
      echo "${HOURS}" | grep ${HOURNOW} > /dev/null 2>&1
      if [ $? -eq 0 ]; then
        SUSPENDFOR=`echo ${LINE} | awk -F\| '{print $2}'`
        echo "${SUSPENDFOR}"
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Aufwachintervall für den nächsten Ruhezustand auf ${SUSPENDFOR} gesetzt." >> ${LOG} 2>&1
      fi
    done
  fi
  # Weekend
  if [ ${DAYOFWEEK} -ge 6 ] && [ ${DAYOFWEEK} -le 7 ]; then
    for LINE in ${F5INTWEEKEND}; do
      HOURS=`echo ${LINE} | awk -F\| '{print $1}'`
      echo "${HOURS}" | grep ${HOURNOW} > /dev/null 2>&1
      if [ $? -eq 0 ]; then
        SUSPENDFOR=`echo ${LINE} | awk -F\| '{print $2}'`
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Aufwachintervall für den nächsten Ruhezustand auf ${SUSPENDFOR} gesetzt." >> ${LOG} 2>&1
      fi
    done
  fi

  ### Calculation WAKEUPTIMER
  WAKEUPTIMER=$(( `date +%s` + ${SUSPENDFOR} ))
  echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Aufwachzeitpunkt für den nächsten Ruhezustand `date -d @${WAKEUPTIMER} '+%Y-%m-%d_%H:%M:%S'`." >> ${LOG} 2>&1

  ### Enable WLAN
  lipc-set-prop com.lab126.wifid enable 1 >> ${LOG} 2>&1
  echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | WLAN aktivieren." >> ${LOG} 2>&1

  ### Wait on WLAN
  WLANNOTCONNECTED=0
  WLANCOUNTER=0
  while wait_wlan; do
    if [ ${WLANCOUNTER} -gt 30 ]; then
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Leider kein bekanntes WLAN verfügbar." >> ${LOG} 2>&1
      eips -f -g "${LIMGERRWLAN}"
      WLANNOTCONNECTED=1
      break
    fi
    let WLANCOUNTER=WLANCOUNTER+1
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Warte auf WLAN (Versuch ${WLANCOUNTER})." >> ${LOG} 2>&1
    sleep 1
  done

  ### Connected with WLAN?
  if [ ${WLANNOTCONNECTED} -eq 0 ]; then

    ### Workaround Default Gateway after STR
    GATEWAY=`ip route | grep default | grep ${NET} | awk '{print $3}'`
    if [ -z "${GATEWAY}" ]; then
      route add default gw ${ROUTERIP} >> ${LOG} 2>&1
    fi

    ### Batterystate critical? SMS!
    if [ ${CHECKBATTERY} -le 5 ] && [ ${NOTIFYBATTERY} -eq 0 ]; then
      NOTIFYBATTERY=1
      if [ ${SMSACTIV} -eq 1 ]; then
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Batteriezustand kritisch, SMS werden verschickt!" >> ${LOG} 2>&1
        MESSAGE="Der Batteriezustand von ${HOSTNAME} ist kritisch (${CHECKBATTERY}%) - bitte laden!"
        send_sms
      else
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Batteriezustand kritisch." >> ${LOG} 2>&1
      fi
    fi

    ### Check new Script
    # wget (-N) can't https
    RSTATUSSH=`curl --silent --head "http://${RSH}" | head -n 1 | cut -d$' ' -f2`
    if [ ${RSTATUSSH} -eq 200 ]; then
      LMTIMESH=`stat -c %Y "${SCRIPTDIR}/${NAME}.sh"`
      curl --silent --time-cond "${SCRIPTDIR}/${NAME}.sh" --output "${SCRIPTDIR}/${NAME}.sh" "http://${RSH}"
      RMTIMESH=`stat -c %Y "${SCRIPTDIR}/${NAME}.sh"`
      if [ ${RMTIMESH} -gt ${LMTIMESH} ]; then
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Skript aktualisiert, Neustart durchführen." >> ${LOG} 2>&1
        chmod 777 "${SCRIPTDIR}/${NAME}.sh"
        reboot
        exit
      fi
    else
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Skript nicht gefunden (HTTP-Status ${RSTATUSSH})." >> ${LOG} 2>&1
    fi

    ### Get new Weatherdata
    # wget can't https
    if [ "${HOSTNAME}" = "kindle-kt3-schwarz" ]; then
      RIMG="${RSRV}/kindle-weather/weatherdata-bad.png"
    fi
    if [ "${HOSTNAME}" = "kindle-kt3-weiss" ]; then
      RIMG="${RSRV}/kindle-weather/weatherdata-wohnzimmer.png"
    fi

    let REFRESHCOUNTER=REFRESHCOUNTER+1
    RSTATUSIMG=`curl --silent --head "http://${RIMG}" | head -n 1 | cut -d$' ' -f2`
    if [ ${RSTATUSIMG} -eq 200 ]; then
      curl --silent --output "$LIMG" "http://${RIMG}"
      if [ ${REFRESHCOUNTER} -ne 5 ]; then
        eips -g "$LIMG"
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Wetterbild aktualisiert." >> ${LOG} 2>&1
      else
        eips -f -g "$LIMG"
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Wetterbild und E-Ink aktualisiert." >> ${LOG} 2>&1
        REFRESHCOUNTER=0
      fi
    elif [ -z "${RSTATUSIMG}" ]; then
        eips -f -g "$LIMGERRNET"
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Webserver reagiert nicht. Webserver läuft? Server erreichbar? Kindle mit dem WLAN verbunden?" >> ${LOG} 2>&1
    else
        eips -f -g "$LIMGERR"
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Wetterbild auf Webserver nicht gefunden (HTTP-Status ${RSTATUSSH})." >> ${LOG} 2>&1
    fi

    ### Copy log by ssh
    cat ${LOG} | ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /mnt/us/scripts/id_rsa_kindle -l kindle ${RSRV} "cat >> ${RPATH}/${NAME}_${HOSTNAME}.log" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      rm ${LOG}
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Log per SSH an Remote-Server übergeben und lokal gelöscht." >> ${LOG} 2>&1
    else
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Log konnte nicht an den Remote-Server übergeben werden." >> ${LOG} 2>&1
    fi

  fi

  ### Disable WLAN
  # No stable "wakealarm" with enabled WLAN
  lipc-set-prop com.lab126.wifid enable 0
  echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | WLAN deaktivieren." >> ${LOG} 2>&1

  ### Set wakealarm
  echo 0 > /sys/class/rtc/rtc0/wakealarm
  echo ${WAKEUPTIMER} > /sys/class/rtc/rtc0/wakealarm

  ### Go into Suspend to Memory (STR)
  echo "`date '+%Y-%m-%d_%H:%M:%S'` | ${HOSTNAME} | Ruhezustand starten." >> ${LOG} 2>&1
  echo "mem" > /sys/power/state

done
