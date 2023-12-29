pysbd
=====
* created:       December 2023
* by:            paul.kennedy@guardiangeomatics.com
* description:   python module to read an SDB file
* notes:         See main at end of script for example how to use this
* developed for Python version 3++

Done
====
* open file.
* check for sensible file size
* load header
* load list of sensors
* main loop to iterate thru records
* parse timestamp on each record



2Do
===
* figure out the ID on each record so we know which sensor it is from
* extract navigation
* implement loop to extract each record type and pass to a decoder
* convert EM records to point cloud

'''
    # opening the file reads the header and then the channelinfo automatically
    r = SDBReader(<filename>)
        # we can then loop through all packets, 
        while r.moreData():
            record = r.readDatagram()
    # close the File 
    r.close()
'''