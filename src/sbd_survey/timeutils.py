from datetime import datetime
from datetime import timedelta
import math
from operator import le

def main():

	# test case.  these match each other.  verified online.
	gpsseconds = 1248563590
	unixtime = 1564528372
	adjustedgpsTime =    267980536.60 
 
	adjustedgpsTime = 338394535
	print ("adjustedgps2unix %3f " % (adjustedgps2unix(adjustedgpsTime)))

	# print ("unixtime %3f TO gpsseconds %3f" % (unixtime, unix2gps(unixtime)))
	# print ("gpsseconds %3f TO unixtime %3f" % (gpsseconds, gps2unix(gpsseconds)))
	# print ("unixtime %3f TO gpsseconds %3f" % (unixtime, to_timestamp(from_UNIXtimestamp(unixtime))))
###############################################################################
def EXIF_to_DateTime(EXIFTimeTag):
	'''return a python date object from a split date and time record'''
	date_object = datetime.strptime(str(EXIFTimeTag), '%Y-%b-%d %H:%M:%S.%f')
	return date_object

def to_DateTime(recordDate, recordTime):
	'''return a python date object from a split date and time record'''
	date_object = datetime.strptime(str(recordDate), '%Y%m%d') + timedelta(0,recordTime)
	return date_object

def from_UNIXtimestamp(unixtime):
	return datetime(1970, 1 ,1) + timedelta(seconds=unixtime)

def from_GPStimestamp(gpstime):
	return datetime(1980, 1 ,6) + timedelta(seconds=gpstime)

def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()


# https://www.andrews.edu/~tzs/timeconv/timealgorithm.html
#// Define GPS leap seconds
def getleaps():
	leaps = [46828800, 78364801, 109900802, 173059203, 252028804, 315187205, 346723206, 393984007, 425520008, 457056009, 504489610, 551750411, 599184012, 820108813, 914803214, 1025136015, 1119744016, 1167264017]
	return leaps

###############################################################################
def isleap(gpsTime):
	'''Test to see if a GPS second is a leap second'''
	isLeap = False
	leaps = getleaps()
	# lenLeaps = count(leaps)
	for i in leaps:
		if (gpsTime == i):
			isLeap = True
	return isLeap

###############################################################################
def countleaps(gpsTime, dirFlag):
	'''Count number of leap seconds that have passed'''
	leaps = getleaps()
	# lenLeaps = count(leaps)
	nleaps = 0  #// number of leap seconds prior to gpsTime
	for i, leap in enumerate(leaps):
		if "unix2gps" in dirFlag:
			if (gpsTime >= leap - i):
				nleaps = nleaps + 1
		elif "gps2unix" in dirFlag:
			if (gpsTime >= leap):
				nleaps = nleaps + 1
		else:
			print ("ERROR Invalid Flag!")
	return nleaps

###############################################################################
def unix2gps(unixTime):
	'''Convert Unix Time to GPS Time'''
	#// Add offset in seconds
	if math.fmod(unixTime, 1) != 0:
		unixTime = unixTime - 0.5
		isLeap = 1
	else:
		isLeap = 0
	gpsTime = unixTime - 315964800
	nleaps = countleaps(gpsTime, 'unix2gps')
	gpsTime = gpsTime + nleaps + isLeap
	return gpsTime

###############################################################################
def gps2unix(gpsTime):
	'''Convert GPS Time to Unix Time'''
	#// Add offset in seconds
	unixTime = gpsTime + 315964800
	nleaps = countleaps(gpsTime, 'gps2unix')
	unixTime = unixTime - nleaps
	if isleap(gpsTime):
		unixTime = unixTime + 0.5
	return unixTime

###############################################################################
def unix2adjustedgps(unixTime, leapseconds=0):
	'''Convert Unix Time to ADJUSTED GPS Time. this is GPS time - 1 BILLION seconds.  used for LAZ files.'''
	#// Add offset in seconds
	# if math.fmod(unixTime, 1) != 0:
		# unixTime = unixTime - 0.5
		# isLeap = 1
	# else:
		# isLeap = 0
	gpsTime = unixTime - 315964800
	if leapseconds == 0:
		leapseconds = countleaps(gpsTime, 'unix2gps')
	#remove a billion seconds so it fits into a double nicely
	gpsTime = gpsTime + leapseconds - 1000000000
	# gpsTime = gpsTime + nleaps + isLeap - 1000000000
	return gpsTime

###############################################################################
def adjustedgps2unix(adjustedgpsTime, leapseconds=0):
	'''Convert adjusted GPS Time to Unix Time (gpstime - 1billion seconds)'''
	#// Add offset in seconds
	unixTime = adjustedgpsTime + 315964800 + 1000000000

	if leapseconds == 0:
		leapseconds = countleaps(unixTime, 'gps2unix')

	unixTime = unixTime - leapseconds
	# if isleap(adjustedgpsTime):
		# unixTime = unixTime + 0.5
	return unixTime


###################################################################################################
if __name__ == "__main__":
		main()