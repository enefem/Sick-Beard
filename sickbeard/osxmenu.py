

import objc
from Foundation import *
from AppKit import *
from PyObjCTools import AppHelper
from objc import YES, NO, nil
from threading import Thread

import os
import cherrypy
import Cheetah.DummyTransaction
import sickbeard
from sickbeard import tv, ui
from notifiers import growl_notifier
import sys

status_icons = {'idle':'sb_idle.png',
                'clicked':'sb_clicked.png'}
start_time = NSDate.date()
debug = 0

class SickBeardDelegate(NSObject):

    icons = {}
    status_bar = None

    def awakeFromNib(self):
        #Status Bar iniatilize
        #if (debug == 1) : NSLog("[osx] awake")
        self.buildMenu()
        #Timer for updating menu
        self.timer = NSTimer.alloc().initWithFireDate_interval_target_selector_userInfo_repeats_(start_time, 1.0, self, 'updateAction:', None, True)

        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSDefaultRunLoopMode)
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSEventTrackingRunLoopMode)
#        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSModalPanelRunLoopMode)
        
        
        self.timer.fire()
        
        

    def buildMenu(self):
        #logging.info("building menu")
        status_bar = NSStatusBar.systemStatusBar()
        self.status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        for i in status_icons.keys():
            self.icons[i] = NSImage.alloc().initByReferencingFile_(os.path.join(sickbeard.PROG_DIR, status_icons[i]))

        self.status_item.setImage_(self.icons['idle'])
        self.status_item.setAlternateImage_(self.icons['clicked'])
        self.status_item.setHighlightMode_(1)
        self.status_item.setToolTip_('SickBeard')
        self.status_item.setEnabled_(YES)

        NSLog("[osx] menu 1 building")

        #Variables
        self.state = "Idle"
        self.speed = 0
        self.version_notify = 1
        self.status_removed = 0

        NSLog("[osx] menu 2 initialization")

        #Menu construction
        self.menu = NSMenu.alloc().init()

        try:
            menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Dummy", '', '')
            menu_item.setHidden_(YES)
            self.isLeopard = 1
        except:
            self.isLeopard = 0

        NSLog("[osx] menu 3 construction")

        #State Item
        self.open_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Open Browser', 'openBrowserAction:', '')
        self.open_menu_item.setRepresentedObject_("")
        self.menu.addItem_(self.open_menu_item)

        #force search
        self.force_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Force Search', 'forceSearchAction:', '')
        self.force_menu_item.setRepresentedObject_("")
        self.menu.addItem_(self.force_menu_item)
        # stop search
        self.searchActive_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Stop Search', '', '')
        self.searchActive_menu_item.setRepresentedObject_("")
        self.menu.addItem_(self.searchActive_menu_item)

        #seporator
        self.separator_menu_item = NSMenuItem.separatorItem()
        self.menu.addItem_(self.separator_menu_item)
        
        #Quit SickBeard
        self.quit_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit SickBeard', 'quitAction:', '')
        self.quit_menu_item.setRepresentedObject_("")
        self.menu.addItem_(self.quit_menu_item)
        
        # add icon menu too status icon
        self.status_item.setMenu_(self.menu)

        NSLog("[osx] menu 4 warning added")

    def openBrowserAction_(self, sender):
        NSLog("openeing browser oO")
        sickbeard.launchBrowser()

    def updateAction_(self, sender):
        self._searchUpdate()

    def _searchUpdate(self):
        
        try:
            if not sickbeard.currentSearchScheduler.action.amActive: #@UndefinedVariable
                if self.isLeopard:
                    self.force_menu_item.setHidden_(NO)
                    self.searchActive_menu_item.setHidden_(YES)
                else:
                    self.resume_menu_item.setEnabled_(YES)
                    self.searchActive_menu_item.setEnabled_(NO)
            else:
                if self.isLeopard:
                    self.force_menu_item.setHidden_(YES)
                    self.searchActive_menu_item.setHidden_(NO)
                else:
                    self.force_menu_item.setEnabled_(NO)
                    self.searchActive_menu_item.setEnabled_(YES)
        except :
            NSLog("[osx] pauseUpdate Exception %s" % (sys.exc_info()[0]))

    def forceSearchAction_(self, sender):
        # force it to run the next time it looks
        result = sickbeard.currentSearchScheduler.forceRun()
        if result:
            ui.notifications.message('Episode search started',
                          'Note: RSS feeds may not be updated if retrieved recently')

    def stopSearchAction_(self, sender):
        pass

    def quitAction_(self, sender):
        self.setMenuTitle("\n\n%s\n" % ('Stopping...'))
        sickbeard.invoke_shutdown()

    def setMenuTitle(self, text):
        try:
            style = NSMutableParagraphStyle.new()
            style.setParagraphStyle_(NSParagraphStyle.defaultParagraphStyle())
            style.setAlignment_(NSCenterTextAlignment)
            style.setLineSpacing_(0.0)
            style.setMaximumLineHeight_(9.0)
            style.setParagraphSpacing_(-3.0)

            #Trying to change color of title to white when menu is open TO FIX
            if self.menu.highlightedItem():
                #logging.info("Menu Clicked")
                titleColor = NSColor.highlightColor()
            else:
                #logging.info("Menu Not Clicked")
                titleColor = NSColor.blackColor()

            titleAttributes = {
                NSBaselineOffsetAttributeName :  5.0,
                NSFontAttributeName:             NSFont.menuFontOfSize_(9.0),
                NSParagraphStyleAttributeName:   style
                #,NSForegroundColorAttributeName:  titleColor
                }

            title = NSAttributedString.alloc().initWithString_attributes_(text, titleAttributes)
            self.status_item.setAttributedTitle_(title)
        except :
            NSLog("[osx] setMenuTitle Exception %s" % (sys.exc_info()[0]))



