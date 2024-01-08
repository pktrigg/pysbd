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
	#open the SBD file for reading by creating a new SBDFReader class and passin in the filename to open.  we can then summarise the contents of the file.
	# filename
	# start, end, duration
	# sensor table
	# number of packets of each sensor type
	# logging rate in mBps megabytes per second
	# length of survey coverage in metres
	
	print ( "Processing file:", filename)
	reader = sbd.SBDReader(filename)
	reader.summarise()
	
	start_time = time.time() # time  the process

	# now extract the navigation so we can correctly place the pings and beams as the ping coordinates only update when new navigation appears
	nav, nav2 = reader.loadnavigation()

	# calculate the line length from the first and last navigation records
	print("First Nav Record: %s %.3f %.3f" % (from_timestamp(nav[0][0]), nav[0][1], nav[0][2]))
	print("Last Nav Record: %s %.3f %.3f" % (from_timestamp(nav[-1][0]), nav[-1][1], nav[-1][2]))
	print("Line Length: %.3f, Bearing %.3f" % (geo.calculateRangeBearingFromGrid(nav[0][1], nav[0][2], nav[-1][1], nav[-1][2])))
	
	duration = (nav[-1][0] - nav[0][0])
	print("Aquisition Duration: %.3f seconds" % (duration))
	print("Logging Rate: %.3f MegaBYTES per second" % (reader.filesize / duration / 1024 / 1024))

	while reader.moreData():
		category, decoded = reader.readdatagram()
		sensorid = decoded[0]
		if sensorid is not None:
			reader.SBDfilehdr.sensorsbycategory[category][sensorid].recordcount += 1

		# print(category)
		# if category == reader.GYRO:
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))
		# 	reader.SBDFILEHDR.sensorcategory['category'][sensorid] += 1

		# if category == reader.MOTION: # 3
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Motion: %s %.3f %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['roll'], sensor['pitch'], sensor['heave']))
		
		# if category == reader.BATHY:  # 4
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Depth: %s %.3f" % (from_timestamp(msgtimestamp), sensor['depth']))

		# if category == reader.POSITION: # 8
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))

		# if category == reader.ECHOSOUNDER: # 9
		# 	sensorid, msgtimestamp, sensor, rawdata = decoded
		# 	# print("Echosounder: %s %s " % (sensor['mbesname'], from_timestamp(msgtimestamp)))

		# if the process duration is greater than 1 second then update the progress bar
		update_progress("Scanning", reader.fileptr.tell() / reader.filesize)
				
		# if int(time.time() - start_time)  > 5:
		# 	break

	reader.close()


	print("Complete reading SBD file :-) %s " % (filename))
	print ("Duration %.3fs" % (time.time() - start_time)) # print the processing time.

	reader.SBDfilehdr.printsensorconfiguration()

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
