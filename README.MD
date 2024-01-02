pysbd_survey
=====
* created:       December 2023
* by:            paul.kennedy@guardiangeomatics.com
* description:   python module to read an SDB file
* developed for Python version 3++

Notes
====
The EIVA SBD file format is created by naviscan for acquisition of raw sensor data such as postion, motion, heading, sidescan and multibeam.  The file format is binary in nature.  unfortunately the file format specification is not published by EIVA (we asked) but we needed to access our data for automated QC immediately following acquisition and prior to processing in naviedit/navimodel.  
We have made a pure python decode for the sbd file format.  It is not 100% correct as there are a few parts which we do not yet understand, but for the most part it works

The file format comprises the following sections:

File Header
====
A header of the first timestamp
A slot for the WGS84 specification.  the samples tested are all wmpty, so no WKT / EPSG available
A slot for the UTM specification.  the samples tested are all wmpty, so no WKT / EPSG available
A table of sensors with name, interfacing details and installation offsets and disabled/enabled status

Datagrams
====
A series of datagrams comprising a header, decoded data and the raw bytes from the sensor

File Footer
====
there seems to be no file footer

Done
====
* open file.
* check for sensible file size
* load header
* load list of sensors
* main loop to iterate thru records
* parse timestamp on each record
* header for sensors seem to parse ok.
* parse port config for each sensor
* parse offsets for each sensor
* parse sensor name, category, type
* parse data start byte so we can jump to first datagram
* parsing of datagrams in place.  we can now parse nmea datagrams ok
* extract navigation from nmea records
* implement loop to extract each record type and pass to a decoder
* extract navigation from position datagrams 
* extract heading from gyro datagrams 
* extract depth from depth datagrams 
* extract motion from motion datagrams 
* convert variables into dictionary throughout so its clean
* implement R2sonic BTH0 decode
* implement conversion from angle/tt to Dx,Dz
* implement a stateful sensor dictionary
* loadnavigation function is now working so we can now merge into survey2ssdm
* parse the echosounder processed datagram.  I dont see a format descriptor in the datagram header which looks encouraging
* figure out the format of the raw datagram for echosounder datagrams
* figure out the ID on each record so we know which sensor it is from (its the category)
* test with a bunch of sbd files.
* add arg parser so we can test all files in folder for thorough testing

2Do
===
* make pysbd a pip installable package
* produce a laz file from the sbd file MBES data.
* convert raw bathy range/traveltime to Dx,Dz
* apply current roll to the take off angles in RT-->Dxz calculation
* implement a refraction computation to permit high quality conversions in python
* convert Dxz to east/north/depth point cloud
* convert point cloud to laz file
* implement -s to make a summary of the file contents to a json string
* to make a sensible loadnavigation function we need WGS84 coordinates.  unfortunately the sbd position datagrams only have decoded positions in easting, northing, so we need the user to specify epsg code so we can convert back to lat/lon
* some of the fields in the msgheader are still unknown.  I am sure they are there for a reason!
* figure out why some category is 265 instead of 9. it looks like the secondary system has 256 added to the category but this seems a bit of a hack from the eiva developers!

```
    # opening the file reads the header
    r = SBDReader(<filename>)
        # we can then loop through all packets, 
        while r.moreData():
    		category, decoded = reader.readdatagram()
    		if category == reader.GYRO:
    			sensorid, msgtimestamp, sensor, rawdata = decoded
	    		print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))
    # close the File 
    r.close()
```

Package creation notes
===
# we use twine to create and upload
pip install twine

# to create package
python -m build

# to upload package
python -m twine upload --repository testpypi dist/* --verbose