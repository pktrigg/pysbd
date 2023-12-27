#name:			pysdb
#created:		May 2023
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to read an EIVA binary SDB file
#notes:			See main at end of script for example how to use this
#See readme.md for details

import pprint
import struct
import os.path
from datetime import datetime
import time
import os
import sys
import math
import os.path
from glob import glob
import fnmatch
import numpy as np
import geodetic

def main():
	filename = "C:/ggtools/pysdb/J129N032.SBD"
	#open the SBD file for reading by creating a new SBDFReader class and passin in the filename to open.  The reader will read the initial header so we can get to grips with the file contents with ease.
	print ( "processing file:", filename)
	reader = SBDReader(filename)
	start_time = time.time() # time  the process

	while reader.moreData() > reader.hdr_len:
		pingHdr = reader.readDatagram()
	reader.rewind()

	# navigation = reader.loadNavigation()
	# for n in navigation:
	# 	print ("X: %.3f Y: %.3f Hdg: %.3f Alt: %.3f Depth: %.3f" % (n.sensorX, n.sensorY, n.sensorHeading, n.sensorAltitude, n.sensorDepth))
	print("Complete reading SDB file :-)")
	reader.close()

###############################################################################
# TIME HELPER FUNCTIONS
###############################################################################
def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()

def from_timestamp(unixtime):
	return datetime.utcfromtimestamp(unixtime)

def dateToSecondsSinceMidnight(dateObject):
	return (dateObject - dateObject.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

###############################################################################
def update_progress(job_title, progress):
	length = 20 # modify this to change the length
	block = int(round(length*progress))
	msg = "\r{0}: [{1}] {2}%".format(job_title, "#"*block + "-"*(length-block), round(progress*100, 2))
	if progress >= 1: msg += " DONE\r\n"
	sys.stdout.write(msg)
	sys.stdout.flush()

####################################################################################################################
###############################################################################
class SENSOR:
	def __init__(self, id=0, name=""):

		self.id = id
		self.name = name
###############################################################################
class SBDFILEHDR:
	def __init__(self, fileptr):

		self.sensors = {}

		# File Version: 9.0
		SBDFileHdr_fmt = '=30h'
		SDBFileHdr_len = struct.calcsize(SBDFileHdr_fmt)
		SDBFileHdr_unpack = struct.Struct(SBDFileHdr_fmt).unpack_from

		data = fileptr.read(SDBFileHdr_len)
		s = SDBFileHdr_unpack(data)
		self.version 		= s[19] # from caris dumpeiva
		self.sensorcount 	= s[7]
		self.year 			= s[10]
		self.month 			= s[11]
		self.day 			= s[13]
		self.hour 			= s[14]
		self.minute 		= s[15]
		self.second 		= s[16]
		self.millisecond 	= s[17] # from caris
		self.date = datetime (self.year, self.month, self.day, self.hour, self.minute, self.second, self.millisecond)
		#Time: 1683658757.900 (2023/05/09 18:59:17.900),
		print("File Start Date %s " % (self.date))

		#geodesy is at offset 366 (80 bytes)
		fileptr.seek(366, 0)
		msg_fmt = '=80s'
		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from

		data = fileptr.read(msg_len)
		s = msg_unpack(data)
		self.ellipsiod = s[0].decode('utf-8').rstrip('\x00')

		#geodesy UTM is at 446
		fileptr.seek(446, 0)
		msg_fmt = '=80s'
		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from

		data = fileptr.read(msg_len)
		s = msg_unpack(data)
		self.projection = s[0].decode('utf-8').rstrip('\x00')
		print (self.projection)
		print (self.projection)
		
		#2do figure out how manyy sensor defintions there are...
		#each sensor definition takes 256 bytes.  
		# nmea ZDA at offset 1068
		# name is at offset 1323
		# name Sprint at offset 1579

		#try it as a loop
		#looks like sensor name is 32 bytes and the remaining 224 are not yet known
		fileptr.seek(1068, 0)
		for idx in range(0,self.sensorcount + 1):
			msg_fmt = '=32s'
			msg_len = struct.calcsize(msg_fmt)
			msg_unpack = struct.Struct(msg_fmt).unpack_from
			data = fileptr.read(msg_len)
			s = msg_unpack(data)
			sensorname = s[0].decode('utf-8').rstrip('\x00')

			#we do not know what these contain yet so skip them
			msg_fmt = '=112h'
			msg_len = struct.calcsize(msg_fmt)
			msg_unpack = struct.Struct(msg_fmt).unpack_from
			data = fileptr.read(msg_len)
			s = msg_unpack(data)
			id = s[0]
			baud = s[4]
			parity = s[5]
			bits = s[6]
			stopbits = s[7]

			sensor = SENSOR(id, sensorname)
			# self.fileSize = fileptr.seek(224, 1)
			print (sensor.name)

			self.sensors[sensorname] = sensor

		#not sure why we need this....
		data = fileptr.read(4)

	#########################################################################################
	def __str__(self):
		return (pprint.pformat(vars(self)))

#########################################################################################
class SBDReader:
	'''now lets try to read the data packet header which is 32 bytes...'''
	hdr_fmt = '=16h' # we know this works....
	hdr_fmt = '=3l4f2h'
	hdr_len = struct.calcsize(hdr_fmt)
	hdr_unpack = struct.Struct(hdr_fmt).unpack_from

	#########################################################################################
	def __init__(self, SDBfileName):
		if not os.path.isfile(SDBfileName):
			print ("file not found:", SDBfileName)
		self.fileName = SDBfileName
		self.fileptr = open(SDBfileName, 'rb')
		self.fileSize = self.fileptr.seek(0, 2)
		# go back to start of file
		self.fileptr.seek(0, 0)

		if self.fileSize < 30:
			# do not open impossibly small files.
			self.fileptr.close()
			return
		#the file is of a sensible size so open it.
		self.SDBFileHdr = SBDFILEHDR(self.fileptr)

	#########################################################################################
	def __str__(self):
		return pprint.pformat(vars(self))

	#########################################################################################
	def close(self):
		self.fileptr.close()

	#########################################################################################
	def rewind(self):
		# go back to start of file
		self.fileptr.seek(0, 0)
		self.SDBFileHdr = SBDFILEHDR(self.fileptr)

	#########################################################################################
	def moreData(self):
		bytesRemaining = self.fileSize - self.fileptr.tell()
		# print ("current file ptr position:", self.fileptr.tell())
		return bytesRemaining

	# def loadNavigation(self):
	# 	navigation = []
	# 	self.rewind()
	# 	start_time = time.time() # time the process
	# 	while self.moreData() > 0:
	# 		pingHdr = self.readDatagram()
	# 		if pingHdr != None:
	# 			# we need to calculate the approximate speed, so need the ping interval
	# 			d = datetime (pingHdr.Year, pingHdr.Month, pingHdr.Day, pingHdr.Hour, pingHdr.Minute, pingHdr.Second, pingHdr.HSeconds * 10000)
	# 			r = SDBNAVIGATIONRECORD(to_timestamp(d), d, pingHdr.PingNumber, pingHdr.ShipXcoordinate, pingHdr.ShipYcoordinate, pingHdr.SensorXcoordinate, pingHdr.SensorYcoordinate, pingHdr.SensorDepth, pingHdr.SensorPrimaryAltitude, pingHdr.SensorHeading, pingHdr.SensorSpeed, pingHdr.AuxVal1, pingHdr.AuxVal2)
	# 			navigation.append(r)

	# 	self.rewind()
	# 	# print("Get navigation Range Duration %.3fs" % (time.time() - start_time)) # print the processing time.
	# 	return (navigation)

	#########################################################################################
	def computeSpeedFromPositions(self, navData):
		if (navData[0].sensorX <= 180) & (navData[0].sensorY <= 90): #data is in geographicals
			for r in range(len(navData) - 1):
				rng, bearing12, bearing21 = geodetic.calculateRangeBearingFromGeographicals(navData[r].sensorX, navData[r].sensorY, navData[r+1].sensorX, navData[r+1].sensorY)
				# now we have the range, comput the speed in metres/second. where speed = distance/time
				navData[r].sensorSpeed = rng / (navData[r+1].dateTime.timestamp() - navData[r].dateTime.timestamp())
		else:
			for r in range(len(navData) - 1):
				rng, bearing12, bearing21 = geodetic.calculateRangeBearingFromGridPosition(navData[r].sensorX, navData[r].sensorY, navData[r+1].sensorX, navData[r+1].sensorY)
				# now we have the range, comput the speed in metres/second. where speed = distance/time
				navData[r].sensorSpeed = rng / (navData[r+1].dateTime.timestamp() - navData[r].dateTime.timestamp())

		# now smooth the sensorSpeed
		speeds = [o.sensorSpeed for o in navData]
		npspeeds=np.array(speeds)

		smoothSpeed = geodetic.medfilt(npspeeds, 5)
		meanSpeed = float(np.mean(smoothSpeed))

		for r in range(len(navData) - 1):
			navData[r].sensorSpeed = float (smoothSpeed[r])

		return meanSpeed, navData

	#########################################################################################
	def readDatagram(self):
		ping = None
		# remember the start position, so we can easily comput the position of the next packet
		currentPacketPosition = self.fileptr.tell()
		# print("currentpos %d" % (currentPacketPosition))

		# Sounder ID = 33
		# Disk Loc: 0x1228 offset 4648
		# Datagram type: POSITION (9.0)       Time: 1683658757.900 (2023/05/09 18:59:17.900),  Size:    102,  # subpackets:    0
		# Seqence Number:    0  Easting: 286971.946  Northing: 6748230.922

		# Disk Loc: 0x12A2 offset 4770
		# Datagram type (Other 9.0) : 65535    Time: 1683658757.901 (2023/05/09 18:59:17.901),  Size:     98,  # subpackets:    0

		# Disk Loc: 0x1318 offset 4888
		# Datagram type: POSITION (9.0)       Time: 1683658757.900 (2023/05/09 18:59:17.900),  Size:    102,  # subpackets:    0
		# Seqence Number:    0  Easting: 286971.946  Northing: 6748230.922


		# Disk Loc: 0x1392 offset 5010
		# Datagram type: GYRO (9.0)           Time: 1683658758.107 (2023/05/09 18:59:18.107),  Size:     30,  # subpackets:    0
		# Seqence Number:    0  Gyro:  37.950

		#not sure wht we need these....
		# data = fileptr.read(4)

		# print (self.fileptr.tell())

		data = self.fileptr.read(self.hdr_len)
		s = self.hdr_unpack(data)

		# msgid 			= s[0]
		msgunixtimeseconds 			= s[0]
		msgunixtimemicroseconds 			= s[1]
		msgtimestamp = msgunixtimeseconds + (msgunixtimemicroseconds / 1000000)
		msglen 						= s[2] - 20 #we know this works...!!!!

		# msglen 			= s[4] - 20 #we know this works...!!!!
		msgsubpackets 	= s[2]

		# print (self.fileptr.tell())
		# Disk Loc: 0x1228 offset 4648 AS PER CARIS, WHICH MEANS CARIS OFFSET + 40 BYTE HEADER
		msg_fmt = '=' + str(msglen) + 's' + '4h'
		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from

		print ("Reading %d bytes" % (msg_len))
		data = self.fileptr.read(msg_len)
		s = msg_unpack(data)
		# msg=s[0].decode('utf-8').rstrip('\x00')
		print(s[0])

		return ping

#########################################################################################
#########################################################################################
#########################################################################################
if __name__ == "__main__":
	main()

