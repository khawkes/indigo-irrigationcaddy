#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# IrrigationCaddy server plugin
#
# Copyright (c) 2013, Whizzo Software, LLC. All rights reserved.
# http://www.whizzosoftware.com

from __future__ import with_statement

import functools
import os
import serial
import sys
import threading
import time
import indigo
import urllib
import urllib2
import simplejson as json

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		# set debug option
		if 'debugEnabled' in pluginPrefs:
			self.debug = pluginPrefs['debugEnabled']
		else:
			self.debug = False

		# create empty device list
		self.deviceList = []

		# install authenticating opener
		self.passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
		authhandler = urllib2.HTTPBasicAuthHandler(self.passman)
		opener = urllib2.build_opener(authhandler)
		urllib2.install_opener(opener)
	
	def __del__(self):
		indigo.PluginBase.__del__(self)

	def deviceStartComm(self, device):
		self.debugLog("Starting device: " + device.name)
		if device.id not in self.deviceList:
			self.deviceList.append(device.id)
			if device.pluginProps.has_key("useAuthentication") and device.pluginProps["useAuthentication"]:
				self.passman.add_password(None, u"http://" + device.pluginProps["address"], device.pluginProps["username"], device.pluginProps["password"])
			self.update(device)

	def deviceStopComm(self,device):
		self.debugLog("Stopping device: " + device.name)
		if device.id in self.deviceList:
			self.deviceList.remove(device.id)

	def startup(self):
		self.debugLog(u"startup called")

	def runConcurrentThread(self):
		self.debugLog(u"Starting polling thread")
		try:
			while True:
				sleepInterval = 60
				if self.pluginPrefs.has_key("pollingInterval"):
					sleepInterval = int(self.pluginPrefs["pollingInterval"])
				self.sleep(sleepInterval)
				for deviceId in self.deviceList:
					self.update(indigo.devices[deviceId])
		except self.StopThread:
			# cleanup
			pass
		self.debugLog(u"Exited polling thread")

	def shutdown(self):
		self.debugLog(u"shutdown called")

	def update(self,device):
		theUrl = u"http://" + device.pluginProps["address"] + "/status.json"
		try:
			self.debugLog("Requesting status JSON")
			f = urllib2.urlopen(theUrl)
		except urllib2.HTTPError, e:
			self.errorLog("Error getting Irrigation Caddy (%s) status: %s" % (device.name, str(e)))
			return
		except urllib2.URLError, e:
			self.errorLog("Error getting Irrigation Caddy (%s) status (Irrigation Caddy isn't running): %s" % (device.name, str(e)))
			return
		except Exception, e:
			self.errorLog("Unknown error getting Irrigation Caddy (%s) status: %s" % (device.name, str(e)))
			return
		theJSON = f.read()
		self.debugLog("Received status JSON: " + theJSON)
		statusObj = json.loads(theJSON)
		
		val = "off"
		if statusObj["allowRun"]:
			val = "on"
		self.updateDeviceState(device, "active", val)
		
		val = "off"
		if statusObj["running"]:
			val = "on"
		self.updateDeviceState(device, "running", val)
		self.updateDeviceState(device, "zoneNumber", statusObj["zoneNumber"])
		self.updateDeviceState(device, "zoneSecondsLeft", statusObj["zoneSecLeft"])
		self.updateDeviceState(device, "programNumber", statusObj["progNumber"])
		self.updateDeviceState(device, "programSecondsLeft", statusObj["progSecLeft"])
		
		val = "off"
		if statusObj["isRaining"]:
			val = "on"
		self.updateDeviceState(device, "raining", val)
		self.updateDeviceState(device, "maxZones", statusObj["maxZones"])
		
		val = "off"
		if statusObj["useSensor1"]:
			val = "on"
		self.updateDeviceState(device, "rainSensor", val)

	def updateDeviceState(self,device,state,newValue):
		if (newValue != device.states[state]):
			device.updateStateOnServer(key=state, value=newValue)
	
	def postData(self,url,values):
		data = urllib.urlencode(values)
		req = urllib2.Request(url, data)
		return urllib2.urlopen(req)
	
	# Action callbacks

	def actionActivateSystem(self, action, device):
		self.debugLog(u"actionActivateSystem called")
		try:
			response = self.postData(u"http://" + device.pluginProps["address"] + "/runSprinklers.htm", {'run' : 'run'})
		except Exception, e:
			self.errorLog("Error sending \"Run Sprinklers\" action to Irrigation Caddy (%s): %s" % (device.name, str(e)))
		
	def actionDeactivateSystem(self, action, device):
		self.debugLog(u"actionDeactivateSystem called")
		try:
			response = self.postData(u"http://" + device.pluginProps["address"] + "/stopSprinklers.htm", {'stop' : 'off'})
		except Exception, e:
			self.errorLog("Error sending \"Stop Sprinklers\" action to Irrigation Caddy (%s): %s" % (device.name, str(e)))
		
	def actionRunProgram(self, action, device):
		self.debugLog(u"actionRunProgram called")
		try:
			response = self.postData(u"http://" + device.pluginProps["address"] + "/runProgram.htm", {'pgmNum' : action.props.get(u"programNum"), 'doProgram' : '1', 'runNow' : 'true'})
		except Exception, e:
			self.errorLog("Error sending \"Run Program\" action to Irrigation Caddy (%s): %s" % (device.name, str(e)))