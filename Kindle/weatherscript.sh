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
LOG="$SCRIPTDIR/$NAME.log"
SUSPENDFOR=900                          # Default, flexibel by F5INTWORKDAY and F5INTWEEKEND
NET="wlan0"

LIMG="$SCRIPTDIR/weatherdata.png"
LIMGERR="$SCRIPTDIR/weathererror.png"
LIMGBATT="$SCRIPTDIR/weatherbattery.png"

RSRV="192.168.1.10"
RIMG="$RSRV/kindle-weather/weatherdata.png"
RSH="$RSRV/kindle-weather/$NAME.sh"

ROUTERIP="192.168.1.1"                # Workaround, forget default gateway after STR
#ROUTERIP="192.168.254.254"             # Workaround, forget default gateway after STR
     
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
PLAYSMSPW="abcdef0123456789abcdef0123456789"
PLAYSMSURL="https://192.168.1.10/playsms/index.php"

CONTACTPAGERS="\
0049171XXXXXXX|Nico
0049151XXXXXXXX|Michele"


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
  for LINE in $CONTACTPAGERS; do
    CONTACTPAGER=`echo $LINE | awk -F\| '{print $1}'`
    CONTACTPAGERNAME=`echo $LINE | awk -F\| '{print $2}'`

    SMSTEST=`echo ${MESSAGE} | sed 's/ /%20/g'`
    #curl -s "${SMSURL_START}&text=${SMSTEST}&${SMSURL_END}&to=${CONTACTPAGER}" > /dev/null
    curl -s -k "${PLAYSMSURL}?app=ws&u=${PLAYSMSUSER}&h=${PLAYSMSPW}&op=pv&to=${CONTACTPAGER}&msg=${SMSTEST}" > /dev/null
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | SMS an ${CONTACTPAGERNAME} versendet!"
  done
}


##########
### Skript

### Variables for IFs
NOTIFYBATTERY=0
REFRESHCOUNTER=0

### Kill Kindle processes
kill_kindle

### Loop
while true; do

  ### Start
  echo "================================================"                                            >> $LOG 2>&1

  ### Check Batterystate
  CHECKBATTERY=`gasgauge-info -s`
  echo "`date '+%Y-%m-%d_%H:%M:%S'` | Batteriezustand: $CHECKBATTERY%"                               >> $LOG 2>&1
  if [ ${CHECKBATTERY} -le 5 ] && [ ${NOTIFYBATTERY} -eq 0 ]; then
    NOTIFYBATTERY=1
    if [ ${SMSACTIV} -eq 1 ]; then
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | Batteriezustand kritisch, SMS werden verschickt!"          >> $LOG 2>&1
      MESSAGE="Der Batteriezustand von $HOSTNAME ist kritisch ($CHECKBATTERY) - bitte laden!"
      send_sms
    else
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | Batteriezustand kritisch"                                  >> $LOG 2>&1
    fi
  fi
  if [ ${CHECKBATTERY} -gt 80 ]; then
    NOTIFYBATTERY=0
  fi
  if [ ${CHECKBATTERY} -eq 1 ]; then
    eips -f -g "$LIMGBATT"
    echo "mem" > /sys/power/state
  fi 

  ### Enable CPU Powersave
  CHECKCPUMODE=`cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor | grep -i "powersave"` 
  if [ ${CHECKCPUMODE} -eq 0 ]; then
    echo powersave > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | CPU runtergetaktet"                                          >> $LOG 2>&1
  fi     

  ### Disable Screensaver, no energysaving by powerd   
  # powerd buggy since 5.4.5 - https://www.mobileread.com/forums/showthread.php?t=235821
  CHECKSAVER=`lipc-get-prop com.lab126.powerd status | grep -i "prevent_screen_saver:0"`
  if [ ${CHECKSAVER} -eq 0 ]; then
    lipc-set-prop com.lab126.powerd preventScreenSaver 1                                             >> $LOG 2>&1
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | Standard Energiesparmodus deaktiviert"                       >> $LOG 2>&1
  fi   

  ### Enable WLAN  
  lipc-set-prop com.lab126.wifid enable 1                                                            >> $LOG 2>&1
  
  ### Wait on WLAN
  WLANCOUNTER=0
  while wait_wlan; do
    if [ ${WLANCOUNTER} -gt 30 ]; then
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | Leider kein bekanntes WLAN verfügbar"                      >> $LOG 2>&1
      break
    fi   
    let WLANCOUNTER=WLANCOUNTER+1
    sleep 1
  done

  ### Workaround Default Gateway after STR
  GATEWAY=`ip route | grep default | grep $NET | awk '{print $3}'`
  if [ -z "$GATEWAY" ]; then
    route add default gw $ROUTERIP                                                                   >> $LOG 2>&1
  fi

  ### Check new Script
  # wget (-N) can't https
  LMTIMESH=`stat -c %Y "$SCRIPTDIR/$NAME.sh"`
  curl --silent --time-cond "$SCRIPTDIR/$NAME.sh" --output "$SCRIPTDIR/$NAME.sh" http://$RSH
  RMTIMESH=`stat -c %Y "$SCRIPTDIR/$NAME.sh"`
  if [ $RMTIMESH -gt $LMTIMESH ]; then
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | Skript aktualisiert, Neustart durchführen"                   >> $LOG 2>&1 
    chmod 777 "$SCRIPTDIR/$NAME.sh"
    reboot
    exit
  fi

  ### HOSTNAME & IP
  IP=`ifconfig $NET | grep "inet addr" | cut -d':' -f2 | awk '{print $1}'`
  HOSTNAME=`nslookup $IP | grep Address | grep $IP | awk '{print $4}' | awk -F. '{print $1}'`

  ### Get new Weatherdata
  # wget can't https
  if [ "${HOSTNAME}" = "kindle-kt3-schwarz" ]; then
    RIMG="$RSRV/kindle-weather/weatherdata-bad.png"
  fi
  if [ "${HOSTNAME}" = "kindle-kt3-weiss" ]; then
    RIMG="$RSRV/kindle-weather/weatherdata-wohnzimmer.png"
  fi

  let REFRESHCOUNTER=REFRESHCOUNTER+1
  if curl --silent --output "$LIMG" "http://$RIMG"; then
    if [ ${REFRESHCOUNTER} -ne 5 ]; then 
      eips -g "$LIMG"
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | Wetterbild aktualisiert"                                   >> $LOG 2>&1
    else
      eips -f -g "$LIMG"
      echo "`date '+%Y-%m-%d_%H:%M:%S'` | Wetterbild und E-Ink aktualisiert"                         >> $LOG 2>&1
      REFRESHCOUNTER=0
    fi        
  else
    eips -f -g "$LIMGERR"
    echo "`date '+%Y-%m-%d_%H:%M:%S'` | Wetterbild nicht aktualisiert"                               >> $LOG 2>&1
  fi

  ### Disable WLAN
  # No stable "wakealarm" with enabled WLAN
  lipc-set-prop com.lab126.wifid enable 0                                                            >> $LOG 2>&1
 
  ### Set SUSPENDFOR
  # no regex in if with /bin/sh 
  DAYOFWEEK=`date +%u`  # 1=Monday
  HOURNOW=`date +%H`    # Hour
  # Workdays
  if [ ${DAYOFWEEK} -ge 1 ] && [ ${DAYOFWEEK} -le 5 ]; then
    for LINE in $F5INTWORKDAY; do
      HOURS=`echo $LINE | awk -F\| '{print $1}'`
      echo "${HOURS}" | grep ${HOURNOW} > /dev/null 2>&1
      if [ $? -eq 0 ]; then
        SUSPENDFOR=`echo $LINE | awk -F\| '{print $2}'`
        echo "$SUSPENDFOR"
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | Aufwachintervall auf $SUSPENDFOR gesetzt"                >> $LOG 2>&1
      fi
    done
  fi
  # Weekend
  if [ ${DAYOFWEEK} -ge 6 ] && [ ${DAYOFWEEK} -le 7 ]; then
    for LINE in $F5INTWEEKEND; do
      HOURS=`echo $LINE | awk -F\| '{print $1}'`
      echo "${HOURS}" | grep ${HOURNOW} > /dev/null 2>&1
      if [ $? -eq 0 ]; then
        SUSPENDFOR=`echo $LINE | awk -F\| '{print $2}'`
        echo "`date '+%Y-%m-%d_%H:%M:%S'` | Aufwachintervall auf $SUSPENDFOR gesetzt"                >> $LOG 2>&1
      fi
    done
  fi

  # Set wakealarm
  WAKEUPTIMER=$(( `date +%s` + $SUSPENDFOR ))
  echo "`date '+%Y-%m-%d_%H:%M:%S'` | Aufwachzeitpunkt `date -d @$WAKEUPTIMER '+%Y-%m-%d_%H:%M:%S'`" >> $LOG 2>&1

  echo 0 > /sys/class/rtc/rtc0/wakealarm
  echo $WAKEUPTIMER > /sys/class/rtc/rtc0/wakealarm

  # Go into Suspend to Memory (STR)
  echo "mem" > /sys/power/state

done
