#name:			r2sonicdecode.py
#created:		December 2024
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to decode a BTH0 datagram from r2sonic MBES systems.  this datagram is the most common datagram used by the r2sonic systems and is assumed to be recorded by EIVA NaviPac and NaviScan software.

import struct
import pprint

####################################################################################################################
###############################################################################
class BTH0:
	'''decode as per following documentation'''
	'''file:///C:/ggtools/pysbd/Sonic%202022-2024-2026%20Operation%20Manual%20v6.3r003.pdf'''

	def __init__(self, rawdata=None):
		self.header = None
		self.H0	= None
		self.R0 = None
		self.A0 = None
		self.A2 = None
		self.I1 = None
		self.G0 = None
		self.G1 = None
		self.Q0 = None
		self.pointcount = 0
		self.ranges = []
		self.angles = []
		self.intensities = []

		#header is 60 bytes...
		packet_fmt = '>4s 2L'
		HDRpacket_len = struct.calcsize(packet_fmt)
		packet_unpack = struct.Struct(packet_fmt).unpack_from

		s = packet_unpack(rawdata)

		# // *** BEGIN PACKET: BATHY DATA FORMAT 0 ***
		#  u32 PacketName; // 'BTH0'
		#  u32 PacketSize; // [bytes] size of this entire packet
		#  u32 DataStreamID; // reserved for future use
		self.header = {
			'packetname': s[0],
			'packetsize': s[1],
			'datastreamid': s[2]
		}

		# trim the leading bytes from the rawdata packet
		# move the pointer to the end of the header
		rawdata = rawdata[HDRpacket_len:]
		# Define the format string for struct.unpack based on the packet structure
		format_str = '>2s H 12s 12s 3L 9f Hh 7f L 2H'
		H0packet_len = struct.calcsize(format_str)
		# pad H0 packet to 4-byte boundary if required
		if (H0packet_len % 4) != 0:
			format_str = '>2s H 12s 12s 3L 9f Hh 7f H 2h 2s'
			H0packet_len = struct.calcsize(format_str)

		unpacked_data = struct.unpack(format_str, rawdata[:H0packet_len])

		# Extract the fields
		self.H0 = {
			'H0_SectionName': unpacked_data[0].decode('utf-8'),
			'H0_SectionSize': unpacked_data[1],
			'H0_ModelNumber': unpacked_data[2].decode('utf-8').rstrip('\x00'),
			'H0_SerialNumber': unpacked_data[3].decode('utf-8').rstrip('\x00'),
			'H0_TimeSeconds': unpacked_data[4],
			'H0_TimeNanoseconds': unpacked_data[5],
			'H0_PingNumber': unpacked_data[6],
			'H0_PingPeriod': unpacked_data[7],
			'H0_SoundSpeed': unpacked_data[8],
			'H0_Frequency': unpacked_data[9],
			'H0_TxPower': unpacked_data[10],
			'H0_TxPulseWidth': unpacked_data[11],
			'H0_TxBeamwidthVert': unpacked_data[12],
			'H0_TxBeamwidthHoriz': unpacked_data[13],
			'H0_TxSteeringVert': unpacked_data[14],
			'H0_TxSteeringHoriz': unpacked_data[15],
			'H0_2026ProjTemp': unpacked_data[16],
			'H0_VTX+Offset': (unpacked_data[17] / 100.0) - 273.15, # kelvin to degC
			'H0_RxBandwidth': unpacked_data[18],
			'H0_RxSampleRate': unpacked_data[19],
			'H0_RxRange': unpacked_data[20],
			'H0_RxGain': unpacked_data[21] * 2,
			'H0_RxSpreading': unpacked_data[22],
			'H0_RxAbsorption': unpacked_data[23],
			'H0_RxMountTilt': unpacked_data[24],
			'H0_RxMiscInfo': unpacked_data[25],
			'H0_reserved': unpacked_data[26],
			'H0_Points': unpacked_data[27]
		}

		# we need this lots so keep it handy
		pointcount = self.H0['H0_Points']
		self.pointcount = pointcount

		#   // section R0: 16-bit bathy point ranges
		rawdata = rawdata[H0packet_len:]
		format_str = '>2s H f ' + str(pointcount) + 'H' # + str(pointcount) + 'H'
		R0packet_len = struct.calcsize(format_str)
		if (R0packet_len % 4) != 0:
			format_str = '>2s H f ' + str(pointcount) + 'H ' + '2s'
			R0packet_len = struct.calcsize(format_str)
		unpacked_data = struct.unpack(format_str, rawdata[:R0packet_len])

		# Extract the fields
		self.R0 = {
			'R0_SectionName': unpacked_data[0].decode('utf-8'), # 'R0'
			'R0_SectionSize': unpacked_data[1], # [bytes] size of this entire section
			'R0_Scalefactor': unpacked_data[2],
			# unpack the ranges into a list of length H0_Points
			'R0_Range': [unpacked_data[x] for x in range(3,3+pointcount)], # [seconds two-way] = R0_Range * R0_ScalingFactor
			# 'R0_unused': [unpacked_data[x] for x in range(3,3+pointcount)],
		}
		# scale the R0_Range values
		for idx, r in enumerate(self.R0['R0_Range']):
			self.R0['R0_Range'][idx] = r * self.R0['R0_Scalefactor']	
		#make this more accessible
		self.ranges = self.R0['R0_Range']

		#   // section A0: bathy point angles, equally-spaced (present only during "equi-angle" spacing mode)
		#   u16 A0_SectionName; // 'A0'
		#   u16 A0_SectionSize; // [bytes] size of this entire section
		#   f32 A0_AngleFirst; // [radians] angle of first (port side) bathy point, relative to array centerline, AngleFirst < AngleLast
		#   f32 A0_AngleLast; // [radians] angle of last (starboard side) bathy point
		#   f32 A0_MoreInfo_0; // 0 (reserved for future use)
		#   f32 A0_MoreInfo_1 //Z-offset, proj [metres]
		#   f32 A0_MoreInfo_2; //Y-offset, proj [metres]
		#   f32 A0_MoreInfo_3; //X-offset, proj [metres]
		#   f32 A0_MoreInfo_4; //0 (reserved for future use)
		#   f32 A0_MoreInfo_5; //0 (reserved for future use)

		#trim the leading bytes already read
		rawdata = rawdata[R0packet_len:]

		# section A0 is optional, so check if it is present
		if rawdata[0:2] == b'A0':
			format_str = '>2s H 8f'
			A0packet_len = struct.calcsize(format_str)
			if (A0packet_len % 4) != 0:
				format_str = '>2s H 8f 2s'
				A0packet_len = struct.calcsize(format_str)
			unpacked_data = struct.unpack(format_str, rawdata[:A0packet_len])
			self.A0 = {
				'A0_SectionName': unpacked_data[0].decode('utf-8'), # 'A0'
				'A0_SectionSize': unpacked_data[1], # [bytes] size of this entire section
				'A0_AngleFirst': unpacked_data[2], # [radians] angle of first (port side) bathy point, relative to array centerline, AngleFirst < AngleLast
				'A0_AngleLast': unpacked_data[3], # [radians] angle of last (starboard side) bathy point
				'A0_MoreInfo_0': unpacked_data[4], # 0 (reserved for future use)
				'A0_MoreInfo_1': unpacked_data[5], # Z-offset, proj [metres]
				'A0_MoreInfo_2': unpacked_data[6], # Y-offset, proj [metres]
				'A0_MoreInfo_3': unpacked_data[7], # X-offset, proj [metres]
				'A0_MoreInfo_4': unpacked_data[8], # 0 (reserved for future use)
				'A0_MoreInfo_5': unpacked_data[9], # 0 (reserved for future use)
			}
			# for each point, calculate the angle
			# angle[n] = A0_AngleFirst + (n * (A0_AngleLast - A0_AngleFirst) / (H0_Points - 1))
			for idx in range(0, pointcount):
				self.A0['A0_AngleStep'].append(self.A0['A0_AngleFirst'] + (idx * (self.A0['A0_AngleLast'] - self.A0['A0_AngleFirst']) / (pointcount - 1)))
			#make this more accessible
			self.angles = self.A0['A0_AngleStep']

			#trim the leading bytes already read
			rawdata = rawdata[A0packet_len:]

		# section A2 is optional, so check if it is present
		elif rawdata[0:2] == b'A2':
			format_str = '>2s H 8f ' + str(pointcount) + 'H'
			A2packet_len = struct.calcsize(format_str)
			if (A2packet_len % 4) != 0:
				format_str = '>2s H 8f ' + str(pointcount) + 'H' + '2s'
				A2packet_len = struct.calcsize(format_str)
			unpacked_data = struct.unpack(format_str, rawdata[:A2packet_len])
			self.A2 = {
				'A2_SectionName': unpacked_data[0].decode('utf-8'), # 'A2'
				'A2_SectionSize': unpacked_data[1], # [bytes] size of this entire section
				'A2_AngleFirst': unpacked_data[2], # // [radians] angle of first (port side) bathy point, relative to array centerline, AngleFirst < AngleLast
				'A2_ScalingFactor': unpacked_data[3], 
				'A0_MoreInfo_0': unpacked_data[4], # 0 (reserved for future use)
				'A0_MoreInfo_1': unpacked_data[5], # Z-offset, proj [metres]
				'A0_MoreInfo_2': unpacked_data[6], # Y-offset, proj [metres]
				'A0_MoreInfo_3': unpacked_data[7], # X-offset, proj [metres]
				'A0_MoreInfo_4': unpacked_data[8], # 0 (reserved for future use)
				'A0_MoreInfo_5': unpacked_data[9], # 0 (reserved for future use)
				'A2_AngleStep': [unpacked_data[x] for x in range(10,10+pointcount)],
			}

			# angle[n] = A2_AngleFirst + (32-bit sum of A2_AngleStep[0] through A2_AngleStep[n]) * A2_ScalingFactor
			for idx, a in enumerate(self.A2['A2_AngleStep']):				
				self.A2['A2_AngleStep'][idx] = self.A2['A2_AngleFirst'] + (sum(self.A2['A2_AngleStep'][0:idx]) * self.A2['A2_ScalingFactor'])

			#make this more accessible
			self.angles = self.A2['A2_AngleStep']

			#trim the leading bytes already read
			rawdata = rawdata[A2packet_len:]

			# section I1 is optional, so check if it is present
			if rawdata[0:2] == b'I1':
				format_str = '>2s H f ' + str(pointcount) + 'H'
				I1packet_len = struct.calcsize(format_str)
				if (I1packet_len % 4) != 0:
					format_str = '>2s H f ' + str(pointcount) + 'H' + '2s'
					I1packet_len = struct.calcsize(format_str)
				unpacked_data = struct.unpack(format_str, rawdata[:I1packet_len])
				self.I1 = {
					'I1_SectionName': unpacked_data[0].decode('utf-8'), # 'I1'
					'I1_SectionSize': unpacked_data[1], # [bytes] size of this entire section
					'I1_ScalingFactor': unpacked_data[2],
					'I1_Intensity': [unpacked_data[x] for x in range(3,3+pointcount)], # [micropascals] intensity[n] = I1_Intensity[n]) * I1_ScalingFactor
				}
				#trim the leading bytes already read
				rawdata = rawdata[I1packet_len:]

			# section G0 is optional, so check if it is present
			if rawdata[0:2] == b'G0':
				format_str = '>2s H 3f'
				G0packet_len = struct.calcsize(format_str)
				if (G0packet_len % 4) != 0:
					format_str = '>2s H 3f 2s'
					G0packet_len = struct.calcsize(format_str)
				unpacked_data = struct.unpack(format_str, rawdata[:G0packet_len])
				self.G0 = {
					'G0_SectionName': unpacked_data[0].decode('utf-8'), # 'G0'
					'G0_SectionSize': unpacked_data[1], # [bytes] size of this entire section
					'G0_DepthGateMin': unpacked_data[2], # [seconds two-way]
					'G0_DepthGateMax': unpacked_data[3], # [seconds two-way]
					'G0_DepthGateSlope': unpacked_data[4], # [radians]
				}
				#trim the leading bytes already read
				rawdata = rawdata[G0packet_len:]

			# section G1 is optional, so check if it is present
			if rawdata[0:2] == b'G1':
				format_str = '>2s H f ' + str(pointcount) + 'H'
				G1packet_len = struct.calcsize(format_str)
				if (G1packet_len % 4) != 0:
					format_str = '>2s H f ' + str(pointcount) + 'H' + '2s'
					G1packet_len = struct.calcsize(format_str)
				unpacked_data = struct.unpack(format_str, rawdata[:G1packet_len])
				self.G1 = {
					'G1_SectionName': unpacked_data[0].decode('utf-8'), # 'G1'
					'G1_SectionSize': unpacked_data[1], # [bytes] size of this entire section
					'G1_ScalingFactor': unpacked_data[2],
					'G1_Gate': [unpacked_data[x] for x in range(3,3+pointcount)], # [seconds two-way] = RangeMin * G1_ScalingFactor
				}
				#trim the leading bytes already read
				rawdata = rawdata[G1packet_len:]

			# section Q0 is optional, so check if it is present
			if rawdata[0:2] == b'Q0':
				format_str = '>2s H ' + str(int((pointcount/2))) + 's'
				Q0packet_len = struct.calcsize(format_str)
				unpacked_data = struct.unpack(format_str, rawdata[:Q0packet_len])
				self.Q0 = {
					'Q0_SectionName': unpacked_data[0].decode('utf-8'), # 'Q0'
					'Q0_SectionSize': unpacked_data[1], # [bytes] size of this entire section
					# loop through the array and split the byte into the left and right nibbles
					'Q0_Quality': [unpacked_data[2][x:x+1] for x in range(0, len(unpacked_data[2]), 1)], # 8 groups of 4 flags bits (phase detect, magnitude detect, reserved, reserved), packed left-to-right
				}
				#trim the leading bytes already read
				rawdata = rawdata[Q0packet_len:]

		return

	####################################################################################################################
	def isphasebitset(self, byte):
		'''check if the phase bit is set'''
		return (byte & (1 << 0)) != 0

	####################################################################################################################
	def ismagnitudebitset(self, byte):
		'''check if the magnitude bit is set'''
		return (byte & (1 << 1)) != 0


	####################################################################################################################
	#print the contents of the class
	def __str__(self):
		return (pprint.pformat(vars(self)))	

####################################################################################################################
###############################################################################
	
		#  // section H0: header
		# #  u16 H0_SectionName; // 'H0'
		# 2s
		# #  u16 H0_SectionSize; // [bytes] size of this entire section
		# H
		# #  u8 H0_ModelNumber[12]; // example "2024", unused chars are nulls
		# 12s
		# #  u8 H0_SerialNumber[12]; // example "100017", unused chars are nulls
		# 12s
		# #  u32 H0_TimeSeconds; // [seconds] ping time relative to 0000 hours 1-Jan-1970, integer part
		# #  u32 H0_TimeNanoseconds; // [nanoseconds] ping time relative to 0000 hours 1-Jan-1970, fraction part
		# #  u32 H0_PingNumber; // pings since power-up or reboot
		# 3L
		# #  f32 H0_PingPeriod; // [seconds] time between most recent two pings
		# #  f32 H0_SoundSpeed; // [meters per second]
		# #  f32 H0_Frequency; // [hertz] sonar center frequency
		# #  f32 H0_TxPower; // [dB re 1 uPa at 1 meter]
		# #  f32 H0_TxPulseWidth; // [seconds]
		# #  f32 H0_TxBeamwidthVert; // [radians]
		# #  f32 H0_TxBeamwidthHoriz; // [radians]
		# #  f32 H0_TxSteeringVert; // [radians]
		# #  f32 H0_TxSteeringHoriz; // [radians]
		# 9f
		# #  u16 H0_2026ProjTemp; // [hundredths of a degree Kelvin] 2026 projector temperature (divide value by 100, subtract 273.15 to get °C)
		# H
		# #  s16 H0_VTX+Offset; // [hundredths of a dB] transmit voltage offset at time of ping (divide value by 100 to get dB)
		# h
		# #  f32 H0_RxBandwidth; // [hertz]
		# #  f32 H0_RxSampleRate; // [hertz] sample rate of data acquisition and signal processing
		# #  f32 H0_RxRange; // [meters] sonar range setting
		# #  f32 H0_RxGain; // [multiply by two for relative dB]
		# #  f32 H0_RxSpreading; // [dB (times log range in meters)]
		# #  f32 H0_RxAbsorption; // [dB per kilometer]
		# #  f32 H0_RxMountTilt; // [radians]
		# 7f
		# #  u32 H0_RxMiscInfo; // reserved for future use
		# H
		# #  u16 H0_reserved; // reserved for future use
		# #  u16 H0_Points; // number of bathy point
		# 2h
	
		# #   // section R0: 16-bit bathy point ranges
		# #   u16 R0_SectionName; // 'R0'
		# #   u16 R0_SectionSize; // [bytes] size of this entire section
		# 	2H
		# #   f32 R0_ScalingFactor;
		# 	f
		# #   u16 R0_Range[H0_Points]; // [seconds two-way] = R0_Range * R0_ScalingFactor
		# #   u16 R0_unused[H0_Points & 1]; // ensure 32-bit section size
		# 	2H
	
	
#   // section A2: 16-bit bathy point angles, arbitrarily-spaced (present only during "equi-distant" spacing mode)
#   u16 A2_SectionName; // 'A2'
#   u16 A2_SectionSize; // [bytes] size of this entire section
#   f32 A2_AngleFirst; // [radians] angle of first (port side) bathy point, relative to array centerline, AngleFirst < AngleLast
#   f32 A2_ScalingFactor;
#   f32 A0_MoreInfo_0; // 0 (reserved for future use)
#   f32 A0_MoreInfo_1 //Z-offset, proj [metres]
#   f32 A0_MoreInfo_2; //Y-offset, proj [metres]
#   f32 A0_MoreInfo_3; //X-offset, proj [metres]
#   f32 A0_MoreInfo_4; //0 (reserved for future use)
#   f32 A0_MoreInfo_5; //0 (reserved for future use) u16 A2_AngleStep[H0_Points]; // [radians] angle[n] = A2_AngleFirst + (32-bit sum of A2_AngleStep[0] through A2_AngleStep[n]) * A2_ScalingFactor
#   u16 A2_unused[H0_Points & 1]; // ensure 32-bit section size
	
#   // section I1: 16-bit bathy intensity (present only if enabled)
#   u16 I1_SectionName; // 'I1'
#   u16 I1_SectionSize; // [bytes] size of this entire section
#   f32 I1_ScalingFactor;
#   u16 I1_Intensity[H0_Points]; // [micropascals] intensity[n] = I1_Intensity[n]) * I1_ScalingFactor
#   u16 I1_unused[H0_Points & 1]; // ensure 32-bit section size

#   // section G0: simple straight-line depth gates
#  u16 G0_SectionName; // 'G0'
#  u16 G0_SectionSize; // [bytes] size of this entire section
#  f32 G0_DepthGateMin; // [seconds two-way]
#  f32 G0_DepthGateMax; // [seconds two-way]
#  f32 G0_DepthGateSlope; // [radians]
#  // section G1: 8-bit gate positions, arbitrary paths (present only during "verbose" gate description mode)
#  u16 G1_SectionName; // 'G1'
#  u16 G1_SectionSize; // [bytes] size of this entire section
#  f32 G1_ScalingFactor;
#  struct
#  {
#  u8 RangeMin; // [seconds two-way] = RangeMin * G1_ScalingFactor
#  u8 RangeMax; // [seconds two-way] = RangeMax * G1_ScalingFactor
#  } G1_Gate[H0_Points];
#  u16 G1_unused[H0_Points & 1]; // ensure 32-bit section size
#  // section Q0: 4-bit quality flags
#  u16 Q0_SectionName; // 'Q0' quality, 4-bit
#  u16 Q0_SectionSize; // [bytes] size of this entire section
#  u32 Q0_Quality[(H0_Points+7)/8]; // 8 groups of 4 flags bits (phase detect, magnitude detect, reserved, reserved), packed left-to-right
# // *** END PACKET: BATHY FORMAT 0 ***

