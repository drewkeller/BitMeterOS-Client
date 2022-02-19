#!/usr/bin/env python

import cfg
#import bmclient
from db import Database
from time import sleep
import wx
import wx.adv
import sys
import os
import os.path
import gettext
import datetime
from datetime import datetime, timedelta
import re
import traceback
import logging

TITLE = "Bitmeter OS Client"
ICON = "icon.ico"
APP_NAME = "BitmeterOSClient"
APP_VENDOR = "AWK"
APP_VERSION = "1.0"
APP_USER_MODEL_ID = "AWK.BitmeterOSClient"

_ = gettext.gettext


class TaskBarIcon(wx.adv.TaskBarIcon):

    def __init__(self, frame):
        self.frame = frame
        wx.adv.TaskBarIcon.__init__(self)
        self.iconName = ""
        self.label = ""
        self.SetIcon(ICON, TITLE)
    
    def SetIcon(self, iconName, label):
        if iconName != self.iconName or label != self.label:
            self.iconName = iconName
            self.label = label
            super().SetIcon(wx.Icon(iconName), label)

    def CreatePopupMenu(self):
        menu = wx.Menu()

        # create menu items that show alert status (icon based on percentage and value in text)
        try:
            alerts = db.getSortedAlerts([('amount', False), ('interval', False)])
            for id, alert in enumerate(alerts):
                icon = app.getIconFromPercent(alert.percent, theme=config.menu_theme)
                label = f"{alert.percent:>3.0f}%   {alert.usage.toString():>10}  - {alert.name}"
                self.createMenuItem(menu, label, icon=icon)
        except Exception as ex:
            logging.error(f"{_('Error creating alert menu item')}: {ex}")
        
        # This gives different/inaccurate numbers from the alert usages 
        #menu.AppendSeparator()
        #self.createMenuItem(menu, f"{bmclient.getTodayUsage()} - Today")
        #self.createMenuItem(menu, f"{bmclient.getBillingPeriodUsage()} - This Billing")
        
        # create menu items that open URLs to hosts called out in the config file
        try:
            menu.AppendSeparator()
            self.createMenuItemForHost(menu, _('Local (admin)'), "localhost")
            if len(config.hosts) > 0:
                for key, host in config.hosts.items():
                    self.createMenuItemForHost(menu, f"{_('Open')} {host.label}", host.name, host.port)
        except Exception as ex:
            logging.error(f"{_('Error creating host menu item')}: {ex}")

        menu.AppendSeparator()
        self.createMenuItem(menu, _('Exit'), func=app.onExit)
        return menu
    
    def createMenuItem(self, menu, label, icon=None, func=None, itemid=wx.ID_ANY):
        item = wx.MenuItem(menu, itemid, label)
        if icon:
            #img = wx.Image(icon.replace(".ico", ".png"))
            ico = wx.Icon(icon)
            bmp = wx.Bitmap(ico.Width, ico.Height)
            bmp.CopyFromIcon(ico)
            #bmp = img.ConvertToBitmap()
            item.SetBitmap(bmp)
        if func:
            menu.Bind(wx.EVT_MENU, func, id=item.GetId())
        menu.Append(item)
        return item

    def createMenuItemForHost(self, menu, label, host, port=2605):
        item = self.createMenuItem(menu, label, func=self.onHostClick)
        item.host = host
        item.port = port
        return item

    def onHostClick(self, event):
        menu = wx.Menu()
        menu = event.EventObject
        id = event.GetId()
        item = menu.FindItemById(id)
        app.openUrl(f"http://{item.host}:{item.port}")


class App(wx.App):
    def OnInit(self):
        if not self.isOnlyInstance():
            return False

        self.frame = wx.Frame(None)
        self.SetTopWindow(self.frame)
        self.taskbarIcon = TaskBarIcon(self.frame)

        # set up timer for periodic update
        self.timer = wx.Timer(self)
        self.timer.Start(1000)
        self.Bind(wx.EVT_TIMER, self.onTimerTick)

        return True

    def isOnlyInstance(self):
        """ 
        Ensure we are the only instance or quit.
        Multiples of the same icon on the taskbar would be confusing .
        """
        self.name = f"{self.AppName}.{wx.GetUserId()}"
        self.instance = wx.SingleInstanceChecker(self.name)
        if self.instance.IsAnotherRunning():
            return False
        return True

    def onExit(self, event):
        self.taskbarIcon.RemoveIcon()
        self.taskbarIcon.Destroy()
        self.frame.Close()
        self.Destroy()

    def onTimerTick(self, event):
        """ Update all alerts """    
        db.getAlerts()
        (alert, percent, usage) = db.getHighestAlertPercent()
        icon = app.getIconFromPercent(percent, theme=config.taskbar_theme)
        label = f"{percent:>3.0f}%   {usage.toString():>10}  - {alert.name}"
        app.taskbarIcon.SetIcon(icon, label)
        delta = datetime.now() - timedelta(days=1)
        ts = int(delta.timestamp())
        if percent >= config.warning_threshold_percent and alert.lastNotified < ts:
            self.notify(_('Usage Warning'), label, 0)
            ts = int(datetime.now().timestamp())
            alert.lastNotified = ts
            assert(alert.lastNotified > 0)

    def getIconFromPercent(self, percent, theme):
        # round to nearest 10 and pad to 3 digits
        padded = f"{int(round(percent, -1)):0>3}"
        icon = f"status-{padded}"
        icon = f"icons{os.sep}{theme}{os.sep}{icon}.ico"
        return icon

    def openUrl(self, url):
        if sys.platform == 'win32':
            os.system(f"start \"\" {url}")
        else:
            print(_('Failed to open url'))

    def notify(self, title, msg, duration=5):
        #self.taskbarIcon.ShowBalloon(title, msg, duration)
        notify = wx.adv.NotificationMessage(title, msg,
            parent=None, flags=wx.ICON_INFORMATION)
        notify.UseTaskBarIcon(self.taskbarIcon)
        if sys.platform == 'win32':
            startPath = os.path.expandvars("%AppData%\Microsoft\Windows\Start Menu\Programs")
            shortcutPath = startPath + "\BitMeter OS Client\BitMeter OS Client.lnk"
            success = notify.MSWUseToasts(shortcutPath=shortcutPath, appId=APP_USER_MODEL_ID)
        notify.Show(timeout=duration)

if __name__ == '__main__':
    try:
        logging.basicConfig(filename="bitmeter.log", level=logging.DEBUG)
        cfg.app = App(redirect=False)
        app = cfg.app
        config = cfg.config
        cfg.db = Database()
        db = cfg.db
        wx.App.SetAppName(app, APP_NAME)
        wx.App.SetVendorName(app, APP_VENDOR)
        app.MainLoop()
    except Exception:
        logging.error(traceback.print_exc())
