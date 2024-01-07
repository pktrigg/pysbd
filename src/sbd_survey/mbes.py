import sys
import os
import numpy as np

# local imports
import geodetic

###############################################################################
def computebathypointcloud(datagram, geo):
	'''using the MRZ datagram, efficiently compute a numpy array of the point clouds  '''
	# print("time, %s Longitude %.10f Latitude %.10f" % (datagram.date, datagram.longitude, datagram.latitude))
	for beam in datagram.beams:
		# tested subracting the delta.  its not the way
		beam.east, beam.north = geo.convertToGrid((datagram.longitude + beam.deltaLongitude_deg ), (datagram.latitude + beam.deltaLatitude_deg))
		#this looks like a heave artefact
		# beam.depth = beam.z_reRefPoint_m - datagram.txTransducerDepth_m
		beam.depth = (beam.z_reRefPoint_m - datagram.z_waterLevelReRefPoint_m) * -1.0
		beam.depth = beam.depth + datagram.ellipsoidHeightReRefPoint_m

		# beam.depth = beam.z_reRefPoint_m - datagram.z_waterLevelReRefPoint_m
		beam.id 	= datagram.pingCnt
	npeast = np.fromiter((beam.east for beam in datagram.beams), float, count=len(datagram.beams)) 
	npnorth = np.fromiter((beam.north for beam in datagram.beams), float, count=len(datagram.beams)) 
	npdepth = np.fromiter((beam.depth for beam in datagram.beams), float, count=len(datagram.beams)) 
	npintensity = np.fromiter((beam.reflectivity1_dB for beam in datagram.beams), float, count=len(datagram.beams)) 
	npq = np.fromiter((beam.rejectionInfo1 for beam in datagram.beams), float, count=len(datagram.beams)) 

	# we can now comput absolute positions from the relative positions
	# npLatitude_deg = npdeltaLatitude_deg + datagram.latitude_deg	
	# npLongitude_deg = npdeltaLongitude_deg + datagram.longitude_deg
	return (npeast, npnorth, npdepth, npintensity, npq)

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
		self.xarr = []
		self.yarr = []
		self.zarr = []
		self.iarr = []
		self.qarr = []
		# idarr = []
		# self.xarr = np.array(npx)
		# self.yarr = np.array(npy)
		# self.zarr = np.array(npz)
		# self.qarr = np.array(npq)
		# self.idarr = np.array(npid)

	###############################################################################
	def add(self, npx, npy, npz, npi, npq):
		'''add the new ping of data to the existing array '''
		# self.xarr = np.append(self.xarr, np.array(npx))
		# self.yarr = np.append(self.yarr, np.array(npy))
		# self.zarr = np.append(self.zarr, np.array(npz))
		# self.qarr = np.append(self.zarr, np.array(npq))
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

