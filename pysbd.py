#name:			pysbd
#created:		May 2023
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to read an EIVA binary SDB file
#notes:			See main at end of script for example how to use this
#See readme.md for details
# sensorcategory
# 3 = ZDA
# 36 = gyro
# 35 = motion
# 7 SVS
# 13 rov depth
# 17 positionining
# 9 usbl
# 33 mbes

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
from pynmeagps import NMEAReader

###############################################################################
def main():
	filename = "C:/ggtools/pysbd/J129N032.SBD"
	# filename = "C:/ggtools/pysbd/J355N005.SBD"
	# filename = "C:/ggtools/pysbd/J355N001.SBD"
	filename = "C:/ggtools/pysbd/J129N032_stripped.SBD"

	#open the SBD file for reading by creating a new SBDFReader class and passin in the filename to open.  The reader will read the initial header so we can get to grips with the file contents with ease.
	print ( "processing file:", filename)
	reader = SBDReader(filename)
	# reader.fileptr.seek(4392, 0)

	start_time = time.time() # time  the process

	while reader.moreData():
		sensortype, msgtimestamp, msglen, data = reader.readdatagram()
		if sensortype is None:
			continue
		print(from_timestamp(msgtimestamp), sensortype, msglen, data)
		# if sensortype == 8: # NMEA INGGA Position
			# nmeastring=data.decode('utf-8').rstrip('\x00')
			# nmeaobject = NMEAReader.parse(nmeastring,VALCKSUM=0)
			# print(nmeaobject.lat, nmeaobject.lon)

	# navigation = reader.loadNavigation()
	# for n in navigation:
 		# print ("Date %s X: %.10f Y: %.10f Hdg: %.3f" % (from_timestamp(n[0]), n[1], n[2], n[3]))

	reader.close()
	print("Complete reading SBD file :-)")

####################################################################################################################
###############################################################################
class SENSOR:
	def __init__(self, id=0, porttype=0, name="", sensorcategory=0, sensortype=0, ipaddress="0.0.0.0", port=0, offsetx = 0, offsety = 0, offsetz = 0, offsetheading = 0, offsetroll = 0, offsetpitch = 0, offsetheave = 0):

		self.id 			= id
		self.name 			= name
		self.sensorcategory	= sensorcategory
		self.sensortype 	= sensortype
		self.ipaddress		= ipaddress
		self.porttype 		= porttype
		self.port 			= port
		self.offsetx 		= offsetx
		self.offsety 		= offsety
		self.offsetz 		= offsetz
		self.offsetheading 	= offsetheading
		self.offsetroll 	= offsetroll
		self.offsetpitch 	= offsetpitch
		self.offsetheave 	= offsetheave

	#print the contents of the class
	def __str__(self):
		return (pprint.pformat(vars(self)))	
	
###############################################################################
class SBDFILEHDR:
	def __init__(self, fileptr):

		self.sensors = {}

		# File Version: 9.0
		#header is 60 bytes...
		SBDFileHdr_fmt = '=30h'
		# SBDFileHdr_fmt = '<2H 2L 24h'
		SDBFileHdr_len = struct.calcsize(SBDFileHdr_fmt)
		SDBFileHdr_unpack = struct.Struct(SBDFileHdr_fmt).unpack_from

		data = fileptr.read(SDBFileHdr_len)
		s = SDBFileHdr_unpack(data)
		# self.unixtimeseconds=s[2]
		# self.unixtimemilliseconds=s[3]
		self.sensorcount 	= s[7]
		self.datastartbyte	= s[8]
		self.year 			= s[10]
		self.month 			= s[11]
		self.day 			= s[13]
		self.hour 			= s[14]
		self.minute 		= s[15]
		self.second 		= s[16]
		self.millisecond 	= s[17] # from caris
		self.version 		= s[19] # from caris dumpeiva
		self.date = datetime (self.year, self.month, self.day, self.hour, self.minute, self.second, self.millisecond)
		#Time: 1683658757.900 (2023/05/09 18:59:17.900),
		print("File Start Date %s " % (self.date))

		#geodesy is at offset 366 (80 bytes)
		fileptr.seek(366, 0)
		msg_fmt = '80s'
		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from
		data = fileptr.read(msg_len)
		s = msg_unpack(data)
		self.ellipsiod = s[0].decode('utf-8').rstrip('\x00')
		print (self.ellipsiod)

		#geodesy UTM is at 446
		fileptr.seek(446, 0)
		msg_fmt = '80s'
		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from
		data = fileptr.read(msg_len)
		s = msg_unpack(data)
		self.projection = s[0].decode('utf-8').rstrip('\x00')
		print (self.projection)
		
		#2do figure out how manyy sensor defintions there are...
		#each sensor definition takes 256 bytes.  
		# looks like the sensor definition starts at byte 1060 with an ID and then a type (hex 0x424)
		#looks like sensor name is 32 bytes and the remaining 224 are not yet known
		fileptr.seek(1060, 0)
		for idx in range(0,self.sensorcount + 1):
			msg_fmt 		= '8B 32s H'
			msg_len 		= struct.calcsize(msg_fmt)
			msg_unpack 		= struct.Struct(msg_fmt).unpack_from
			data 			= fileptr.read(msg_len)
			s 				= msg_unpack(data)
			sensorname 		= s[8].decode('utf-8').rstrip('\x00')
			sensorcategory	= s[0]
			sensortype		= s[1]
			porttype		= s[9]

			#now we need to read the rest of the structure based on the port type		
			if porttype == 1: # serial ports...
				#looks like we need 14 bytes for a com port definition
				msg_fmt 		= '<7H 11f 78H'
				msg_len 		= struct.calcsize(msg_fmt)
				msg_unpack 		= struct.Struct(msg_fmt).unpack_from
				data 			= fileptr.read(msg_len)
				s 				= msg_unpack(data)
				disabled 		= s[0]
				port 			= s[1]
				baud 			= s[3]
				parity 			= s[4]
				databits 		= s[5]
				stopbits 		= s[6]
				ipaddress = str("0.0.0.0")
				#seems ok until here.
				latency			= s[8]
				offsetx			= s[10]
				offsety			= s[11]
				offsetz			= s[12]
				offsetheading	= s[13]
				depthc_o	= s[13]
				offsetroll		= s[14]
				offsetpitch		= s[15]
				offsetheave		= s[16]
				gravity			= s[18]

			elif porttype == 2: # UDP ports...
				msg_fmt 		= '<2H 6B 11f 80H'
				#looks like we need 14 bytes for a ethernet port definition
				msg_len 		= struct.calcsize(msg_fmt)
				msg_unpack 		= struct.Struct(msg_fmt).unpack_from
				data 			= fileptr.read(msg_len)
				s 				= msg_unpack(data)
				disabled		= s[0]
				portnumber 		= s[1]
				ip1 			= s[4]
				ip2 			= s[5]
				ip3 			= s[6]
				ip4 			= s[7]
				ipaddress = str("%d.%d.%d.%d" % (ip1, ip2, ip3, ip4))
				stopbits 		= s[7]
				latency			= s[9]
				offsetx			= s[10]
				offsety			= s[11]
				offsetz			= s[12]
				offsetheading	= s[13]
				offsetroll		= s[14]
				offsetpitch		= s[15]
				offsetheave		= s[16]
				gravity			= s[18]
				depthc_o	= s[13]

			elif porttype == 4: # ATTU ports...
				msg_fmt 		= '<2H 6B 11f 80H'
				#looks like we need 14 bytes for a ethernet port definition
				msg_len 		= struct.calcsize(msg_fmt)
				msg_unpack 		= struct.Struct(msg_fmt).unpack_from
				data 			= fileptr.read(msg_len)
				s 				= msg_unpack(data)
				disabled		= s[0]
				portnumber 		= s[1]
				ip1 			= s[4]
				ip2 			= s[5]
				ip3 			= s[6]
				ip4 			= s[7]
				ipaddress = str("%d.%d.%d.%d" % (ip1, ip2, ip3, ip4))
				stopbits 		= s[7]
				latency			= s[9]
				offsetx			= s[10]
				offsety			= s[11]
				offsetz			= s[12]
				offsetheading	= s[13]
				offsetroll		= s[14]
				offsetpitch		= s[15]
				offsetheave		= s[16]
				gravity			= s[18]
				depthc_o	= s[13]

			else: # anything else
				msg_fmt 		= '<2H 6B 11f 80H'
				#looks like we need 14 bytes for a ethernet port definition
				msg_len 		= struct.calcsize(msg_fmt)
				msg_unpack 		= struct.Struct(msg_fmt).unpack_from
				data 			= fileptr.read(msg_len)
				s 				= msg_unpack(data)
				disabled		= s[0]
				portnumber 		= s[1]
				ip1 			= s[4]
				ip2 			= s[5]
				ip3 			= s[6]
				ip4 			= s[7]
				ipaddress = str("%d.%d.%d.%d" % (ip1, ip2, ip3, ip4))
				stopbits 		= s[7]
				latency			= s[9]
				offsetx			= s[10]
				offsety			= s[11]
				offsetz			= s[12]
				offsetheading	= s[13]
				offsetroll		= s[14]
				offsetpitch		= s[15]
				offsetheave		= s[16]
				gravity			= s[18]
				depthc_o	= s[13]

			sensor = SENSOR(id, porttype, sensorname, sensorcategory, sensortype, ipaddress, port, offsetx, offsety, offsetz, offsetheading, offsetroll, offsetpitch, offsetheave)
			print (id, sensor.name)

			self.sensors[sensorname] = sensor

		#print the sensor definitions
		for sensor in self.sensors:
			print (self.sensors[sensor])
			
		#not sure why we need to advance by 4 bytes....
		# msg_fmt 		= '<2H'
		# msg_len 		= struct.calcsize(msg_fmt)
		# msg_unpack 		= struct.Struct(msg_fmt).unpack_from
		# data 			= fileptr.read(msg_len)
		# s 				= msg_unpack(data)

		#the header has a pointer to the start of the data, so lets set the file pointer there now.		
		fileptr.seek(self.datastartbyte+20,0)
		print("Completed reading header at byte offset: %d " % (fileptr.tell()))
		# data = fileptr.read(4)
		
	#########################################################################################
	def __str__(self):
		return (pprint.pformat(vars(self)))

#########################################################################################
class SBDReader:
	'''now lets try to read the data packet header which is 32 bytes...'''
	# hdr_fmt = '=16h' # we know this works....
	hdr_fmt = '<4h 2L 2H'
	hdr_fmt = '<2L 2L L'
	hdr_fmt = '<4H 2L L'
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

	#########################################################################################
	def loadNavigation(self):
		navigation = []
		self.rewind()
		heading = 0
		start_time = time.time() # time the process
		while self.moreData() > 0:
			sensortype, msgtimestamp, msglen, data = self.readdatagram()

			if sensortype == 8: # NMEA INGGA Position
				nmeastring=data.decode('utf-8').rstrip('\x00')
				nmeaobject = NMEAReader.parse(nmeastring,VALCKSUM=0)
				navigation.append([msgtimestamp, nmeaobject.lon, nmeaobject.lat, heading])

		self.rewind()
		# print("Get navigation Range Duration %.3fs" % (time.time() - start_time)) # print the processing time.
		return (navigation)

	#########################################################################################
	def readdatagram(self):
		ping = None
		# remember the start position, so we can easily comput the position of the next packet
		currentPacketPosition = self.fileptr.tell()
		print("reading datagram from currentpos %d %s" % (currentPacketPosition, hex(currentPacketPosition)))

		data = self.fileptr.read(self.hdr_len)
		s = self.hdr_unpack(data)

		sensortype 					= s[0]
		msgunixtimeseconds 			= s[4]
		msgunixtimemicroseconds 	= s[5]
		msgtimestamp 				= msgunixtimeseconds + (msgunixtimemicroseconds / 1000000)
		msglen 						= s[6] #we know this works...!!!!

		if msglen == 0:
			return None, None, None, None

		if msglen == 102:
			msg_fmt = '< 20s' + str(msglen-20) + 's'
		elif msglen == 98:
			#god knows why we sometimes see this type of message.  makes no sense yet
			msg_fmt = '< 16s' + str(msglen-16) + 's' #+ '4s'
		else:
			msg_fmt = '< 20s' + str(msglen-20) + 's'

		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from

		data = self.fileptr.read(msg_len)
		s1 = msg_unpack(data)
		# msg=s1[0].decode('utf-8').rstrip('\x00')
		# print("sensortype: %d data: %s" %(sensortype, s1[1]))

		return sensortype, msgtimestamp, msglen, s1[1]

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

#########################################################################################
#########################################################################################
#########################################################################################
if __name__ == "__main__":
	main()

