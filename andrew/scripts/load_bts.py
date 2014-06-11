import MySQLdb as mdb
import sys
import numpy as np
import glob

import load_credentials_nogit as creds

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Syntax: [list of files to be loaded into the DB (or 'all')] ['add or 'reset']")

    #Load in the files to be put in the DB
    filelist = []
    if sys.argv[1].lower() == 'all':
        filelist = glob.glob("*.csv")
    else:
        filelist = np.loadtxt(sys.argv[1],dtype=np.str,usecols=(0,),ndmin=1)
    filelist = np.array(filelist)

    #Check that there is at least one file:
    if len(filelist) == 0:
        raise IOError("No files in list!")

    #Check that the user wants to either append or overwrite the database:
    op_type = sys.argv[2].lower()
    if op_type != 'add' and op_type != 'reset':
        raise IOError("Operation type must be either 'add' or 'reset'")

    #Connect to the db:
    con = ''
    try:
        con = mdb.connect(host=creds.host,user=creds.user,db=creds.database,passwd=creds.password)
        cur = con.cursor()
        #If the user wants to restart, drop the db:
        if op_type == 'reset':
            cur.execute('drop table if exists flightdelays')
            cur.execute("""create table flightdelays(fid int not null auto_increment primary key,
            year smallint,
            month tinyint,
            dayofmonth tinyint,
            dayofweek tinyint,
            flightdate date,
            uniquecarrier varchar(2),
            airlineid mediumint,
            tailnum varchar(6),
            flightnum varchar(10),
            originairportid mediumint,
            origincitymarketid mediumint,
            origin varchar(3),
            originstate varchar(2),
            destairportid mediumint,
            destcitymarketid mediumint,
            dest varchar(3),
            deststate varchar(2),
            crsdeptime varchar(4),
            deptime varchar(4) not null default "9999",
            depdelay float not null default -9999.,
            taxiout float not null default -9999.,
            wheelsoff varchar(4),
            wheelson varchar(4),
            taxiin float not null default -9999,
            crsarrtime varchar(4),
            arrtime varchar(4) not null default "9999",
            arrdelay float not null default -9999.,
            cancelled float,
            cancellationcode varchar(1),
            diverted float,
            distance float,
            carrierdelay float not null default 0.,
            weatherdelay float not null default 0.,
            nasdelay float not null default 0.,
            securitydelay float not null default 0.,
            lateaircraftdelay float not null default 0.
            )""")#If a plane arrives less than 15 minutes late, it's not considered to be 'delayed' and therefore the different delay types are left blank - nobody needs to be blamed for the delay because it's so short. 

        for i,filename in enumerate(filelist):
            print filename
            cur.execute('''load data local infile "{0:s}" into table flightdelays fields terminated by "," optionally enclosed by """" ignore 1 lines(
            year,@quarter,month,dayofmonth,dayofweek,@datevar,uniquecarrier,airlineid,@dummy,tailnum,flightnum,originairportid,@dummy,origincitymarketid,origin,@origincityname,originstate,@dummy,@originstatename,@dummy,destairportid,@dummy,destcitymarketid,dest,@destcityname,deststate,@dummy,@deststatename,@dummy,crsdeptime,@deptime,@depdelay,@depdelayminutes,@depdel15,@departuredelaygroups,@deptimeblk,@taxiout,wheelsoff,wheelson,@taxiin,crsarrtime,@arrtime,@arrdelay,@arrdelayminutes,@arrdelay15,@arrivaldelaygroups,@arrtimeblk,cancelled,cancellationcode,diverted,@crselapsedtime,@actualelapsedtime,@airtime,@flights,distance,@distancegroup,@carrierdelay,@weatherdelay,@nasdelay,@securitydelay,@lateaircraftdelay,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy)
            set flightdate=STR_TO_DATE(@datevar, '%Y-%m-%d'),
            deptime = ifnull(nullif(@deptime,''),"9999"),
            arrtime = ifnull(nullif(@arrtime,''),"9999"),
            depdelay = ifnull(nullif(@depdelay,''),-9999.),
            arrdelay = ifnull(nullif(@arrdelay,''),-9999.),
            taxiout = ifnull(nullif(@taxiout,''),-9999.),
            taxiin = ifnull(nullif(@taxiin,''),-9999.),
            carrierdelay = ifnull(nullif(@carrierdelay,''),0.),
            weatherdelay = ifnull(nullif(@weatherdelay,''),0.),
            nasdelay = ifnull(nullif(@nasdelay,''),0.),
            securitydelay = ifnull(nullif(@securitydelay,''),0.),
            lateaircraftdelay = ifnull(nullif(@lateaircraftdelay,''),0.)
            '''.format(filename))
            # cur.execute('''load data local infile "{0:s}" into table flightdelays fields terminated by "," optionally enclosed by """" ignore 1 lines(
            # year,quarter,month,dayofmonth,dayofweek,@datevar,uniquecarrier,airlineid,@dummy,tailnum,flightnum,originairportid,@dummy,origincitymarketid,origin,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy,@dummy)
            # set flightdate=STR_TO_DATE(@datevar, '%Y-%m-%d')'''.format(filename))
            con.commit()

    except mdb.Error, e:
        print "Error %d: %s" % (e.args[0],e.args[1])
        sys.exit(1)
    finally:
        if con:
            con.close()
        