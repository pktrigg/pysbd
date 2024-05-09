import sys
import os
import numpy as np
import math
from datetime import datetime, timedelta

# local imports
import geodetic
from timeutils import adjustedgps2unix, unix2adjustedgps
import refraction


###############################################################################
def computebathypointcloudmrz(datagram, geo):
	'''using the MRZ datagram, efficiently compute a numpy array of the point clouds  '''
	# print("time, %s Longitude %.10f Latitude %.10f" % (datagram.date, datagram.longitude, datagram.latitude))
	for beam in datagram.beams:
		beam.east, beam.north = geo.convertToGrid((datagram.longitude + beam.deltaLongitude_deg ), (datagram.latitude + beam.deltaLatitude_deg))
		# beam.depth = beam.z_reRefPoint_m - datagram.txTransducerDepth_m
		beam.depth = (beam.z_reRefPoint_m - datagram.z_waterLevelReRefPoint_m) * -1.0
		beam.depth = beam.z_reRefPoint_m * -1.0
		beam.depth = beam.depth + datagram.ellipsoidHeightReRefPoint_m
		# datagram.z_waterLevelReRefPoint_m seems to be the CRP to transducer depth difference due to lever arm pitch and roll
		# beam.depth = beam.z_reRefPoint_m - datagram.z_waterLevelReRefPoint_m

		beam.id 	= datagram.pingCnt
	npeast = np.fromiter((beam.east for beam in datagram.beams), float, count=len(datagram.beams)) 
	npnorth = np.fromiter((beam.north for beam in datagram.beams), float, count=len(datagram.beams)) 
	npdepth = np.fromiter((beam.depth for beam in datagram.beams), float, count=len(datagram.beams)) 
	npintensity = np.fromiter((beam.reflectivity1_dB for beam in datagram.beams), float, count=len(datagram.beams)) 
	npq = np.fromiter((beam.rejectionInfo1 for beam in datagram.beams), float, count=len(datagram.beams)) 
	npa = np.fromiter((beam.beamAngleReRx_deg for beam in datagram.beams), float, count=len(datagram.beams)) 
	npt = np.fromiter((unix2adjustedgps(beam.timestamp) for beam in datagram.beams), float, count=len(datagram.beams)) 
	
	# we can now comput absolute positions from the relative positions
	# npLatitude_deg = npdeltaLatitude_deg + datagram.latitude_deg	
	# npLongitude_deg = npdeltaLongitude_deg + datagram.longitude_deg
	return (npt, npa, npeast, npnorth, npdepth, npintensity, npq)


def from_timestamp(unixtime):
	return datetime.utcfromtimestamp(unixtime)

###############################################################################
def computebathypointcloudbth(BTHDatagram, sensordata, sensorinstallation, geo):
	'''using the R2Sonic BTH0 datagram, efficiently compute a numpy array of the point clouds  '''
	
	depth_velocity_profile = [(0, 1500), (100, 1500), (5000, 1500)]  # Example profile

	# for all the beams in the decoded datagram compute the depth
	pitch			= sensordata['pitch']
	roll			= sensordata['roll']
	gyro			= sensordata['gyro']
	timestamp 		= sensordata['timestamp']
	speedsound 		= BTHDatagram.H0['H0_SoundSpeed']
	position1		= [sensordata['easting'], sensordata['northing'], sensordata['depth']]

	for idx, angle in enumerate(BTHDatagram.angles):
		#convert from traveltime to dxy...
		# depth, acrosstrack = refraction.ray_trace_to_time(BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth_velocity_profile)
		# depth, acrosstrack = refraction.ray_trace_to_time(BTHDatagram.angles[idx] - math.radians(sensordata['roll']), BTHDatagram.ranges[idx], depth_velocity_profile)
		#convert from traveltime to range using a SVP at head
		range = BTHDatagram.ranges[idx] * 0.5 * speedsound
		# range = BTHDatagram.ranges[idx] * speedsound

		# sensorinstallation.offsetroll
		offset=[0,0,range]
		#checked if we should subtract or add the instant roll   for sure it is ADD
		roll = 180 - math.degrees(BTHDatagram.angles[idx]) + sensorinstallation.offsetroll + sensordata['roll']
		# pitch = sensorinstallation.offsetpitch
		dxyz = geodetic.rotate3d(offset, -1.0 * sensordata['pitch'], roll, 0)

		# print("Beam %d Angle %.3f Range %.3f Depth %.3f acrosstrack %.3f " % (idx, BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth, acrosstrack))
		# using the  sensor gyro, easting, northing compute the positon on the sealfoor
		# offset=[dxyz[0],0,dxyz[2]]
		newcoordinates = geodetic.rotate3d(dxyz, 0, 0, gyro)
		position2 = [position1[0]+newcoordinates[0], position1[1]+newcoordinates[1], position1[2] + ( -1.0 * newcoordinates[2]) ]

		BTHDatagram.east.append(position2[0])
		BTHDatagram.north.append(position2[1])
		BTHDatagram.depth.append(-1.0 * position2[2])
		BTHDatagram.timestamp.append(timestamp)
		# print (newcoordinates)
		# print (position2)

	# now convert from east north to geographicals
	# for idx, east in enumerate(BTHDatagram.east):
	# 	BTHDatagram.east[idx], BTHDatagram.north[idx] = geo.convertToGeographicals(BTHDatagram.east[idx], BTHDatagram.north[idx])

	npeast = np.array(BTHDatagram.east)
	npnorth = np.array(BTHDatagram.north)
	npdepth = np.array(BTHDatagram.depth)
	npt = np.fromiter((unix2adjustedgps(timestamp) for timestamp in BTHDatagram.timestamp), float, count=BTHDatagram.pointcount) 

	npintensity = np.zeros(BTHDatagram.pointcount) # npdepth
	npq = np.zeros(BTHDatagram.pointcount)
	npa = np.zeros(BTHDatagram.pointcount) # np.array(BTHDatagram.angles) #needs to be in degrees


	# npeast = np.fromiter((BTHDatagram.east for beam in BTHDatagram.east), float, count=len(BTHDatagram.pointcount)) 
	# npnorth = np.fromiter((BTHDatagram.north for beam in BTHDatagram.pointcount), float, count=len(BTHDatagram.pointcount)) 
	# npdepth = np.fromiter((BTHDatagram.depth for beam in BTHDatagram.pointcount), float, count=len(BTHDatagram.pointcount)) 
	# npintensity = np.fromiter((beam.reflectivity1_dB for beam in BTHDatagram.pointcount), float, count=len(BTHDatagram.pointcount)) 
	# npq = np.fromiter((beam.rejectionInfo1 for beam in BTHDatagram.pointcount), float, count=len(BTHDatagram.pointcount)) 
	# npa = np.fromiter((beam.beamAngleReRx_deg for beam in BTHDatagram.pointcount), float, count=len(BTHDatagram.pointcount)) 
	# npt = np.fromiter((unix2adjustedgps(beam.timestamp) for beam in BTHDatagram.pointcount), float, count=len(BTHDatagram.pointcount)) 

	return (npt, npa, npeast, npnorth, npdepth, npintensity, npq)

###############################################################################
class Cpointcloud:
	'''class to hold a point cloud'''
	# xarr = np.empty([0], dtype=float)
	# yarr = np.empty([0], dtype=float)
	# zarr = np.empty([0], dtype=float)
	# qarr = np.empty([0], dtype=float)

	# self.xarr = []
	# self.yarr = []
	# self.zarr = []
	# self.qarr = []
	# self.idarr = []

	###############################################################################
	def __init__(self, npx=None, npy=None, npz=None, npi=None, npq=None, npid=None):
		'''add the new ping of data to the existing array '''
		# np.append(self.xarr, np.array(npx))
		# np.append(self.yarr, np.array(npy))
		# np.append(self.zarr, np.array(npz))
		# np.append(self.qarr, np.array(npq))
		# np.append(self.idarr, np.array(npid))
		self.tarr = [] # timestamps
		self.aarr = [] # beam angle
		self.xarr = [] # easting
		self.yarr = [] # northing
		self.zarr = [] # depth
		self.iarr = [] # intensity
		self.qarr = [] # quality
		# idarr = []
		# self.xarr = np.array(npx)
		# self.yarr = np.array(npy)
		# self.zarr = np.array(npz)
		# self.qarr = np.array(npq)
		# self.idarr = np.array(npid)

	###############################################################################
	def add(self, npt, npa, npx, npy, npz, npi, npq):
		'''add the new ping of data to the existing array '''
		# self.xarr = np.append(self.xarr, np.array(npx))
		# self.yarr = np.append(self.yarr, np.array(npy))
		# self.zarr = np.append(self.zarr, np.array(npz))
		# self.qarr = np.append(self.zarr, np.array(npq))
		self.tarr.extend(npt)
		self.aarr.extend(npa)
		self.xarr.extend(npx)
		self.yarr.extend(npy)
		self.zarr.extend(npz)
		self.iarr.extend(npi)
		self.qarr.extend(npq)
		# self.idarr.extend(npid)

# ###############################################################################
# def despike_point_cloud(points, eps, min_samples):
# 	"""Despike a point cloud using DBSCAN."""
# 	clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(points)
# 	labels = clustering.labels_
# 	filtered_points = points[labels != -1]
# 	rejected_points = points[labels == -1]
    
# 	print("EPS: %f MinSample: %f Rejected: %d Survivors: %d InputCount %d" % (eps,  min_samples, len(rejected_points), len(filtered_points), len(points)))
# 	return rejected_points

