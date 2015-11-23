'''
    3D Enabler [for] LG TV - addon for Kodi to enable 3D mode
    Copyright (C) 2014  Pavel Kuzub
    Copyright (C) 2015  Dennis Koot

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import sys
import xbmc
import xbmcgui
import xbmcaddon
import simplejson
import re
import urllib2
from xml.dom.minidom import parseString
import base64
import uuid
import select

__addon__   = xbmcaddon.Addon()
libs = os.path.join(__addon__.getAddonInfo('path'), 'lib')
sys.path.append(libs)
libs = os.path.join(__addon__.getAddonInfo('path'), 'lib/libLGTV_serial')
sys.path.append(libs)
libs = os.path.join(__addon__.getAddonInfo('path'), 'lib/serial')
sys.path.append(libs)

from libLGTV_serial import LGTV
import serial

class Settings(object):
    def __init__(self):
#        xbmc.log('3D> Settings.__init__()', xbmc.LOGNOTICE)
        self.enabled         = True
        self.tvname          = ''
        self.notifications   = True
        self.notifymessage   = ''
        self.authCount       = 0
        self.pollCount       = 0
        self.curTVmode       = 0
        self.newTVmode       = 0
        self.pollsec         = 5
        self.idlesec         = 5
        self.inProgress      = False
        self.inScreensaver   = False
        self.addonname       = __addon__.getAddonInfo('name')
        self.icon            = __addon__.getAddonInfo('icon')
        self.TVserialport    = '/dev/ttyS0'
        self.TVcmd3Dou       = 'xt 0 0 0 0 0'
        self.TVcmd3Dsbs      = 'xt 0 0 1 0 0'
        self.TVcmd3Dnone     = 'xt 0 1 0 0 0'
        self.load()

    def getSetting(self, name, dataType = str):
#        xbmc.log('3D> Settings.getSetting()', xbmc.LOGNOTICE)
        value = __addon__.getSetting(name)
        if dataType == bool:
            if value.lower() == 'true':
                value = True
            else:
                value = False
        elif dataType == int:
            value = int(value)
        else:
            value = str(value)
#        xbmc.log('3D> getSetting:' + str(name) + '=' + str(value), xbmc.LOGNOTICE)
        return value

    def setSetting(self, name, value):
#        xbmc.log('3D> Settings.setSetting()', xbmc.LOGNOTICE)
        if type(value) == bool:
            if value:
                value = 'true'
            else:
                value = 'false'
        else:
            value = str(value)
#        xbmc.log('3D> setSetting:' + str(name) + '=' + str(value), xbmc.LOGNOTICE)
        __addon__.setSetting(name, value)

    def getLocalizedString(self, stringid):
#        xbmc.log('3D> Settings.getLocalizedString()', xbmc.LOGNOTICE)
        return __addon__.getLocalizedString(stringid)

    def load(self):
#        xbmc.log('3D> Settings.load()', xbmc.LOGNOTICE)
        self.enabled            = self.getSetting('enabled', bool)
        self.tvname             = self.getSetting('tvname', str)
        self.notifications      = self.getSetting('notifications', bool)
        self.curTVmode          = self.getSetting('curTVmode', int)
        self.pollsec            = self.getSetting('pollsec', int)
        self.idlesec            = self.getSetting('idlesec', int)
        self.TVserialport       = self.getSetting('TVserialport', str)
        self.TVcmd3Dou          = self.getSetting('TVcmd3Dou', str)
        self.TVcmd3Dsbs         = self.getSetting('TVcmd3Dsbs', str)
        self.TVcmd3Dnone        = self.getSetting('TVcmd3Dnone', str)

def toNotify(message):
#    xbmc.log('3D> toNotify()', xbmc.LOGNOTICE)
    if len(settings.notifymessage) == 0:
        settings.notifymessage = message
    else:
        settings.notifymessage += '. ' + message

def notify(timeout = 5000):
#    xbmc.log('3D> notify()', xbmc.LOGNOTICE)
    if len(settings.notifymessage) == 0:
        return
    if settings.notifications:
        xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(settings.addonname, settings.notifymessage, timeout, settings.icon))
#    xbmc.log('3D> NOTIFY: ' + settings.notifymessage, xbmc.LOGNOTICE)
    settings.notifymessage = ''

def getStereoscopicMode():
#    xbmc.log('3D> getStereoscopicMode()', xbmc.LOGNOTICE)
    query = '{"jsonrpc": "2.0", "method": "GUI.GetProperties", "params": {"properties": ["stereoscopicmode"]}, "id": 1}'
    result = xbmc.executeJSONRPC(query)
    json = simplejson.loads(result)
#    xbmc.log('3D> Received JSON response: ' + str(json), xbmc.LOGNOTICE)
    ret = 'unknown'
    if json.has_key('result'):
        if json['result'].has_key('stereoscopicmode'):
            if json['result']['stereoscopicmode'].has_key('mode'):
                ret = json['result']['stereoscopicmode']['mode'].encode('utf-8')
    # "off", "split_vertical", "split_horizontal", "row_interleaved"
    # "hardware_based", "anaglyph_cyan_red", "anaglyph_green_magenta", "monoscopic"
    return ret

def getTranslatedStereoscopicMode():
#    xbmc.log('3D> getTranslatedStereoscopicMode()', xbmc.LOGNOTICE)
    mode = getStereoscopicMode()
#    xbmc.log('3D> getTranslatedStereoscopicMode: ' + str(mode), xbmc.LOGNOTICE)
    if mode == 'split_horizontal': return 1
    elif mode == 'split_vertical': return 2
    else: return 0

def stereoModeHasChanged():
#    xbmc.log('3D> stereoModeHasChanged()', xbmc.LOGNOTICE)
    if settings.curTVmode != settings.newTVmode:
        return True
    else:
        return False

def mainStereoChange():
#    xbmc.log('3D> mainStereoChange()', xbmc.LOGNOTICE)
    if settings.newTVmode == 1:
#        xbmc.log('3D> mainStereoChange 1 / OU', xbmc.LOGNOTICE)
#        xbmc.log('3D> ' + settings.TVcmd3Dou, xbmc.LOGNOTICE)
        #settings.TVport.write("xt 0 0 0 0 0\r")
        settings.TVport.write(settings.TVcmd3Dou + "\r")
        print settings.TVport.read(10) # read a '\n' terminated line
    elif settings.newTVmode == 2:
#        xbmc.log('3D> mainStereoChange 2 / SBS', xbmc.LOGNOTICE)
#        xbmc.log('3D> ' + settings.TVcmd3Dsbs, xbmc.LOGNOTICE)
        #settings.TVport.write("xt 0 0 1 0 0\r")
        settings.TVport.write(settings.TVcmd3Dsbs + "\r")
        print settings.TVport.read(10) # read a '\n' terminated line
    else:
#        xbmc.log('3D> mainStereoChange 0 / None', xbmc.LOGNOTICE)
#        xbmc.log('3D> ' + settings.TVcmd3Dnone, xbmc.LOGNOTICE)
        #settings.TVport.write("xt 0 1 0 0 0\r")
        settings.TVport.write(settings.TVcmd3Dnone + "\r")
        print settings.TVport.read(10) # read a '\n' terminated line
    # Notify of all messages
    notify()
    settings.curTVmode = settings.newTVmode

def mainTrigger():
#    xbmc.log('3D> mainTrigger()', xbmc.LOGNOTICE)
    if not settings.inProgress:
        settings.inProgress = True
        settings.newTVmode = getTranslatedStereoscopicMode()
        if stereoModeHasChanged():
            mainStereoChange()
        settings.inProgress = False

def onAbort():
#    xbmc.log('3D> onAbort()', xbmc.LOGNOTICE)
    # On exit switch TV back to None 3D
    settings.newTVmode = 0
    if stereoModeHasChanged():
#        xbmc.log('3D> Exit procedure: changing back to None 3D', xbmc.LOGNOTICE)
        mainStereoChange()

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
#        xbmc.log('3D> MyMonitor.__init__()', xbmc.LOGNOTICE)
        xbmc.Monitor.__init__(self)

    def onSettingsChanged( self ):
#        xbmc.log('3D> MyMonitor.onSettingsChanged()', xbmc.LOGNOTICE)
        settings.load()

    def onScreensaverDeactivated(self):
#        xbmc.log('3D> MyMonitor.onScreensaverDeactivated()', xbmc.LOGNOTICE)
        settings.inScreensaver = False

    def onScreensaverActivated(self):
#        xbmc.log('3D> MyMonitor.onScreensaverActivated()', xbmc.LOGNOTICE)
        settings.inScreensaver = True

    def onNotification(self, sender, method, data):
#        xbmc.log('3D> MyMonitor.onNotification()', xbmc.LOGNOTICE)
        # If detect mode is poll only - do not react on events
#        xbmc.log('3D> Notification Received: ' + str(sender) + ': ' + str(method) + ': ' + str(data), xbmc.LOGNOTICE)
        if method == 'Player.OnPlay':
            if xbmc.Player().isPlayingVideo():
#                xbmc.log('3D> Trigger: onNotification: ' + str(method), xbmc.LOGNOTICE)
                #Small delay to ensure Stereoscopic Manager completed changing mode
                xbmc.sleep(500)
                mainTrigger()
        elif method == 'Player.OnStop':
#            xbmc.log('3D> Trigger: onNotification: ' + str(method), xbmc.LOGNOTICE)
            #Small delay to ensure Stereoscopic Manager completed changing mode
            xbmc.sleep(500)
            mainTrigger()

def main():
#    xbmc.log('3D> main()', xbmc.LOGNOTICE)
    global dialog, dialogprogress, responseMap, settings, monitor
    dialog = xbmcgui.Dialog()
    dialogprogress = xbmcgui.DialogProgress()
    settings = Settings()
    monitor = MyMonitor()
#    xbmc.log('3D> opening serial port', xbmc.LOGNOTICE)

#    def get_port_ensured(self):
#        ser = None
#        while ser == None:
#            try:
#                ser = self.get_port()
#            except serial.serialutil.SerialException:
#                time.sleep(0.07)
#        return ser

    #settings.TVport = serial.Serial(0, 9600, timeout=1) # open first serial port
    settings.TVport = serial.Serial(settings.TVserialport, 9600, timeout=1) # open first serial port
#    xbmc.log('3D> ' + settings.TVport.portstr, xbmc.LOGNOTICE) # check which port was really used
    while not xbmc.abortRequested:
        if not settings.inScreensaver:
            settings.pollCount += 1
            if xbmc.getGlobalIdleTime() <= settings.idlesec:
                if settings.pollCount > settings.pollsec:
                    mainTrigger()
                    settings.pollCount = 0
                    continue
        xbmc.sleep(1000)
    onAbort()
#    xbmc.log('3D> closing serial port', xbmc.LOGNOTICE)
    settings.TVport.close() # close port
#    xbmc.log('3D> main() END', xbmc.LOGNOTICE)

if __name__ == '__main__':
    main()
