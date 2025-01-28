# udi-teslaEV  -  for Polyglot v3x 
## Tesla EV Node server
The main node displays node status and the number of EVs associated with account
Each EV will have a Status node and 2 subnodes - Climate and Charging
Status gives an overview and allow some generic control
Climate controls Climate settings as well as Windows
Charging control Charging settings 


## Installation
Requires PG3x
OBS!!!!!! 
To issue commands one must install an electronic key on the car
On your mobile device open  https://tesla.com/_ak/my.isy.io. It should open the tesla app where you can approve the key-install - Older EVs may not support the virtual key.
Note, currently only supports commands for NA cars
 
Run the node server 
Update configuration parameters - most important is region NA (North America), EU (Europe and most of the rest of world), CN (China)
Note - currently only NA is supported for commands
Set TEMP_UNIT (C/F) and DIST_UNIT (Miles/Km) 
Set LOCATION_EN (True/False)

Location is needed to get access to longitude and latitude needed to control windows (close) as well as Homelink 
Note, if Location is enabled - an Icon will show on App.

Restart node server and press authenticate (should only be needed first time).
On authentication, you will need to grant the correct API permissions.  At a minimum the two following permissions need to be granted.
- Vehicle Information
- Vehicle Commands

If permissions need to be updated or changed, log into tesla.com and manage your third party apps.  These settings are in the Tesla website under Account Settings -> Security -> Third Party Apps -> Tesla Plugin for IoX.

### Limitations imposed by the API
```
Data (update/Poll) limit:   200 API requests / car / day
Commands limit:	            50 API requests / car / day
Wake-up limit:        	    15 API requests / car / day
Charging commands limit:    5 API requests / car / day
```
The ShortPoll and LongPoll settings are used to mitigate the rate limits set by Tesla.

ShortPoll = default 10 min (120 call/day)
    Polls data from car if it is awake - does nothing if car is asleep
    sends heartbeat to ISY

LongPoll = default 120min (7200sec) (12 call/day) - likely to wake the EV
    Polls data from car. If it is asleep it will wake the car and retrieve data.
    Note, one can increase this and manually wake the car from the CA to reduce power used when car is awake 

Some considerations on poll interval (given the API constraint) -
Polling too often will prevent the car from going to sleep (using more battery).
Polling too slow so car goes to sleep will require a wakeup that is limited to 15 times per day.
It may be better to let ISY control when to update data if one wants the least battery use. 

## Notes 
If additional fields for control or display is desired contact author @ https://github.com/Panda88CO/udi-TeslaEV

