import os
import sys
import time
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser
import numpy as np
import subprocess
import shlex
import ctypes
# import multiprocessing
import multiprocessing as mp
# from ctypes import wintypes
from datetime import timedelta

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
import delivershared as ds

#class used to display the progress
g_procprogress = ds.CPROGRESS(0)

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
	parser.add_argument('-ds', 		dest='bathysensorid', 		action='store', 		default="1", help='Specify the depth sensor to use [default = 0],e.g. -ds 0')
	parser.add_argument('-gs', 		dest='gyrosensorid', 		action='store', 		default="0", help='Specify the gyro sensor to use [default = 0],e.g. -ds 0')
	parser.add_argument('-ps', 		dest='positionsensorid', 		action='store', 		default="0", help='Specify the position sensor to use [default = 0],e.g. -ds 0')
	parser.add_argument('-ms', 		dest='motionsensorid', 		action='store', 		default="0", help='Specify the motion sensor to use [default = 0],e.g. -ds 0')
	parser.add_argument('-s', 		dest='summary', 		action='store_true', 		default=False, help='Scan the files and make a summary of the sensors and sensor,e.g. -s')
	parser.add_argument('-cpu', 		dest='cpu', 		action='store', 		default='0', 	help='number of cpu processes to use in parallel. [Default: 0, all cpu]')
	
	args = parser.parse_args()

	if args.inputfolder == '.':
		args.inputfolder = os.getcwd()

	if os.path.isdir(args.inputfolder):
		files = fileutils.findFiles2(False, args.inputfolder, "*.sbd")
	else:
		files = [args.inputfolder]
		args.inputfolder = os.path.dirname(args.inputfolder)

	geo = geodetic.geodesy(EPSGCode=args.epsg)

	# for filename in files:
		# process(args, geo, filename)	

	tasks = []
	update_progress("Converting SBD to LAZ", (0))
	for idx, filename in enumerate(files):
		# root = os.path.splitext(os.path.expanduser(os.path.basename(filename)))[0]
		# lasoutfilename = os.path.join(os.path.dirname(filename), root + ".las").replace('\\','/')
		# lazoutfilename = os.path.join(os.path.dirname(filename), root + ".laz").replace('\\','/')
		
		# the file exists so skip it to make things faster
		# if os.path.exists(lazoutfilename):
		# 	continue

		tasks.append([args, geo, filename])
		# gsf2las.convert(filename, outfilename, args.epsg)	
		# update_progress("Converting GSF to LAS", (1))
	args.cpu = '1'

	if args.cpu == '1':
		for idx, task in enumerate(tasks):
			sbd2las(task[0], task[1], task[2])
			update_progress("Converting SBD to LAS", (idx/len(files)))
		update_progress("Converting SBD to LAS", (1))
	else:
		update_progress("Converting SBD to LAS", (0.01))
		cpu = ds.getcpucount(args.cpu)
		print("Converting %d SBD to LAS... with %d CPU's" % (len(files), cpu))
		pool = mp.Pool(cpu)
		g_procprogress.setmaximum(len(tasks))

		poolresults = [pool.apply_async(sbd2las, (task[0], task[1], task[2], idx/len(tasks)), callback= advanceprogress) for idx, task in enumerate(tasks)]
		
		pool.close()
		pool.join()
		update_progress("Converting GSF to LAS", (1))

# ################################################################################
# def getcpucount(requestedcpu):
# 	'''control how many CPU's we use for multi processing'''
# 	if int(requestedcpu) == 0:
# 		requestedcpu = multiprocessing.cpu_count()

# 		stat = MEMORYSTATUSEX()
# 		ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
# 		# print("MemoryLoad: %d%%" % (stat.dwMemoryLoad))
# 		# print("MemoryAvailable: %d%%" % (stat.ullAvailPhys/(1024*1024*1024)))
# 		availablememoryingigs = stat.ullAvailPhys/(1024*1024*1024)
# 		# make sure we have enough memory per CPU
# 		requiredgigspercpu = 4

# 		maxcpu = max(1, int(availablememoryingigs/ requiredgigspercpu))
# 		# ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
# 		# print("MemoryLoad: %d%%" % (stat.dwMemoryLoad))
# 		# ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
# 		# print("MemoryLoad: %d%%" % (stat.dwMemoryLoad))
# 		# ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
# 		# print("MemoryLoad: %d%%" % (stat.dwMemoryLoad))
# 		# ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
# 		# print("MemoryLoad: %d%%" % (stat.dwMemoryLoad))

# 		if int(requestedcpu) > maxcpu:
# 			requestedcpu = maxcpu
# 	return int(requestedcpu)


################################################################################
def advanceprogress(result):
	# print(result)
	update_progress("Converting SBD to LAS", result)	

###############################################################################
def sbd2las(args, geo, filename, taskid=0):
	#open the SBD file for reading by creating a new SBDFReader class and passin in the filename to open.  The reader will read the initial header so we can get to grips with the file contents with ease.
	
	print ( "Processing file:", filename)
	reader = sbd.SBDReader(filename)
	reader.SBDfilehdr.printsensorconfiguration()
	if args.summary:
		reader.summarise()
		return

	print ("Processing with Position Sensor:	%s" % (reader.SBDfilehdr.sensorsbycategory[reader.POSITION][int(args.positionsensorid)].name))
	print ("Processing with Bathy Sensor:		%s" % (reader.SBDfilehdr.sensorsbycategory[reader.BATHY][int(args.bathysensorid)].name))
	print ("Processing with Gyro Sensor:		%s" % (reader.SBDfilehdr.sensorsbycategory[reader.GYRO][int(args.gyrosensorid)].name))
	print ("Processing with Motion Sensor:		%s" % (reader.SBDfilehdr.sensorsbycategory[reader.MOTION][int(args.motionsensorid)].name))

	start_time = time.time() # time  the process

	# now extract the navigation so we can correctly place the pings and beams as the ping coordinates only update when new navigation appears
	nav = reader.loadnavigation(bathysensorid = int(args.bathysensorid), positionsensorid = int(args.positionsensorid), gyrosensorid = int(args.gyrosensorid), motionsensorid = int(args.motionsensorid))
	# extract the first filed in the list into a timestamp list
	timestamps = [float(i[0]) for i in nav]
	# convert all coordinates in the navigation list into easting northing using geo.convertToGrid
	for idx, n in enumerate(nav):
		x, y = geo.convertToGeographicals(n[1], n[2])
		nav[idx][1] = x
		nav[idx][2] = y

	# get the sensor offsets
	sensor = reader.SBDfilehdr.sensorsbycategory[reader.BATHY][int(args.bathysensorid)]
	
	list_x = [i[1] for i in nav]
	list_y = [i[2] for i in nav]

	#the depth sensor might not be colocated to the MBES so lets compute the depth at the MBES using the sensor offsets
	offset	=[sensor.offsetx, sensor.offsety, sensor.offsetz]
	pitch	= 1
	roll	= 0
	heading	= 0
	newcoordinates = geodetic.rotate3d(offset, pitch, roll, heading)

	list_z = [(-1.0 * i[3]) for i in nav]

	tsx = timeseries.cTimeSeries(timestamps, list_x)
	tsy = timeseries.cTimeSeries(timestamps, list_y)
	tsz = timeseries.cTimeSeries(timestamps, list_z)

	print("Loading Point Cloud...")
	pointcloud = mbes.Cpointcloud()

	while reader.moreData():
		category, sensorid, decoded = reader.readdatagram()
		# if category == reader.BATHY:  # 4
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Depth: %s %.3f" % (from_timestamp(msgtimestamp), sensor['depth']))

		if category == reader.ECHOSOUNDER: # 9
			msgtimestamp, sensordata, rawdata = decoded
			# print("Echosounder: %s %s " % (sensor['mbesname'], from_timestamp(msgtimestamp)))
			if rawdata[0:4] == b'BTH0':
				print("R2sonic Echosounder located: %s %s " % (sensordata['mbesname'], from_timestamp(msgtimestamp)))
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
				# we need to replace the realtime navigation with interpolated positions so thebeams are better georeferenced
				mrz.longitude = tsx.getValueAt(mrz.timestamp)
				mrz.latitude = tsy.getValueAt(mrz.timestamp)
				mrz.ellipsoidHeightReRefPoint_m = tsz.getValueAt(mrz.timestamp)
				# #only replace if valid.  this happens at start and end of file if depth sensor is slow update
				# if rovdepth < 0:
				# 	mrz.ellipsoidHeightReRefPoint_m = rovdepth
				t, a, x, y, z, i, q = mbes.computebathypointcloud(mrz, geo)
				pointcloud.add(t, a, x, y, z, i, q)

				# if the process duration is greater than 1 second then update the progress bar
				update_progress("Creating Point Cloud", reader.fileptr.tell() / reader.filesize)
				
				# if int(time.time() - start_time)  > 2:
					# break

	reader.close()

	# setup a las file for export...
	pointsourceID 		= 1
	outfilename = fileutils.replacesuffix(filename, ".las")
	# outfilename = os.path.splitext(filename)[0] + '.laz'
	# outfilename = fileutils.createoutputfilename(filename, ".las")
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

	#we need to fit the backscatter into 16 bit integer field so lets maximise the precision
	#reflectivity is normall a negative number in the 0-100 range so we can multiply by 100 to keep the details
	writer.intensity = np.round(pointcloud.iarr,decimals = 3)
	writer.intensity = np.multiply(writer.intensity, -100)
	writer.intensity = np.clip(writer.intensity, 0, 64000)
	writer.intensity = np.int16(writer.intensity).tolist()

	writer.gpstime = np.array(pointcloud.tarr)
	# writer.scanangle = np.array(pointcloud.aarr)

	# writer.z = np.multiply(-1.0, np.round(pointcloud.zarr,decimals = 3)).tolist()
	writer.computebbox_offsets()
	writer.writepoints()

	# we need to write the header after writing records so we can update the bounding box, point format etc 
	writer.writeHeader()
	writer.close()

	#replace filename suffix with .laz
	import os

	outfilenamelaz = zip(outfilename)
	if os.path.exists(outfilenamelaz):
		os.remove(outfilename)
	print("Complete reading SBD file :-) %s " % (outfilename))
	print ("Duration %.3fs" % (time.time() - start_time)) # print the processing time.

	return taskid
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

	outfilename = os.path.splitext(filespec)[0] + '.laz'
	cmd = "laszip.exe" + \
		" -i %s" % (filespec) + \
		" -o %s" % (outfilename) + \
		" -cores 4" + \
		" -olaz "

	stdout, stderr = runner(cmd, False)

	return outfilename

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

# ###############################################################################
# class CPROGRESS(object):
# 	'''thread safe class to display progress in command window when in multiprocess mode'''
# 	# procprogress = CPROGRESS(1000)
# 	# for i in range(1000):
# 	# 	time.sleep(0.01)
# 	# 	procprogress.increment_progress("test", i)

# 	###########################################################################
# 	def __init__(self, maxcount=100):
# 		self.length = 20 # modify this to change the length
# 		self.maxcount = max(maxcount,1)
# 		# self.progress = 0
# 		self.stime = datetime.now()
# 		self.value = 0
# 		self.msg = "Progress:"

# 	###########################################################################
# 	def setmaximum(self, value, current=0):
# 		self.maxcount = value
# 		self.value = current
# 		self.stime = datetime.now()

# 	###########################################################################
# 	def increment_progress(self, msg="", value=0):
		
# 		if len(str(msg)) > 0:
# 			self.msg = msg

# 		if value == 0:
# 			self.value = self.value + 1
# 		else:
# 			self.value = value

# 		progress = self.value/self.maxcount
		
# 		# print(value)
# 		secondsconsumed = (datetime.now() - self.stime).total_seconds()
# 		secondsperitem = secondsconsumed / max(self.value,1)
# 		secondsremaining = int((self.maxcount - self.value) * secondsperitem)
# 		timeremaining = str(timedelta(seconds=secondsremaining))
# 		block = int(round(self.length*progress))
# 		msg = "\r{0}: [{1}] {2:2.2f}% Remaining: {3}".format(self.msg, "#"*block + "-"*(self.length-block), round(progress*100, 2), timeremaining)
# 		if progress >= 1: msg += " DONE\r\n"
# 		sys.stdout.write(msg)
# 		sys.stdout.flush()

# 	###########################################################################
# 	def complete(self, msg):
# 		length = 20 # modify this to change the length
# 		progress = 1
# 		block = int(round(length*progress))
# 		msg = "\r{0}: [{1}] {2}%".format(msg, "#"*block + "-"*(length-block), round(progress*100, 2))
# 		if progress >= 1: msg += " DONE\r\n"
# 		sys.stdout.write(msg)
# 		sys.stdout.flush()

# #########################################################################################
# class MEMORYSTATUSEX(ctypes.Structure):
# 	_fields_ = [
# 		("dwLength", ctypes.c_ulong),
# 		("dwMemoryLoad", ctypes.c_ulong),
# 		("ullTotalPhys", ctypes.c_ulonglong),
# 		("ullAvailPhys", ctypes.c_ulonglong),
# 		("ullTotalPageFile", ctypes.c_ulonglong),
# 		("ullAvailPageFile", ctypes.c_ulonglong),
# 		("ullTotalVirtual", ctypes.c_ulonglong),
# 		("ullAvailVirtual", ctypes.c_ulonglong),
# 		("sullAvailExtendedVirtual", ctypes.c_ulonglong),
# 	]

# 	def __init__(self):
# 		# have to initialize this to the size of MEMORYSTATUSEX
# 		self.dwLength = ctypes.sizeof(self)
# 		super(MEMORYSTATUSEX, self).__init__()
#########################################################################################
#########################################################################################
if __name__ == "__main__":
	main()
