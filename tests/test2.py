import os
import sys
import time
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser

# when developing locally use this...
sys.path.append(str(Path(__file__).parent.parent / "src/sbd_survey"))
import sbd
import r2sonicdecode
# import refraction
import fileutils

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

	for filename in files:
		sbd.process(filename)	

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
