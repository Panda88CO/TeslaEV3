#!/usr/bin/env python3

import sys
import time 

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=20)

from TeslaEVOauth import teslaEVAccess
from TeslaEVStatusNode import teslaEV_StatusNode
#from TeslaCloudEVapi  import teslaCloudEVapi
from TeslaEVOauth import teslaAccess


VERSION = '0.0.1'

class TeslaEVController(udi_interface.Node):
    #from  udiLib import node_queue, wait_for_node_done,tempUnitAdjust,  setDriverTemp, cond2ISY,  mask2key, heartbeat, state2ISY, bool2ISY, online2ISY, EV_setDriver, openClose2ISY

    def __init__(self, polyglot, primary, address, name, ev_cloud_access):
        super(TeslaEVController, self).__init__(polyglot, primary, address, name)
        logging.setLevel(10)
        self.poly = polyglot
        self.portalID = None
        self.portalSecret = None
        self.n_queue = []
        self.vehicleList = []
        self.vin_list = [] # needed for streaming server
        #self.stream_cert = {}
        self.TEVcloud = ev_cloud_access
        
        logging.info('_init_ Tesla EV Controller ')
        self.ISYforced = False
        self.name = 'Tesla EV Info'
        self.primary = primary
        self.address = address
        #self.tokenPassword = ""
        self.n_queue = []
        self.CELCIUS = 0
        self.FARENHEIT = 1 
        self.KM = 0
        self.MILES = 1
        #self.dUnit = self.MILES #  Miles = 1, Kilometer = 0
        #self.tUnit = self.FARENHEIT  #  C = 0, F=1,
        self.supportedParams = ['DIST_UNIT', 'TEMP_UNIT']
        self.paramsProcessed = False
        self.customParameters = Custom(self.poly, 'customparams')
        self.portalData = Custom(self.poly, 'customNSdata')
        self.Notices = Custom(polyglot, 'notices')

        #self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)

        self.poly.subscribe(self.poly.WEBHOOK, self.webhook)
        self.hb = 0
        self.connected = False
        self.nodeDefineDone = False
        self.statusNodeReady = False
        self.customNsDone = False
        self.portalReady = False
        self.poly.updateProfile()
        self.poly.ready()
        #self.poly.addNode(self, conn_status = None, rename = False)
        #self.poly.addNode(self)
        #self.wait_for_node_done()
        #self.status_nodes = {}
        #self.node = self.poly.getNode(self.address)
        self.tempUnit = 0 # C
        self.distUnit = 0 # KM
        self.customParam_done = False
        self.config_done = False
        #self.poly.setLogLevel('debug')

        self.EVid = None
        self.status_node = None
        #self.EV_setDriver('ST', 1, 25)

        logging.info('Controller init DONE')

    def check_config(self):
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.config_done= True


    def configDoneHandler(self):
        logging.debug('configDoneHandler - config_done')
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.config_done= True
        try:
            self.TEVcloud.getAccessToken()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
        return

    def oauthHandler(self, token):
        # When user just authorized, pass this to your service, which will pass it to the OAuth handler
        self.TEVcloud.oauthHandler(token)
        # Then proceed with device discovery
        self.configDoneHandler()

    def handleLevelChange(self, level):
        logging.info('New log level: {level}')

    def handleNotices(self, level):
        logging.info('handleNotices:')


    def customNSHandler(self, key, data):        
        self.portalData.load(data)
        #stream_cert = {}
        logging.debug(f'customNSHandler : key:{key}  data:{data}')
        if key == 'nsdata':
            if 'portalID' in data:
                self.portalID = data['portalID']
                #self.customNsDone = True
            if 'PortalSecret' in data:
                self.portalSecret = data['PortalSecret']
                #self.customNsDone = True
            if self.TEVcloud.initializePortal(self.portalID, self.portalSecret):
                self.portalReady = True

            #if 'issuedAt' in data:
            #    stream_cert = {}
            #    stream_cert['issuedAt'] = data['issuedAt']
            #    stream_cert['expiry'] = data['expiry']
            #    stream_cert['expectedRenewal'] = data['expectedRenewal']
            #    stream_cert['ca'] = data['ca']
            #    self.TEVcloud.stream_cert  = stream_cert
            logging.debug(f'Custom Data portal: {self.portalID} {self.portalSecret}')

        self.TEVcloud.customNsHandler(key, data)
        
    #def customDataHandler(self, Data):
    #    logging.debug('customDataHandler')
    #    self.customData.load(Data)
    #    #logging.debug('handleData load - {}'.format(self.customData))
         

    def customParamsHandler(self, userParams):
        self.customParameters.load(userParams)
        logging.debug(f'customParamsHandler called {userParams}')

        oauthSettingsUpdate = {}
        #oauthSettingsUpdate['parameters'] = {}
        oauthSettingsUpdate['token_parameters'] = {}
        # Example for a boolean field

        if 'REGION' in userParams:
            if self.customParameters['REGION'] != 'Input region NA, EU, CN':
                region = str(self.customParameters['REGION'])
                if region.upper() not in ['NA', 'EU', 'CN']:
                    logging.error(f'Unsupported region {region}')
                    self.poly.Notices['REGION'] = 'Unknown Region specified (NA = North America + Asia (-China), EU = Europe. middle East, Africa, CN = China)'
                else:
                    self.TEVcloud.cloud_set_region(region)
        else:
            logging.warning('No region found')
            self.customParameters['REGION'] = 'Input region NA, EU, CN'
            region = None
            self.poly.Notices['region'] = 'Region not specified (NA = Nort America + Asia (-China), EU = Europe. middle East, Africa, CN = China)'
   
        if 'DIST_UNIT' in userParams:
            if self.customParameters['DIST_UNIT'] != 'Km or Miless':
                dist_unit = str(self.customParameters['DIST_UNIT'])

                if dist_unit[0].upper() not in ['K', 'M']:
                    logging.error(f'Unsupported distance unit {dist_unit}')
                    self.poly.Notices['dist'] = 'Unknown distance Unit specified'
                else:
                    if dist_unit[0].upper() == 'K':
                        
                        self.TEVcloud.teslaEV_SetDistUnit(0)
                    else:
                        self.TEVcloud.teslaEV_SetDistUnit(1)
                        
        else:
            logging.warning('No DIST_UNIT')
            self.customParameters['DIST_UNIT'] = 'Km or Miles'

        if 'TEMP_UNIT' in userParams:
            if self.customParameters['TEMP_UNIT'] != 'C or F':
                temp_unit = str(self.customParameters['TEMP_UNIT'])
                if temp_unit[0].upper() not in ['C', 'F']:
                    logging.error(f'Unsupported temperatue unit {temp_unit}')
                    self.poly.Notices['temp'] = 'Unknown distance Unit specified'
                else:
                    if temp_unit[0].upper() == 'C':
                        self.TEVcloud.teslaEV_SetTempUnit(0)
                    else:
                        self.TEVcloud.teslaEV_SetTempUnit(1)

        else:
            logging.warning('No TEMP_UNIT')
            self.customParameters['TEMP_UNIT'] = 'C or F'


        if 'VIN' in userParams:
            if self.customParameters['VIN'] != 'EV VIN':
                self.EVid = str(self.customParameters['VIN'])
        else:
            logging.warning('No VIN')
            self.customParameters['VIN'] = 'EV VIN'
            self.EVid = None


        
        if 'LOCATION_EN' in userParams:
            if self.customParameters['LOCATION_EN'] != 'True or False':
                self.locationEn = str(self.customParameters['LOCATION_EN'])
                if self.locationEn.upper() not in ['TRUE', 'FALSE']:
                    logging.error(f'Unsupported Location Setting {self.locationEn}')
                    self.poly.Notices['location'] = 'Unknown distance Unit specified'
                else:
                    self.TEVcloud.teslaEV_set_location_enabled(self.locationEn)
                    
        else:
            logging.warning('No LOCATION')
            self.customParameters['LOCATION_EN'] = 'True or False'   
        self.customParam_done = True

        logging.debug('customParamsHandler finish ')


    def init_webhook(self, EVid):
        init ={}
        init['name'] = 'Tesla'
        init['assets']  = [EVid]
        logging.debug(f'webhook_ init {init}')
        self.poly.webhookStart(init)

    def webhook(self, data): 
        try:
            logging.info(f"Webhook received: { data }")        
            self.TEVcloud.teslaEV_process_stream_data(data)        
            vehicleID = self.TEVcloud.teslaEV_get_stream_id(data)  
            self.status_nodes[vehicleID].update_all_drivers()
        except Exception as e:
            logging.error(f'Exception webhook {e}')

    def start(self):
        logging.info('start')
        EVname = None
        #self.Parameters.load(customParams)
        self.poly.updateProfile()

        #self.poly.setCustomParamsDoc()

        #while not self.customParam_done or not self.customNsDone and not self.config_done:
        while not self.config_done and not self.portalReady:
            logging.info('Waiting for node to initialize')
            logging.debug(' 1 2 3: {} {} {}'.format(self.customParam_done, self.TEVcloud.customNsDone(),self.config_done))
            time.sleep(1)

        logging.debug(f'Portal Credentials: {self.portalID} {self.portalSecret}')
        #self.TEVcloud.initializePortal(self.portalID, self.portalSecret)
        while not self.TEVcloud.portal_ready():
            time.sleep(5)
            logging.debug('Waiting for portal connection')
        while not self.TEVcloud.authenticated():
            logging.info('Waiting to authenticate to complete - press authenticate button')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            time.sleep(5)

        assigned_addresses =['controller']
        code, vehicles = self.TEVcloud.teslaEV_get_vehicles()
        if code in ['ok']:
            self.vehicleList = self.TEVcloud.teslaEV_get_vehicle_list()
            logging.debug(f'vehicleList: {code} - {self.vehicleList}')


        if len(self.vehicleList) > 1 and self.EVid is None:
            self.poly.Notices['VIN']=f"Please one of the following VINs in configuration: {self.vehicleList}"
            self.poly.Notices['VIN2']="Then restart"
            #self.EV_setDriver('GV0', 0, 25)   
            exit()

        if self.EVid is None:
            self.EVid = str(self.vehicleList[0])
            self.customParameters['VIN'] = self.EVid

        EVname = self.TEVcloud.teslaEV_GetName(self.EVid)
            
        

        logging.debug(f'EVname {EVname}')        
        #self.EV_setDriver('GV0', self.bool2ISY(self.EVid is not None), 25)            

        self.init_webhook(self.EVid)

        #self.TEVcloud.teslaEV_check_streaming_certificate_update(self.EVid )
        if not self.TEVcloud.teslaEV_check_streaming_certificate_update(self.EVid ): #We need to update streaming server credentials
            logging.info('ERROR failed to connect to streaming server - EV may be too old')
            exit()
            
        code, state = self.TEVcloud._teslaEV_wake_ev(self.EVid)
  
        sync_status = False
        while not sync_status:
            time.sleep(3)
            code, res = self.TEVcloud.teslaEV_streaming_synched(self.EVid)
            logging.debug(f'{self.EVid} synched {code} {res}')
            if code == 'ok':
                if res['response']['synced'] :
                    sync_status = True
                    if EVname == None or EVname == '':
                        # should not happen but just in case 
                        EVname = 'ev'+str(self.EVid)
                    EVname = str(EVname)
                    nodeAdr = 'ev'+str(self.EVid)[-14:] 
                    nodeName = self.poly.getValidName(EVname)
                    nodeAdr = self.poly.getValidAddress(nodeAdr)
                    if not self.poly.getNode(nodeAdr):
                        logging.debug('Node Address : {} {}'.format(self.poly.getNode(nodeAdr), nodeAdr))
                        logging.info(f'Creating Status node {nodeAdr} for {nodeName}')
                        self.status_node = teslaEV_StatusNode(self.poly, nodeAdr, nodeAdr, nodeName, self.EVid, self.TEVcloud)
                        assigned_addresses.append(nodeAdr)

                        while not (self.status_node.subnodesReady() or self.status_node.statusNodeReady):
                            logging.debug(f'Subnodes {self.status_node.subnodesReady()}  Status {self.status_node.statusNodeReady}')
                            logging.debug('waiting for nodes to be created')
                            time.sleep(5)
                        # need condition to only do this once 
                        # Load data once - need to synchronize data available 
                        logging.info('Getting startup data for node - not streamed')
                        self.TEVcloud.teslaEV_UpdateCloudInfoAwake(self.EVid) #Needs to be enabled once other stuff is working 
                        time.sleep(1)
                        self.status_node.update_all_drivers()


        logging.debug(f'Scanning db for extra nodes : {assigned_addresses}')
        for indx, node  in enumerate(self.nodes_in_db):
            #node = self.nodes_in_db[nde]
            logging.debug(f'Scanning db for node : {node}')
            if node['primaryNode'] not in assigned_addresses:
                logging.debug('Removing node : {} {}'.format(node['name'], node))
                self.poly.delNode(node['address'])
        self.updateISYdrivers()
        self.initialized = True


    def validate_params(self):
        logging.debug('validate_params: {}'.format(self.Parameters.dump()))
        self.paramsProcessed = True


    def stop(self):
        self.Notices.clear()
        #if self.TEV:
        #    self.TEV.disconnectTEV()
        #self.EV_setDriver('ST', 0, 25 )
        logging.debug('stop - Cleaning up')
        self.poly.stop()



    def portal_initialize(self, portalId, portalSecret):
        #logging.debug('portal_initialize {portalId} {portalSecret}')
        #portalId = None
        #portalSecret = None
        self.TEVcloud.initializePortal(portalId, portalSecret)

    def systemPoll(self, pollList):
        logging.debug(f'systemPoll - {pollList}')
        if self.TEVcloud:
            if self.TEVcloud.authenticated():
                #self.TEVcloud.teslaEV_get_vehicles()
                if 'longPoll' in pollList: 
                    self.longPoll()
                    if 'shortPoll' in pollList: #send short polls heart beat as shortpoll is not executed
                        self.heartbeat()
                elif 'shortPoll' in pollList:
                    self.shortPoll()
            else:
                logging.info('Waiting for system/nodes to initialize')

    def shortPoll(self):
        logging.info('Tesla EV Controller shortPoll(HeartBeat)')
        self.heartbeat()
        #try:
        #    logging.debug(f'short poll list - heart beat')
        #except Exception:
        #    logging.info('Not all nodes ready:')

    def longPoll(self):
        logging.info('Tesla EV  Controller longPoll - connected = {}'.format(self.TEVcloud.authenticated()))

        try:
            logging.debug(f'long poll list - checking for token update required')
            self.TEVcloud.teslaEV_check_streaming_certificate_update(self.EVid) #We need to check if we need to update streaming server credentials

        except Exception:
            logging.info(f'Not all nodes ready:')



    def poll(self, type ): # dummey poll function
        #if type in [ 'long']:
        ##    self.updateISYdrivers()
        #else:
        pass

    #def updateISYdrivers(self):
    #    logging.debug('System updateISYdrivers - Controller')       
    #    value = self.TEVcloud.authenticated()
    #    self.EV_setDriver('GV0', self.bool2ISY(value), 25)
    #    #self.EV_setDriver('GV1', self.GV1, 56)
    #    self.EV_setDriver('GV2', self.distUnit, 25)
    #    self.EV_setDriver('GV3', self.tempUnit, 25)



    #def ISYupdate (self, command):
    #    logging.debug('ISY-update main node called')
    #    if self.TEVcloud.authenticated():
    #        self.longPoll()

 
    id = 'controller'
    commands = {   }

    drivers = [
    #        {'driver': 'ST', 'value':0, 'uom':25},
    #        {'driver': 'GV0', 'value':0, 'uom':25},
    #        #{'driver': 'GV1', 'value':0, 'uom':56},
    #        {'driver': 'GV2', 'value':99, 'uom':25},
    #        {'driver': 'GV3', 'value':99, 'uom':25},
            ]
    
            # ST - node started
            # GV0 Access to TeslaApi
            # GV1 Number of EVs



if __name__ == "__main__":
    try:
        logging.info('Starting TeslaEV Controller')
        polyglot = udi_interface.Interface([],{ "enableWebhook": True })

        #TeslaEVController(polyglot, 'controller', 'controller', 'Tesla EVs')
        polyglot.start(VERSION)
        #polyglot.updateProfile()
        polyglot.setCustomParamsDoc()

        TEV_cloud = teslaEVAccess(polyglot, 'energy_device_data energy_cmds vehicle_device_data vehicle_cmds vehicle_charging_cmds open_id offline_access')
        #TEV_cloud = teslaEVAccess(polyglot, 'energy_device_data energy_cmds open_id offline_access')
        #TEV_cloud = teslaEVAccess(polyglot, 'open_id vehicle_device_data vehicle_cmds  vehicle_charging_cmds offline_access')
        logging.debug(f'TEV_Cloud {TEV_cloud}')
        TEV =TeslaEVController(polyglot, 'controller', 'controller', 'Tesla EVs', TEV_cloud)
        
        logging.debug('before subscribe')
        polyglot.subscribe(polyglot.STOP, TEV.stop)
        polyglot.subscribe(polyglot.CUSTOMPARAMS, TEV.customParamsHandler)
        polyglot.subscribe(polyglot.CONFIGDONE, TEV.configDoneHandler)
        #polyglot.subscribe(polyglot.ADDNODEDONE, TEV.node_queue)        
        polyglot.subscribe(polyglot.LOGLEVEL, TEV.handleLevelChange)
        polyglot.subscribe(polyglot.NOTICES, TEV.handleNotices)
        polyglot.subscribe(polyglot.POLL, TEV.systemPoll)
        polyglot.subscribe(polyglot.START, TEV.start, 'controller')
        #polyglot.subscribe(polyglot.WEBHOOK, TEV.webhook)
        logging.debug('Calling start')
        polyglot.subscribe(polyglot.CUSTOMNS, TEV.customNSHandler)
        polyglot.subscribe(polyglot.OAUTH, TEV.oauthHandler)
        
        logging.debug('after subscribe')
        polyglot.ready()
        polyglot.runForever()

        polyglot.setCustomParamsDoc()
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
