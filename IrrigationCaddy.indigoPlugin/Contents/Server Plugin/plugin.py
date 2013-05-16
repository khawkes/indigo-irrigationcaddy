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

		if 'debugEnabled' in pluginPrefs:
			self.debug = pluginPrefs['debugEnabled']
		else:
			self.debug = False
		self.deviceList = []
	
	def __del__(self):
		indigo.PluginBase.__del__(self)

	def deviceStartComm(self, device):
		self.debugLog("Starting device: " + device.name)
		if device.id not in self.deviceList:
			self.update(device)
			self.deviceList.append(device.id)

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

	def shutdown(self):
		self.debugLog(u"shutdown called")

	def update(self,device):
		theUrl = u"http://" + device.pluginProps["address"] + "/status.json"
		try:
			self.debugLog("Getting status JSON")
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
		self.debugLog("Got status JSON")
		theJSON = f.read()
		self.debugLog(theJSON)
		statusObj = json.loads(theJSON)
		self.updateDeviceState(device, "active", statusObj["allowRun"])
		self.updateDeviceState(device, "running", statusObj["running"])
		self.updateDeviceState(device, "zoneNumber", statusObj["zoneNumber"])
		self.updateDeviceState(device, "programNumber", statusObj["progNumber"])

	def updateDeviceState(self,device,state,newValue):
		if (newValue != device.states[state]):
			device.updateStateOnServer(key=state, value=newValue)
		
	# Action callbacks

	def actionActivateSystem(self, action, device):
		indigo.server.log(u"actionActivateSystem called")
		url = u"http://" + device.pluginProps["address"] + "/runSprinklers.htm"
		values = {'run' : 'run'}
		data = urllib.urlencode(values)
		req = urllib2.Request(url, data)
		try:
			response = urllib2.urlopen(req)
		except Exception, e:
			self.errorLog("Error sending \"Run Sprinklers\" action to Irrigation Caddy (%s): %s" % (device.name, str(e)))
		
	def actionDeactivateSystem(self, action, device):
		indigo.server.log(u"actionDeactivateSystem called")
		url = u"http://" + device.pluginProps["address"] + "/stopSprinklers.htm"
		values = {'stop' : 'off'}
		data = urllib.urlencode(values)
		req = urllib2.Request(url, data)
		try:
			response = urllib2.urlopen(req)
		except Exception, e:
			self.errorLog("Error sending \"Stop Sprinklers\" action to Irrigation Caddy (%s): %s" % (device.name, str(e)))
		
	def actionRunProgram(self, action, device):
		indigo.server.log(u"actionRunProgram called")
		url = u"http://" + device.pluginProps["address"] + "/runProgram.htm"
		values = {'pgmNum' : action.props.get(u"programNum"), 'doProgram' : '1', 'runNow' : 'true'}
		data = urllib.urlencode(values)
		req = urllib2.Request(url, data)
		try:
			response = urllib2.urlopen(req)
		except Exception, e:
			self.errorLog("Error sending \"Run Program\" action to Irrigation Caddy (%s): %s" % (device.name, str(e)))