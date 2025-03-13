# udi-teslaEV  -  for Polyglot v3x 
## Tesla EV Node server

Each EV will have a Status node and 2 subnodes - Climate and Charging
Status gives an overview and allow some generic control
Climate controls Climate settings as well as Windows
Charging control Charging settings 

The node subscribes to data from the EV.  Data will be updated automatically when data changes.  Therefore, there is no need poll data from the server - Data updates when data changes.

Sending commands uses the API.  Note API calls are charged, so try to minimize the use to wht makes sense.

FOR PERSONAL USE - not commercial 

## Installation
Requires PG3x
OBS!!!!!! 
To use the node server one must install an electronic key on the car
On your mobile device open  https://tesla.com/_ak/my.isy.io. It should open the tesla app where you can approve the key-install - Older EVs may not support the virtual key.
Note, currently only supports commands for NA cars
 
Additionally, one must open external access.
got to https://my.isy.io/index.htm and log in 
Select PG3->Remote Connections on the eISY/Polisy
Make sure that Remote Connection is ACTIVE
To validate if it works there is a TEST button on the main page on the node (result shown in the last field in the main page).

Run the node server 
Update configuration parameters - most important is region NA (North America), EU (Europe and most of the rest of world), CN (China)
Note - currently only NA is supported for commands
Set TEMP_UNIT (C/F) and DIST_UNIT (Miles/Km) 
Set LOCATION_EN (True/False)
set VIN if more than 1 EV is assoiated with the Tesla Account
If more than 1 EV on the account, the node can be installed multiple times with differnt VINs specified here

Location is needed to get access to longitude and latitude needed to control windows (close) as well as Homelink 
Note, if Location is enabled - an Icon will show on App.

Restart node server and press authenticate (should only be needed first time).
On authentication, you will need to grant the correct API permissions.  At a minimum the two following permissions need to be granted.
- Vehicle Information
- Vehicle Commands

If permissions need to be updated or changed, log into tesla.com and manage your third party apps.  These settings are in the Tesla website under Account Settings -> Security -> Third Party Apps -> Tesla Plugin for IoX.


The ShortPoll and LongPoll settings are used to mitigate the rate limits set by Tesla.

ShortPoll = default 1 min
    sends heartbeat to ISY

LongPoll = default 120min (7200sec) (12 call/day) - likely to wake the EV
    Polls the state of the car 
    Checks if tokens needs refresh

## Notes 
If additional fields for control or display is desired contact author @ https://github.com/Panda88CO/TeslaEV3
POssible data can be found at https://developer.tesla.com/docs/fleet-api/fleet-telemetry/available-data
