
# kindle-kt3_weatherdisplay_battery-optimized

## Kindle KT3 als Wetterstation

Gleich erst mal zu Beginn: 
Schlagt es euch gleich erst mal aus dem Kopf, wenn ihr denkt, ihr haut das Skript auf einen Server im LAN und die Dateien auf das Kindle, fertig. So wird das nichts! Die beiden Skripts, vor allem aber `cron_kindle-wetter.py` (Server), welches für die Erstellung der PNG-Datei verantwortlich ist, ist extrem auf meine Bedürfnisse angepasst und muss von euch, an eure Geräte und Bedürfnisse, angepasst werden. 

Ohne Basic-Kenntnisse im Skripting: FINGER WEG!

<img src="https://raw.githubusercontent.com/nicoh88/kindle-kt3_weatherdisplay_battery-optimized/master/README.jpg" style="border:1px solid lightgray" alt="Zwei Kindle KT3 als Wetterstation">

## Batterie / Akku

Das Kindle-Skript `weatherscript.sh` ist auf möglichst lange Akkulaufzeit optimiert!

* Kindle Dienste werden beendet.
* CPU wird in den "Powersave-Mode" versetzt.
* WLAN nur kurz aktiv.
* E-INK-Display wird nicht immer vollständig aktualisiert.
* Individuellen Aufwachintervall nach Wochentag und Stunde.
* Suspend-to-RAM / Suspend-to-Memory (STR).

In der aktuellen Konfiguration (57 Änderungen am Tag) hält der Akku des KT3 **ca. 30-35 Tage**.


## Vorbereitungen

Natürlich ist es keine Standardfunktionalität, das Wetter auf einem Kindle als Bildschirmschoner anzeigen zu lassen, aus diesem Grund muss das Kindle gejailbreakt und SSH aktiviert werden.

**Ein paar Fakten:**
* Jailbreak funktioniert nur, wenn sich auf dem Kindle eine Firmware 5.8.7 oder älter befindet.
* Jailbreak muss "persistend" / "dauerhaft" gemacht werden.
  - Firmware-Updates (nicht OTA > BIN-Datei per USB) können eingespielt werden - der Jailbreak bleibt, nach aktuellem Stand (2018-03-08 | Firmware 5.9.4) weiterhin bestehen.
  - Es könnte aber mit jeder neueren Version Schluss sein - also Obacht und vorher in der [Community](https://www.mobileread.com/forums/forumdisplay.php?f=150) informieren!
* USB-Networking (usbnet) muss installiert werden, um dann über ein paar Anpassungen der Konfigurationsdateien (Kindle-Laufwerk) SSH zu aktivieren.

**Übliche Fragen:**
- [Welchen Kindle (Typ) habe ich?](https://wiki.mobileread.com/wiki/Kindle_Serial_Numbers)
- [Wie jailbreake ich mein Kindle?](https://wiki.mobileread.com/wiki/5_x_Jailbreak)

**Fragen zum Jailbreak werden von mir nicht beantwortet!**


## Funktionsweise / Logik / Features

Auf einem Server im LAN, sucht sich das Skript `cron_kindle-wetter.py`, bei mir alle 10 Minuten, die Wetterdaten zusammen.

* Innenraumtemperaturen und Luftfeuchten holt es sich aus meiner HomeMatic CCU2 ([XML-API Addon](https://www.homematic-inside.de/software/xml-api)) von zwei [HmIP-STH](https://www.amazon.de/Homematic-IP-Temperatur-Luftfeuchtigkeitssensor-150181A1/dp/B01MQECR9R/ref=as_li_ss_tl?_encoding=UTF8&psc=1&refRID=X07WWNTM8YPT09RJ0JJX&linkCode=ll1&tag=logdemacosxli-21&linkId=2675c7ae97bda525ebb2694284611493). Zusätzlich werden die Werte in eine MySQL-Datenbank geschrieben, damit ich die MIN- / MAX-Werte anzeigen kann.
  - Warum zwei [HmIP-STH](https://www.amazon.de/Homematic-IP-Temperatur-Luftfeuchtigkeitssensor-150181A1/dp/B01MQECR9R/ref=as_li_ss_tl?_encoding=UTF8&psc=1&refRID=X07WWNTM8YPT09RJ0JJX&linkCode=ll1&tag=logdemacosxli-21&linkId=2675c7ae97bda525ebb2694284611493)? Ich unterscheide, aufgrund von einem Kindle KT3 im Bad (Schwarz) und einen im Wohnzimmer (Weiß), zwischen Bad und Wohnzimmer. Es werden auch zwei, geringfügig unterschiedliche PNGs erzeugt.
* Luftqualität ist aktuell noch hart codiert, da mir hier noch der passende Sensor fehlt.
* Bezeichnung der aktuellen Wetterlage (sunny, rain, etc.) holt es sich über die "Weather Underground API".
* Außentemperatur, Luftfeuchte, Windgeschwindigkeit, -Richtung und Regenmenge holt er sich aus meiner HomeMatic CCU2 ([XML-API Addon](https://www.homematic-inside.de/software/xml-api)) von einem [HmIP-SWO-PR](https://www.amazon.de/Homematic-IP-Wettersensor-Pro-151821A0/dp/B07589Q8FH/ref=as_li_ss_tl?s=diy&ie=UTF8&qid=1521926725&sr=1-1&keywords=hmip%20swo%20pro&linkCode=ll1&tag=logdemacosxli-21&linkId=865a8f2b0656b22db5582e7592e85f7e). Zusätzlich werden die Werte in eine MySQL-Datenbank geschrieben, damit ich die MIN- / MAX-Werte anzeigen kann.
* 3-Tages-Vorhersage holt es sich über die "Weather Underground API".
* Sonnenauf- und Sonnenuntergang holt es sich auch über die WU API.

Hat der Server alle Wetterdaten zusammen, lädt er sich die SVG-Datei `cron_kindle-wetter_preprocess.svg` und tauscht die für den Bereich definierten Variablen mit den echten und aktuellen Wetterdaten aus. Hier werden durch eine Logik sogar zwei Dateien `weatherdata-bad.png` und `weatherdata-wohnzimmer.png` erzeugt, welche dann im Webserver-Verzeichnis, des Servers, abgelegt werden.

<img src="https://raw.githubusercontent.com/nicoh88/kindle-kt3_weatherdisplay_battery-optimized/master/Kindle/weatherdata-wohnzimmer.png" style="border:1px solid lightgray" width="300">&nbsp;&nbsp;&nbsp;<img src="https://raw.githubusercontent.com/nicoh88/kindle-kt3_weatherdisplay_battery-optimized/master/Kindle/weatherdata-bad.png" style="border:1px solid lightgray" width="300">

Das Skript `weatherscript.sh` gehört auf das Kindle, bei mir `/mnt/us/scripts/`. Dieses Skript startet in der Regel 60 Sekunden nach dem Starten des Kindles und beendet dann erst mal alle Kindle üblichen Dienste, um Ressourcen / Akkukapazität zu sparen. Dann läuft das Skript in eine Schleife, die dauerhaft, immer und immer wieder, abgearbeitet wird. Pausiert wird das Skript durch ein STR (Suspend-to-RAM/ Suspend-to-Memory). Vor dem STR wird noch ein Wecker gestellt, der der Kindle-Hardware sagt, wann das Kindle wieder aufwachen soll. Dann, wenn der Wecker klingelt, läuft das Skript weiter, führt ein paar Befehle aus, holt sich das neue PNG mit den Wetterinformationen und verabschiedet sich für einen dynamischen Intervall wieder in den STR.

* Beendet unwichtige Kindle Dienste.
* Prüft den Batteriestatus.
  * ... wenn 5% oder weniger, bekomme ich und meine Frau eine SMS.
  * ... bei 1% wird ein statisches Bild mit "battery low" geladen.
    * ... das Bild wird so lange angezeigt, bis das Kindle am Strom angeschlossen wird und über Powertaste wieder aufgeweckt wird.
* CPU wird runtergetackte und in den "Powersave-Mode" versetzt.
* Standard Bildschirmschoner wird deaktiviert.
* WLAN wird aktiviert.
  * ... es wird gewartet, bis eine WLAN-Verbindung aufgebaut wurde.
* Standard-Gateway wird erneut gesetzt (Workaround).
* Hostname und IP-Adresse wird ermittelt.
  * ... je nach Hostname wird nun ein bestimmtes PNG-Bild von meinem Webserver geladen (welches von `cron_kindle-wetter.py` erzeugt wurde).
* Das PNG-Bild wird jetzt auf dem E-INK Display angezeigt.
  * ... nur bei jedem fünften Mal wird eine Komplettaktualisierung des Displays gemacht.
  * ... alle anderen Male nur eine Teilaktualisierung (dadurch können Schatten entstehen).
* WLAN wird deaktiviert.
* Aufwachintervall wird gesetzt, siehe `F5INTWORKDAY` und `F5INTWEEKEND`.
  * ... an einem Wochentag um 1 Uhr, egal wie viele Minuten, wird der Aufwachintervall auf 3600 Sekunden gesetzt, also eine Stunde.
  * ... an einem Wochentag um 15 Uhr wird der Aufwachintervall auf 900 Sekunden gesetzt, also 15 Minuten.
  * ... am Wochenende ...
* Suspend-to-RAM / Suspend-to-Memory (STR) wird ausgeführt.


## Installation

### Server

* Variablen im Skript `cron_kindle-wetter.py` anpassen, ggf. das ganze Skript.
* Skript `cron_kindle-wetter.py` und SVG `cron_kindle-wetter_preprocess.svg` übertragen.
* Skript ausführbar machen `chmod 744 cron_kindle-wetter.py`.
* Skript regelmäßig über Crontab ausführen.

### Kindle

* Variablen im Skript `weatherscript.sh` anpassen, ggf. das ganze Skript.
* Skript `weatherscript.sh`, Upstart-Datei `weather.conf` und die 5 PNGs auf Kindle übertragen - bei mir `/mnt/us/scripts/`.
* Skript ausführbar machen `chmod 744 weatherscript.sh`.
* Upstart-Datei kopieren, vorher Kindle-Filesystem schreibbar machen `mntroot rw && cp /mnt/us/scripts/wetter.conf /etc/upstart/wetter.conf`
* Nach einem Neustart des Kindles dauert es nun 60 Sekunden, bis das Skript `weatherscript.sh` startet und das PNG anzeigt.

#### Info

Wenn ihr Mal mehr Zeit in der üblichen Kindle-UI benötigt oder es euch nicht mehr gefällt, startet das Kindle neu - ca. 20-30 Sekunden Powertaste drücken. Wenn auf dem Boot-Screen, im Fortschrittsbalken, noch ca. 1cm fehlen, kann man per SSH auf das Kindle zugreifen und mit `kill` den `sleep` und das `weatherscript.sh` beenden oder die Upstart-Datei `/etc/upstart/wetter.conf` löschen und so den Autostart zukünftig verhindern. SCHNELL, MAN HAT NUR 60 SEKUNDEN ZEIT!


## Versionsverlauf

2018-03-24 - Skripts veröffentlicht


## Lizenz

The MIT License (MIT)

Copyright (c) 2018 Nico Hartung

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

