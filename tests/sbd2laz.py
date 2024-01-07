import os
import sys
import time
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser
import numpy as np
import subprocess
import shlex

# when developing locally use this...
sys.path.append(str(Path(__file__).parent.parent / "src/sbd_survey"))
import sbd
# import r2sonicdecode
# import refraction
import fileutils
import kmall
import mbes
import geodetic
import pylasfile
import timeseries

# # when installed use this...
# from sbd_survey import sbd
# from sbd_survey import fileutils
# from sbd_survey import r2sonicdecode
# from sbd_survey import refraction


###############################################################################
def main():

	parser = ArgumentParser(description='\n * Process one or many group folders.')
	parser.add_argument('-i', 			dest='inputfolder', action='store', 		default='.',	help='the root folder to find one more more group folders. Pease refer to procedure for the group folder layout - e.g. c:/mysurveyarea')
	parser.add_argument('-epsg', 		dest='epsg', 		action='store', 		default="", help='Specify an output EPSG code for transforming from WGS84 to East,North,e.g. -epsg 4326')
	
	args = parser.parse_args()

	if args.inputfolder == '.':
		args.inputfolder = os.getcwd()

	if os.path.isdir(args.inputfolder):
		files = fileutils.findFiles2(False, args.inputfolder, "*.sbd")
	else:
		files = [args.inputfolder]
		args.inputfolder = os.path.dirname(args.inputfolder)

	geo = geodetic.geodesy(EPSGCode=args.epsg)

	for filename in files:
		process(geo, filename)	

###############################################################################
def process (geo, filename):
	#open the SBD file for reading by creating a new SBDFReader class and passin in the filename to open.  The reader will read the initial header so we can get to grips with the file contents with ease.
	
	# print ( "Processing file:", filename)
	reader = sbd.SBDReader(filename)
	reader.SBDfilehdr.printsensorconfiguration()

	start_time = time.time() # time  the process

	# now extract the navigation so we can correctly place the pings and beams as the ping coordinates only update when new navigation appears
	nav, nav2 = reader.loadnavigation()
	# extract the first filed in the list into a timestamp list
	timestamps = [float(i[0]) for i in nav]
	# convert all coordinates in the navigation list into easting northing using geo.convertToGrid
	for idx, n in enumerate(nav):
		x, y = geo.convertToGeographicals(n[1], n[2])
		nav[idx][1] = x
		nav[idx][2] = y

	list_x = [i[1] for i in nav]
	list_y = [i[2] for i in nav]
	tsx = timeseries.cTimeSeries(timestamps, list_x)
	tsy = timeseries.cTimeSeries(timestamps, list_y)


	print("Loading Point Cloud...")
	pointcloud = mbes.Cpointcloud()

	while reader.moreData():
		category, decoded = reader.readdatagram()
		# print(category)
		# if category == reader.GYRO:
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))

		# if category == reader.MOTION: # 3
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Motion: %s %.3f %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['roll'], sensor['pitch'], sensor['heave']))
		
		# if category == reader.BATHY:  # 4
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Depth: %s %.3f" % (from_timestamp(msgtimestamp), sensor['depth']))

		# if category == reader.POSITION: # 8
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))

		if category == reader.ECHOSOUNDER: # 9
			sensorid, msgtimestamp, sensor, rawdata = decoded
			# print("Echosounder: %s %s " % (sensor['mbesname'], from_timestamp(msgtimestamp)))
			if rawdata[0:4] == b'BTH0':
				print("R2sonic Echosounder located: %s %s " % (sensor['mbesname'], from_timestamp(msgtimestamp)))
				#this is how we decode the BTH0 datagram from r2sonic 
				# BTHDatagram = r2sonicdecode.BTH0(rawdata)
				# depth_velocity_profile = [(0, 1500), (100, 1500), (200, 1500)]  # Example profile

				# for all the beams in the decoded datagram compute the depth
				# for idx, angle in enumerate(BTHDatagram.angles):
					# depth, acrosstrack = refraction.ray_trace_to_time(BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth_velocity_profile)
					# print("Beam %d Angle %.3f Range %.3f Depth %.3f acrosstrack %.3f " % (idx, BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth, acrosstrack))
					# using the  sensor gyro, easting, northing compute the positon on the sealfoor
					# print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))
					# print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))
			if rawdata[4:8] == b'#MRZ':
				#print("Kongsberg EM KMALL Echosounder located: %s %s " % (sensor['mbesname'], from_timestamp(msgtimestamp)))
				# lets decode the MRZ datagram...
				mrz = kmall.RANGEDEPTH(None, 0)
				mrz.decode(rawdata)
				# print(datagram)
				mrz.longitude = tsx.getValueAt(to_timestamp(mrz.date))
				mrz.latitude = tsy.getValueAt(to_timestamp(mrz.date))
				x, y, z, i, q = mbes.computebathypointcloud(mrz, geo)
				pointcloud.add(x, y, z, i, q)

				# if the process duration is greater than 1 second then update the progress bar
				update_progress("Creating Point Cloud", reader.fileptr.tell() / reader.filesize)
				
				# if int(time.time() - start_time)  > 5:
				# 	break


			#debug to make it quick
			# if (time.time() - start_time) > 20:
	reader.close()

	# setup a las file for export...
	pointsourceID 		= 1
	outfilename = fileutils.createoutputfilename(filename, ".las")
	writer = pylasfile.laswriter(outfilename, 1.4)
	writer.hdr.FileSourceID = pointsourceID
	# get the wkt from the geo definition

	# write out a WGS variable length record so users know the coordinate reference system

	writer.writeVLR_WKT(geo.getwkt())
	# writer.writeVLR_WGS84()
	writer.hdr.PointDataRecordFormat = 1

	writer.x = np.round(pointcloud.xarr,decimals = 3).tolist()
	writer.y = np.round(pointcloud.yarr,decimals = 3).tolist()
	writer.z = np.round(pointcloud.zarr,decimals = 3).tolist()
	writer.intensity = np.round(pointcloud.iarr,decimals = 3).tolist()

	# writer.z = np.multiply(-1.0, np.round(pointcloud.zarr,decimals = 3)).tolist()
	writer.computebbox_offsets()
	writer.writepoints()

	# we need to write the header after writing records so we can update the bounding box, point format etc 
	writer.writeHeader()
	writer.close()

	#replace filename suffix with .laz
	import os

	outfilename = zip(outfilename)
	print("Complete reading SBD file :-) %s " % (outfilename))
	print ("Duration %.3fs" % (time.time() - start_time)) # print the processing time.

####################################################################################################################

###############################################################################
# TIME HELPER FUNCTIONS
###############################################################################
def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()

def from_timestamp(unixtime):
	return datetime.utcfromtimestamp(unixtime)

###############################################################################
def update_progress(job_title, progress):
	'''progress value should be a value between 0 and 1'''
	length = 20 # modify this to change the length
	block = int(round(length*progress))
	msg = "\r{0}: [{1}] {2}%".format(job_title, "#"*block + "-"*(length-block), round(progress*100, 2))
	if progress >= 1: msg += " DONE\r\n"
	sys.stdout.write(msg)
	sys.stdout.flush()

###############################################################################
def zip(filespec):
	'''zip every las file'''

	outfilename = os.path.splitext(outfilename)[0] + '.laz'
	cmd = "laszip.exe" + \
		" -i %s" % (filespec) + \
		" -o %s" % (outfilename) + \
		" -cores 4" + \
		" -olaz "

	stdout, stderr = runner(cmd, False)

	return

###############################################################################
def runner(cmd, verbose=False):
	'''process runner method.  pass the command to run and True if you want to real time verbose output of errors'''

	cmdname = cmd.split(" ")

	# ds.log('Processing command %s' % (cmdname))

	args = shlex.split(cmd)

	stdout = []
	stderr = []
	popen = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True, stderr=subprocess.PIPE)
	for stderr_line in iter(popen.stderr.readline, ""):
		stderr.append(stderr_line)
		if verbose:
			print(stderr_line.rstrip())
	for stdout_line in iter(popen.stdout.readline, ""):
		stdout.append(stdout_line)
	popen.stdout.close()
	popen.stderr.close()

	popen.wait()

	return [stdout, stderr]

#########################################################################################
#########################################################################################
if __name__ == "__main__":
	main()
