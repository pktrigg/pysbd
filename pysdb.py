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

# ###############################################################################
# def createxyz(reader, projection, step=0):
# 	lastTimeStamp = 0
# 	navigation = reader.loadNavigation()

# 	if len(navigation) == 0:
# 		return

# 	# dump data to xyz
# 	for update in navigation:
# 		if update.timestamp - lastTimeStamp >= step:
# 			if projection is not None:
# 				x,y = projection(float(update.shipX),float(update.shipY))
# 				print("%.10f, %.10f, %.3f, %.3f" % (x, y, update.sensorAux1, update.sensorAux2))
# 			else:
# 				print("%.10f, %.10f, %.3f, %.3f" % (update.shipX, update.shipY, update.sensorAux1, update.sensorAux2))
# 			# print("%s %.10f, %.10f, %.3f, %.3f" % (update.dateTime, update.shipX, update.shipY, update.sensorAux1, update.sensorAux2))
# 			lastTimeStamp = update.timestamp

###############################################################################
# TIME HELPER FUNCTIONS
###############################################################################
def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()

def from_timestamp(unixtime):
	return datetime.utcfromtimestamp(unixtime)

def dateToKongsbergDate(dateObject):
	return dateObject.strftime('%Y%m%d')

def dateToKongsbergTime(dateObject):
	return dateObject.strftime('%H%M%S')

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


		#not sure we need this....
		# pkppkpkpk
		data = fileptr.read(4)

		print (fileptr.tell())



		# #NOW DO THE SECOND RECORD...

		# print ("XX %d" % (fileptr.tell()))

		# #now lets try to read the data packet header which is 20 bytes...
		# hdr_fmt = '=18h' # 36 bytes according to CARIS dump program
		# hdr_len = struct.calcsize(hdr_fmt)
		# hdr_unpack = struct.Struct(hdr_fmt).unpack_from

		# data = fileptr.read(hdr_len)
		# s = hdr_unpack(data)
		
		# msgid 			= s[0]
		# msglen 			= s[16]
		# msgsubpackets 	= s[2]

		# print (fileptr.tell())
		# # Disk Loc: 0x1228 offset 4648
		# msg_fmt = '=' + str(msglen) + 's'
		# msg_len = struct.calcsize(msg_fmt)
		# msg_unpack = struct.Struct(msg_fmt).unpack_from

		# print (fileptr.tell())
		# data = fileptr.read(msg_len)
		# s = msg_unpack(data)
		# msg=s[0].decode('utf-8').rstrip('\x00')
		# print(msg)
		# print(msg)




		# # self.fileSize = fileptr.seek(4770, 0) # as per CARIS...
		# #not sure wht we need these....
		# # data = fileptr.read(10)
		# print ("YY %d" % (fileptr.tell()))


		# #now lets try to read the data packet header which is 20 bytes...
		# msg_fmt = '=20h' # 40 bytes we think
		# msg_len = struct.calcsize(msg_fmt)
		# msg_unpack = struct.Struct(msg_fmt).unpack_from

		# data = fileptr.read(msg_len)
		# s = msg_unpack(data)
		

		# #s[8] seems to be the packet length
		# msgid 			= s[0]
		# msglen 			= s[1]
		# msglen 			= s[8] #this is correct!!!!
		# msgsubpackets 	= s[2] 

		# #first nmea string at 4682
		# msg_fmt = '=' + str(msglen) + 's'
		# msg_len = struct.calcsize(msg_fmt)
		# msg_unpack = struct.Struct(msg_fmt).unpack_from

		# print (fileptr.tell())
		# data = fileptr.read(msg_len)
		# s = msg_unpack(data)
		# print(s[0])
		# print(s[0])

#########################################################################################
	def __str__(self):
		return (pprint.pformat(vars(self)))

class Packet61Reader:
	P61Header_fmt = '=2H 4L 10B H 2L 2H L 2H 3L'
	P61Header_len = struct.calcsize(P61Header_fmt)
	P61Header_unpack = struct.Struct(P61Header_fmt).unpack_from

	P61Checksum_fmt = '=L'
	P61Checksum_len = struct.calcsize(P61Checksum_fmt)
	P61Checksum_unpack = struct.Struct(P61Checksum_fmt).unpack_from

	def __init__(self, fileptr):
		data = fileptr.read(self.P61Header_len)
		s = self.P61Header_unpack(data)

		self.version 					= s[0]
		self.offset 					= s[1]
		self.syncPattern				= s[2]
		self.size	 					= s[3]
		self.dataOffset					= s[4]
		self.dataIdentifier				= s[5]
		self.s7kTime 					= s[6:16]
		self.recordVersion				= s[17]
		self.deviceIdentifier			= s[18]
		self.reserved					= s[19]
		self.systemEnumerator			= s[20]
		self.reserved2					= s[21]
		self.flags						= s[22]
		self.reserved3					= s[23]
		self.reserved4					= s[24]
		self.totalRecordsinFragmentedSet= s[25]
		self.fragmentNumber				= s[26]

		# now read the dynamic part of the record.  we need to compute the bytes to read from the size minus the header and checksum
		bytesTosRead = self.size - self.P61Header_len - self.P61Checksum_len
		self.dataSection = fileptr.read(bytesTosRead)

		# now read the checksum
		data = fileptr.read(self.P61Checksum_len)
		s = self.P61Checksum_unpack(data)
		self.checksum = s[0]

class SBDReader:
	# SDBPacketHeader_fmt = '=h2b3hL'
	# SDBPacketHeader_len = struct.calcsize(SDBPacketHeader_fmt)
	# SDBPacketHeader_unpack = struct.Struct(SDBPacketHeader_fmt).unpack_from

	#now lets try to read the data packet header which is 32 bytes...
	hdr_fmt = '=16h'
	hdr_len = struct.calcsize(hdr_fmt)
	hdr_unpack = struct.Struct(hdr_fmt).unpack_from

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

	def __str__(self):
		return pprint.pformat(vars(self))

	def close(self):
		self.fileptr.close()

	def rewind(self):
		# go back to start of file
		self.fileptr.seek(0, 0)
		self.SDBFileHdr = SBDFILEHDR(self.fileptr)

	def moreData(self):
		bytesRemaining = self.fileSize - self.fileptr.tell()
		print ("current file ptr position:", self.fileptr.tell())
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

	def readDatagramheader(self):
		data = self.fileptr.read(self.SDBPacketHeader_len)
		if len(data) != self.SDBPacketHeader_len:
			return 0,0,0,0
		s = self.SDBPacketHeader_unpack(data)

		MagicNumber				= s[0]
		HeaderType				= s[1]
		SubChannelNumber		= s[2]
		NumChansToFollow		= s[3]
		Reserved1				= s[4]
		Reserved2				= s[5]
		NumBytesThisRecord		= s[6]

		return HeaderType, SubChannelNumber, NumChansToFollow, NumBytesThisRecord

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

		msgid 			= s[0]
		msglen 			= s[4] - 20
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


		# # read the packet header.  This permits us to skip packets we do not support
		# HeaderType, SubChannelNumber, NumChansToFollow, NumBytesThisRecord = self.readDatagramheader()
		# # trap corrup record
		# if NumBytesThisRecord == 0:
		# 	return ping

		# if HeaderType == 0:
		# 	ping = SDBPINGHEADER(self.fileptr, self.SDBFileHdr, SubChannelNumber, NumChansToFollow, NumBytesThisRecord)

		# 	# now read the padbytes at the end of the packet
		# 	padBytes = currentPacketPosition + NumBytesThisRecord - self.fileptr.tell()
		# 	if padBytes > 0:
		# 		data = self.fileptr.read(padBytes)
		# if HeaderType == 61:
		# 	ping = SDBPINGHEADER(self.fileptr, self.SDBFileHdr, SubChannelNumber, NumChansToFollow, NumBytesThisRecord)
		# 	bathy = Packet61Reader(self.fileptr)
		# 	# now read the padbytes at the end of the packet
		# 	padBytes = currentPacketPosition + NumBytesThisRecord - self.fileptr.tell()
		# 	# padBytes = (self.fileptr.tell() - currentPacketPosition) % 64
		# 	print ("Ping: %s  record for system:%s type:%s" % (ping.PingNumber, bathy.deviceIdentifier, bathy.recordVersion))
		# 	if padBytes > 0:
		# 		# bathy = Packet61Reader(self.fileptr) # this does not seem to work.  Odd!
		# 		data = self.fileptr.read(padBytes)
		# else:
		# 	# print ("unsupported packet type:%s at byte offset:%s NumBytes:%s" % (HeaderType, currentPacketPosition, NumBytesThisRecord))
		# 	self.fileptr.seek(currentPacketPosition + NumBytesThisRecord, 0)

		# return ping

	# def readChannel(self):
	#	 return SDBPINGCHANHEADER()

if __name__ == "__main__":
	main()

