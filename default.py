#!/usr/bin/python

"""
Lux for Kodi
Author: Thomas Verwijst
Originally developed as a support service for switching lights on playback states, though it could be ajusted very easily for other tasks
"""

import xbmc
import xbmcaddon
import xbmcgui
import datetime

import subprocess

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')

#global functions
def log(msg):
    try:
        print "#[Lux]# " + str(msg)
    except UnicodeEncodeError:
        print "#[Lux]# " + str(msg.encode( "utf-8", "ignore" ))

def notify(msg):
    dialog = xbmcgui.Dialog()
    dialog.notification(__scriptname__, str(msg) , xbmcgui.NOTIFICATION_INFO, 2500)

def triggerTime(h=0, m=0, next_day=False):
    now = datetime.datetime.now()
    # add one day to the date
    if(next_day):
        now = now + datetime.timedelta(days=1)
    test_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return test_time

def enableForSource(filepath):

    if (filepath.find("http://") > -1): #and getSettingAsBool('ExcludeHTTP'):
        log("Excluded: Video is playing via HTTP source, which is currently set as excluded location.")
        return False
    else:
        log("Not Excluded: Video is playing from a local source")

    return True

log("Loading '%s' version '%s'" % (__scriptname__, __version__))

#Class start
class LightsOut(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.init_property()
        log("Initalized")

    def init_property(self):
        # self.debug = __addon__.getSetting("debug")
        self.active = False
        self.show_notifications = __addon__.getSetting("show_notifications")
        self.reset_timeout = int(__addon__.getSetting("reset_timeout") ) *1000
        self.disable_on_pause = __addon__.getSetting("disable_on_pause")
        # scheduling settings
        self.use_schedule = __addon__.getSetting("use_schedule")
        start_hour      = int(__addon__.getSetting("start_hour") )
        start_minute    = int(__addon__.getSetting("start_minute") )
        end_hour        = int(__addon__.getSetting("end_hour") )
        end_minute      = int(__addon__.getSetting("end_minute") )

        self.start_time  = triggerTime(start_hour, start_minute)

        if(start_hour > end_hour):
            # add a day to date if end hour is lower than start hour
            self.end_time    = triggerTime(end_hour, end_minute, True)
        else:
            self.end_time    = triggerTime(end_hour, end_minute)

    def onPlayBackStarted(self):
        self.init_property()
        self.enable()

    def onPlayBackPaused(self):
        if self.disable_on_pause == "true":
            subprocess.call( "sudo python /home/pi/.xbmc/addons/service.sublime/resources/setpin.py 2 out high", shell=True)

    def onPlayBackResumed(self):
        if self.disable_on_pause == "true":
            self.enable()

    def onPlayBackStopped(self):
        self.reset()

    def onPlayBackEnded(self):
        xbmc.sleep(self.reset_timeout)
        self.onPlayBackStopped()

    def enable(self):

        trigger_window_active = False
        now = datetime.datetime.now()
        current_time = now.time()
        end_datetime = self.end_time
        start_time  = self.start_time.time()
        end_time    = end_datetime.time()

        schedule_ends_today = start_time < end_time
        shedule_active = self.use_schedule=="true"

        if shedule_active:
            if schedule_ends_today:
                # end time is on the same day as the start time
                trigger_window_active = current_time > start_time and current_time < end_time

            else:
                # end time is on an different day than the start time:
                    # current is after start time, and before end time (next day)
                    # OR
                    # current time before start time and current time is before end time (same day) => current time is after  00:00
                trigger_window_active = (current_time > start_time and now < end_datetime) or (current_time < start_time and current_time < end_time)
        else:
            trigger_window_active = True

        if trigger_window_active:
            if self.show_notifications == "true":
                notify("Switched off the lights" )
            subprocess.call( "sudo python /home/pi/.xbmc/addons/service.lux/resources/setpin.py 2 out low", shell=True)
            self.active = True
        else:
            if self.show_notifications == "true":
                notify("Trigger is not active")


    def reset(self):
        player = xbmc.Player()
        if player.isPlayingVideo() == False:
            if self.active:
                if self.show_notifications == "true": notify("Lights switched on" )
                subprocess.call( "sudo python /home/pi/.xbmc/addons/service.lux/resources/setpin.py 2 out high", shell=True)
            else:
                if self.show_notifications == "true": notify("Not active, do nothing" )

monitor = LightsOut()

while not xbmc.abortRequested:
    xbmc.sleep(1000)

del monitor