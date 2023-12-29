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
* header for sensors seem to parse ok.
* parse port config for each sensor
* parse offsets for each sensor
* parse sensor name, category, type
* parse data start byte so we can jump to first datagram
* parsing of datagrams in place.  we can now parse nmea datagrams ok
* extract navigation from nmea records
* implement loop to extract each record type and pass to a decoder


2Do
===
* extract navigation from position datagrams (category 17)
* extract heading from gyro datagrams (category 36)
* figure out the ID on each record so we know which sensor it is from

```
    # opening the file reads the header
    r = SBDReader(<filename>)
        # we can then loop through all packets, 
        while r.moreData():
            record = r.readDatagram()
    # close the File 
    r.close()
```
