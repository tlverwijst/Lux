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
import re
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

        self.hyperion_schedule  = __addon__.getSetting("hyperion") == "true"
        self.hyperion_state     = self.getHyperionState();

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
            subprocess.call("sudo python /home/pi/.xbmc/addons/service.sublime/resources/setpin.py 2 out high", shell=True)

    def onPlayBackResumed(self):
        if self.disable_on_pause == "true":
            self.enable()

    def onPlayBackStopped(self):
        self.reset()

    def onPlayBackEnded(self):
        log("playback ended, timeout: "+str(self.reset_timeout) +" seconds")
        xbmc.sleep(self.reset_timeout)
        self.onPlayBackStopped()

    def enableHyperion(self):
        subprocess.call("sudo /sbin/initctl start hyperion", shell=True)

    def disableHyperion(self):
        subprocess.call("sudo /sbin/initctl stop hyperion", shell=True)

    def getHyperionState(self):
        # regex
        enabled = re.compile('hyperion start/running')
        disabled = re.compile('hyperion stop/waiting')

        # get state
        state = subprocess.check_output("sudo /sbin/initctl status hyperion", shell=True)

        if enabled.match(state):
            log("Hyperion is running")
            return True
        elif disabled.match(state):
            log("Hyperion is NOT running")
            return False
        else:
            log("Hyperion not found")
            return False

        notify('Hyperion State:' + str(state) )

    def enable(self):

        log("Enabled")

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
            # set message
            message = "Switched off the lights"

            # notify if enabled
            if self.show_notifications == "true": notify(message)

            #  switch lights
            subprocess.call( "sudo python /home/pi/.xbmc/addons/service.lux/resources/setpin.py 2 out low", shell=True)
            self.active = True

            if self.hyperion_schedule and self.hyperion_state == False:
                log("Enabling Hyperion")
                self.enableHyperion()

            else:
                log("Hyperion is already running, or ignoring")

        else:
            message = "Trigger is not active"
            if self.show_notifications == "true":
                notify(message)
            log(message)

            if self.hyperion_schedule and self.hyperion_state == True:
                log("Hyperion is running, but it shouldnt, stopping service")
                self.disableHyperion()

    def reset(self):

        player = xbmc.Player()

        if player.isPlayingVideo() == False:

            if self.active:
                message = "Lights switched on"
                if self.show_notifications == "true":
                    notify(message)
                subprocess.call( "sudo python /home/pi/.xbmc/addons/service.lux/resources/setpin.py 2 out high", shell=True)
            else:
                message = "Not active, do nothing"
                if self.show_notifications == "true":
                    notify(message)

            log(message)

monitor = LightsOut()

while not xbmc.abortRequested:
    xbmc.sleep(1000)

del monitor
