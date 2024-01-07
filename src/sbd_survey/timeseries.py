import os
import numpy as np
import math

###############################################################################
def main():
	'''an example how to use the time series class.
	'''
	attitude = [[0.001,100],[2,200], [5,500], [10,1000]]
	tsRoll = cTimeSeries(attitude)
	print(tsRoll.getValueAt(6))

	# now make an interpolated time series.  this is useful if we need to export at a given interval.
	interval=1
	interpolatedroll = tsRoll.createinterpolatedseries(interval)
	print(interpolatedroll)

###############################################################################
class cTimeSeries:
	'''# how to use the time series class, a 2D list of time
	# attitude = [[1,100],[2,200], [5,500], [10,1000]]
	# tsRoll = cTimeSeries(attitude)
	# print(tsRoll.getValueAt(6))'''


###############################################################################
	def __init__(self, timeOrTimeValue, values=""):
		'''the time series requires a 2d series of [[timestamp, value],[timestamp, value]].  It then converts this into a numpy array ready for fast interpolation'''
		self.name = "2D time series"
		# user has passed 1 list with both time and values, so handle it
		if len(values) == 0:
				arr = np.array(timeOrTimeValue)
				#sort the list into ascending time order
				arr = arr[np.argsort(arr[:,0])]
				self.times = arr[:,0]
				self.values = arr[:,1]
		else:
			# user has passed 2 list with time and values, so handle it
			self.times = np.array(timeOrTimeValue)
			self.values = np.array(values)

	###############################################################################
	def getValueAt(self, timestamp):
		return np.interp(timestamp, self.times, self.values, left=None, right=None)

	###############################################################################
	def createinterpolatedseries(self, interval=1):
		'''now make a new time series interpolated at the user required interval
		'''
		starttime = self.times[0]
		endtime = self.times[-1]

		# create an index of times for the required range.  
		ts = np.arange(starttime, endtime, interval)
		# we need to extend the end record as numpy arange does not include the last record
		ts = np.append(ts, endtime)
		# now interpolate quickly using numpy
		interpolatedValues = np.interp(ts, self.times, self.values, left=None, right=None)
		# put the answers into a new class, so we can use them
		interpolate_ts = cTimeSeries(ts, interpolatedValues)
		return interpolate_ts

	###############################################################################
	def getNearestAt(self, timestamp):
		idx = np.searchsorted(self.times, timestamp, side="left")
		if idx > 0 and (idx == len(self.times) or math.fabs(timestamp - self.times[idx-1]) < math.fabs(timestamp - self.times[idx])):
			return self.times[idx-1], self.values[idx-1]
		else:
			return self.times[idx], self.values[idx]

###################################################################################################
###################################################################################################
if __name__ == "__main__":
		main()
###################################################################################################
###################################################################################################
