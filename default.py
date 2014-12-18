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

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')

#global functions
def log(msg):
    try:
        message = '%s: %s' % (__addonname__, str(msg) )
    except UnicodeEncodeError:
        message = '%s: %s' % (__addonname__, str(msg.encode('utf-8', 'ignore')) )

    print message

def notify(msg):
    dialog = xbmcgui.Dialog()
    dialog.notification(__addonname__, str(msg) , xbmcgui.NOTIFICATION_INFO, 2500)

def triggerTime(h=0, m=0, next_day=False):
    now = datetime.datetime.now()
    # add one day to the date
    if(next_day):
        now = now + datetime.timedelta(days=1)
    test_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return test_time

# def enableForSource(filepath):

#     if (filepath.find("http://") > -1): #and getSettingAsBool('ExcludeHTTP'):
#         log("Excluded: Video is playing via HTTP source, which is currently set as excluded location.")
#         return False
#     else:
#         log("Not Excluded: Video is playing from a local source")

#     return True

log("Loading '%s' version '%s'" % (__addonname__, __addonversion__))

#Class start
class Lux(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.init_property()
        log("Initalized")

    def getSetting(self, setting, boolean=False):

        if boolean == True:
            return __addon__.getSetting(setting) == 'true'
        else:
            return __addon__.getSetting(setting)

    def init_property(self):
        # self.debug = __addon__.getSetting("debug")
        self.active = False
        self.show_notifications = self.getSetting("show_notifications", True)
        self.disable_on_pause   = self.getSetting("disable_on_pause", True)
        self.reset_timeout      = int( self.getSetting("reset_timeout") ) * 1000
        self.min_duration       = int( self.getSetting("minimum_duration") )

        self.hyperion_schedule  = self.getSetting("hyperion", True)
        self.hyperion_state     = self.getHyperionState();

        # scheduling settings
        self.use_schedule = self.getSetting("use_schedule", True)
        start_hour      = int(self.getSetting("start_hour") )
        start_minute    = int(self.getSetting("start_minute") )
        end_hour        = int(self.getSetting("end_hour") )
        end_minute      = int(self.getSetting("end_minute") )

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
        if self.disable_on_pause:
            subprocess.call("sudo python /home/pi/.xbmc/addons/service.sublime/resources/setpin.py 2 out high", shell=True)

    def onPlayBackResumed(self):
        if self.disable_on_pause:
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
        duration_long_enough = True

        now = datetime.datetime.now()
        current_time = now.time()
        end_datetime = self.end_time
        start_time  = self.start_time.time()
        end_time    = end_datetime.time()

        schedule_ends_today = start_time < end_time
        shedule_active = self.use_schedule

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

        if self.getTotalTime() < self.min_duration * 60:
            log('Duration too short')
            duration_long_enough = False

        if trigger_window_active and duration_long_enough:
            # set message
            message = "Switched off the lights"

            # notify if enabled
            if self.show_notifications: notify(message)

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
            if self.show_notifications:
                notify(message)
            log(message)

            if (self.hyperion_schedule and self.hyperion_state == True) and duration_long_enough:
                log("Hyperion is running, but it shouldnt, stopping service")
                self.disableHyperion()

    def reset(self):

        if self.isPlayingVideo() == False:

            if self.active:
                message = "Lights switched on"
                if self.show_notifications:
                    notify(message)
                subprocess.call( "sudo python /home/pi/.xbmc/addons/service.lux/resources/setpin.py 2 out high", shell=True)
            else:
                message = "Not active, do nothing"
                if self.show_notifications:
                    notify(message)

            log(message)

monitor = Lux()

while not xbmc.abortRequested:
    xbmc.sleep(1000)

del monitor
