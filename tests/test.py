import os
import sys
from pathlib import Path
from datetime import datetime

# when developing locally use this...
sys.path.append(str(Path(__file__).parent.parent / "src/sbd_survey"))
import sbd
import r2sonicdecode
import refraction

# # when installed use this...
# from sbd_survey import sbd
# from sbd_survey import r2sonicdecode
# from sbd_survey import refraction

###############################################################################
def main():
	'''here is a test script to demonstrate the use of sbd'''
	
	filename = "J355N001.SBD"
	#open the SBD file for reading by creating a new SBDFReader class and passin in the filename to open.  The reader will read the initial header so we can get to grips with the file contents with ease.
	# print ( "Processing file:", filename)
	if os.path.exists(filename) == False:
		print("File not found:", filename)
		return	
	
	reader = sbd.SBDReader(filename)
	reader.SBDfilehdr.printsensorconfiguration()

	while reader.moreData():
		category, decoded = reader.readdatagram()
		if category == reader.GYRO:
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))

		if category == reader.MOTION: # 3
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Motion: %s %.3f %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['roll'], sensor['pitch'], sensor['heave']))
		
		if category == reader.BATHY:  # 4
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Depth: %s %.3f" % (from_timestamp(msgtimestamp), sensor['depth']))

		if category == reader.POSITION: # 8
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))

		if category == reader.ECHOSOUNDER: # 9
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Echosounder: %s %s " % (sensor['mbesname'], from_timestamp(msgtimestamp)))
			if rawdata[0:4] == b'BTH0':
				#this is how we decode the BTH0 datagram from r2sonic 
				BTHDatagram = r2sonicdecode.BTH0(rawdata)
				depth_velocity_profile = [(0, 1500), (100, 1500), (200, 1500)]  # Example profile

				# for all the beams in the decoded datagram compute the depth
				for idx, angle in enumerate(BTHDatagram.angles):
					depth, acrosstrack = refraction.ray_trace_to_time(BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth_velocity_profile)
					# print("Beam %d Angle %.3f Range %.3f Depth %.3f acrosstrack %.3f " % (idx, BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth, acrosstrack))
					# using the  sensor gyro, easting, northing compute the positon on the sealfoor
					# print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))
					# print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))

	navigation = reader.loadNavigation()
	# for n in navigation:
		# print ("Date %s X: %.10f Y: %.10f Hdg: %.3f" % (from_timestamp(n[0]), n[1], n[2], n[3]))

	reader.close()
	print("Complete reading SBD file :-)")

###############################################################################
# TIME HELPER FUNCTIONS
###############################################################################
def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()

def from_timestamp(unixtime):
	return datetime.utcfromtimestamp(unixtime)

#########################################################################################
#########################################################################################
if __name__ == "__main__":
	main()
