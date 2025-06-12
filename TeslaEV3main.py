#!/usr/bin/env python3

import sys
import time 
from queue import Queue
from threading import Thread, Event, Lock
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=20)
import threading
import json
from TeslaEVapi import teslaEVAccess
from TeslaPWapi import teslaPWAccess
from TeslaAPIOauth import teslaApiAccess
#from TeslaEVStatusNode import teslaEV_StatusNode
from TeslaEVClimateNode import teslaEV_ClimateNode
from TeslaEVChargeNode import teslaEV_ChargeNode
from TeslaEVPwrShareNode import teslaEV_PwrShareNode
from TeslaEVapi import teslaAccess


VERSION = '0.1.44'

class TeslaEVController(udi_interface.Node):
    from  udiLib import node_queue, command_res2ISY, code2ISY, wait_for_node_done,tempUnitAdjust, display2ISY, sentry2ISY, setDriverTemp, cond2ISY,  mask2key, heartbeat, state2ISY, sync_state2ISY, bool2ISY, online2ISY, EV_setDriver, openClose2ISY

    def __init__(self, polyglot, primary, address, name, tesla_api ):
        super(TeslaEVController, self).__init__(polyglot, primary, address, name)
        logging.info(f'_init_ Tesla EV Controller {VERSION}')
        logging.setLevel(10)
        logging.debug('Init Message system')
        self.messageQueue = Queue()
        self.background_thread = threading.Thread(target=self.process_message)
        self.background_thread.daemon = True  # Daemonize thread
        self.background_thread.start()

        self.poly = polyglot
        self.node = None
        self.portalID = None
        self.portalSecret = None
        self.n_queue = []
        self.vehicleList = []
        self.vin_list = [] # needed for streaming server
        #self.stream_cert = {}
        self.tesla_api = tesla_api
        self.TEVcloud = teslaEVAccess(self.poly, self.tesla_api)
        self.TPWcloud = teslaPWAccess(self.poly, self.tesla_api)
        self.power_share_node = None
        self.ISYforced = False
        self.CELCIUS = 0
        self.FARENHEIT = 1 
        self.KM = 0
        self.MILES = 1
        self.supportedParams = ['DIST_UNIT', 'TEMP_UNIT']
        self.paramsProcessed = False
        self.customParameters = Custom(self.poly, 'customparams')
        self.portalData = Custom(self.poly, 'customNSdata')
        self.Notices = Custom(polyglot, 'notices')
        self.initialized = False
        self.STATE_UPDATE_MIN = 15
        self.primary = primary
        self.address = address
        self.name = name
        self.webhookTestTimeoutSeconds = 5

        polyglot.subscribe(polyglot.STOP, self.stop)
        polyglot.subscribe(polyglot.CUSTOMPARAMS, self.customParamsHandler)
        polyglot.subscribe(polyglot.CONFIGDONE, self.configDoneHandler)
        #polyglot.subscribe(polyglot.ADDNODEDONE, TEV.node_queue)        
        polyglot.subscribe(polyglot.LOGLEVEL, self.handleLevelChange)
        polyglot.subscribe(polyglot.NOTICES, self.handleNotices)
        polyglot.subscribe(polyglot.POLL, self.systemPoll)        
        polyglot.subscribe(polyglot.WEBHOOK, self.webhook)
        logging.debug('Calling start')
        polyglot.subscribe(polyglot.START, self.start, 'controller')
        polyglot.subscribe(polyglot.CUSTOMNS, self.customNSHandler)
        polyglot.subscribe(polyglot.OAUTH, self.oauthHandler)
        polyglot.subscribe(polyglot.ADDNODEDONE, self.node_queue)
        self.hb = 0
        self.connected = False
        self.nodeDefineDone = False
        self.customNsDone = False
        self.portalReady = False
        self.poly.updateProfile()
        self.poly.ready()
        self.tempUnit = 0 # C
        self.distUnit = 0 # KM
        self.customParam_done = False
        self.config_done = False
        #self.poly.setLogLevel('debug')
        self.poly.addNode(self, conn_status = None, rename = False)
        #self.poly.addNode(self)
        self.wait_for_node_done()
        self.node = self.poly.getNode(self.address)
        self.EVid = None
        self.data_flowing = False
        self.nbr_wall_conn = 0

        logging.info('Controller init DONE')
        logging.debug(f'drivers ; {self.drivers}')

    def check_config(self):
        self.nodes_in_db = self.poly.getNodesFromDb()
        #self.config_done= True


    def configDoneHandler(self):
        logging.debug('configDoneHandler - config_done')
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.config_done= True
        try:
            self.tesla_api.getAccessToken()
        except ValueError:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
        return

    def oauthHandler(self, token):
        # When user just authorized, pass this to your service, which will pass it to the OAuth handler
        self.tesla_api.oauthHandler(token)
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

            if 'PortalSecret' in data:
                self.portalSecret = data['PortalSecret']
            self.portalReady = True

            logging.debug(f'Custom Data portal: {self.portalID} {self.portalSecret}')

        self.tesla_api.customNsHandler(key, data)
        self.customNsDone =self.tesla_api.customNsDone()
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
                    self.tesla_api.cloud_set_region(region)
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
                    self.poly.Notices['location'] = 'Unknown Location setting '
                else:
                    self.tesla_api.teslaEV_set_location_enabled(self.locationEn)
                    if self.locationEn.upper() == 'TRUE':
                        self.tesla_api.append_scope('vehicle_location')
                    
        else:
            logging.warning('No LOCATION')
            self.customParameters['LOCATION_EN'] = 'True or False'   
        self.customParam_done = True

        logging.debug('customParamsHandler finish ')
        
    def process_message(self):
        logging.debug('Stating proccess_message thread')
        while True:
            try:
      
                data = self.messageQueue.get(timeout = 10) 
                logging.debug('Received message - Q size={}'.format(self.messageQueue.qsize()))

                evID = self.TEVcloud.teslaEV_stream_get_id(data)
                logging.debug(f'EVid in data = {evID}')
                if evID == self.EVid:
                    self.TEVcloud.teslaEV_stream_process_data(data)
                    if self.subnodesReady():            
                        self.update_all_drivers()
                        self.EV_setDriver('ST', 1, 25) # Car must be online to stream data 
                time.sleep(1)

            except Exception as e:
                logging.debug('message processing timeout - no new commands')
                pass

        #@measure_time
    def insert_message(self, msg):
        logging.debug('insert_message: {}'.format(msg))
        self.messageQueue.put(msg)
        qsize = self.messageQueue.qsize()
        logging.debug('Message received and put in queue (size : {})'.format(qsize))
        #logging.debug('Creating threads to handle the received messages')
        #threads = []
        ##for idx in range(0, qsize):
        #    threads.append(Thread(target = self.process_message ))
        #[t.start() for t in threads]
        #logging.debug('{} on_message threads starting'.format(qsize))

    def init_webhook(self, EVid):
        EV = str(EVid)
        init_w ={}
        init_w['name'] = 'Tesla'
        init_w['assets'] = []
        tmp = {}
        tmp['id'] = str(EVid)
        init_w['assets'].append(tmp)
        init_w = {"assets":[{"id":EV}], "name":"Tesla"}
        logging.debug(f'EVid {type(EVid)} {type(str(EVid))}')
        logging.debug(f'webhook_init {init_w}')        
        self.poly.webhookStart(init_w)
        time.sleep(2)
        #self.test()


    def webhook(self, data): 
        try:
            logging.info(f"Webhook received: { data }")  
            if 'body' in data:
                logging.info(f'webhook test received')
                eventInfo = json.loads(data['body'])

                if  eventInfo['event'] == 'webhook-test':
                    self.activate()
            else:
                self.data_flowing = True
                self.insert_message(data)
                qsize = self.messageQueue.qsize()
                while qsize != 0:
                    time.sleep(1)
                    qsize = self.messageQueue.qsize()
                #if self.subnodesReady():            
                #    self.update_all_drivers()
                '''
                evID = self.TEVcloud.teslaEV_stream_get_id(data)
                logging.debug(f'EVid in data = {evID}')
                #if evID in self.EVid:
                self.TEVcloud.teslaEV_stream_process_data(data)
                if self.subnodesReady():            
                    self.update_all_drivers()
                '''
        except Exception as e:
            logging.error(f'Exception webhook {e}')

    def start(self):
        logging.info('start main node')
        self.poly.Notices.clear()
        EVname = None
        #self.Parameters.load(customParams)
        self.poly.updateProfile()

        #self.poly.setCustomParamsDoc()

        while not self.customParam_done or not self.customNsDone or not self.config_done or not self.portalReady:
        #while not self.config_done and not self.portalReady :
            logging.info(f'Waiting for node to initialize {self.customParam_done} {self.customNsDone} {self.config_done} {self.portalReady}')
            #logging.debug(f' 1 2 3: {} {} {} {}'.format(self.customParam_done, , self.config_done))
            time.sleep(1)
        self.tesla_api.initializePortal(self.portalID, self.portalSecret)
        #logging.debug(f'Portal Credentials: {self.portalID} {self.portalSecret}')
        #self.tesla_api.initializePortal(self.portalID, self.portalSecret)
        while not self.tesla_api.portal_ready():
            time.sleep(5)
            logging.debug('Waiting for portal connection')
        while not self.tesla_api.authenticated():
            logging.info('Waiting to authenticate to complete - press authenticate button')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            time.sleep(5)

        assigned_addresses =[self.id]
        self.node_addresses = [self.id]
        self.poly.Notices['products'] = 'Acquiring supported products'
        self.PW_siteid, self.nbr_wall_conn = self.TPWcloud.tesla_get_energy_products()
        logging.debug(f'Nbr Wall Cons main {self.nbr_wall_conn}')
        self.tesla_api.teslaEV_set_power_share_enabled(self.nbr_wall_conn > 0)
               
        code, vehicles = self.TEVcloud.teslaEV_get_vehicles()
        if code in ['ok']:
            self.vehicleList = self.TEVcloud.teslaEV_get_vehicle_list()
            logging.debug(f'vehicleList: {code} - {self.vehicleList}')
        else:
            self.poly.Notices['REG']=f"Cannot get data from EV - make sure it is authenticated"
            #self.EV_setDriver('GV0', 0, 25)   
            sys.exit()

        if len(self.vehicleList) > 1 and self.EVid is None:
            self.poly.Notices['VIN']=f"Please enter one of the following VINs in configuration: {self.vehicleList}"
            self.poly.Notices['VIN2']="Then restart"
            #self.EV_setDriver('GV0', 0, 25)   
            sys.exit()
        elif len(self.vehicleList) == 0:
            self.poly.Notices['VIN2']="Then restart"

        if self.EVid is None or self.EVid == '':
            self.EVid = str(self.vehicleList[0])
            self.customParameters['VIN'] = self.EVid
        logging.debug(f'EVid {self.EVid}')
        EVname = self.TEVcloud.teslaEV_GetName(self.EVid)

        logging.debug(f'EVname {EVname}') 
        self.init_webhook(self.EVid)       
        #self.EV_setDriver('GV0', self.bool2ISY(self.EVid is not None), 25)            
        if EVname == None or EVname == '':
            # should not happen but just in case or user has not given name to EV
            EVname = 'ev'+str(self.EVid)
            EVname = str(EVname)
        nodeName = self.poly.getValidName(EVname)
        self.node.rename(nodeName)
        assigned_addresses.append(self.address)
        self.poly.Notices['subnotes'] = 'Creating sub-notes - 2 or 3 depending on powershare support'
        time.sleep(1)
        self.poly.Notices.delete('products')
        self.createSubNodes()
        #logging.debug(f'climate drivers1 {self.climateNode.drivers}')
        while not (self.subnodesReady()):
            logging.debug(f'Subnodes {self.subnodesReady()} ')
            logging.debug('waiting for nodes to be created')
            time.sleep(5)
        #logging.debug(f'climate drivers2 {self.climateNode.drivers}')
        self.initialized = True   
        code, state = self.TEVcloud._teslaEV_wake_ev(self.EVid)
        logging.debug(f'Wake EV {code} {state}')
        if state not in ['online']:
            self.poly.Notices['NOTONLINE']=f'{EVname} appears offline - cannot continue with EV being online'
        # force creation of new config - assume this will enable retransmit of all data 
        self.poly.Notices['subscribe1'] = 'Subscribing to datastream from EV'
        if not self.tesla_api.teslaEV_streaming_check_certificate_update(self.EVid, True ): #We need to update streaming server credentials
            logging.info('')
            self.poly.Notices['SYNC']=f'{EVname} ERROR failed to connect to streaming server - EV may be too old'
            #self.stop()
            sys.exit()
        
        time.sleep(2)      
        self.poly.Notices['subscribe2'] = 'Waiting for EV to synchronize datastream - this may take some time '
        
        count = 0
        while not self.tesla_api.teslaEV_streaming_synched(self.EVid) or self.data_flowing:
            count += 1
            if count <= 12:
                time.sleep(10)
            elif count <= 24:
                time.sleep(300)
            else:
                self.poly.Notices['subscribe3'] = 'Not able to synchronize to server - enable debug under log try again and send log to developer'
                sys.exit()
        self.poly.Notices.delete('subscribe2')


        self.EV_setDriver('ST', 1, 25)  # EV is synched so online 
        #logging.debug(f'climate drivers5 {self.climateNode.drivers}')                    
        logging.debug(f'Scanning db for extra nodes : {assigned_addresses} - {self.node_addresses}')

        for indx, node  in enumerate(self.nodes_in_db):
            #node = self.nodes_in_db[nde]
            logging.debug(f'Scanning db for node : {node}')
            if node['primaryNode'] not in assigned_addresses:
                logging.debug('Removing node : {} {}'.format(node['name'], node))
                self.poly.delNode(node['address'])
            if node['address'] not in self.node_addresses:
                logging.debug('Removing node : {} {}'.format(node['name'], node))
                self.poly.delNode(node['address'])
        
        #logging.debug(f'climate drivers6 {self.climateNode.drivers}')

        self.update_all_drivers()
        self.poly.Notices['done'] = 'Initialization process completed'
        time.sleep(2)
        self.poly.Notices.clear()
        #logging.debug(f'climate drivers7 {self.climateNode.drivers}')

    def validate_params(self):
        logging.debug('validate_params: {}'.format(self.Parameters.dump()))
        self.paramsProcessed = True


    def stop(self):
        self.Notices.clear()
        #self.background_thread.stop()
        #if self.TEV:
        self.tesla_api.teslaEV_streaming_delete_config(self.EVid)
        self.EV_setDriver('ST', 0, 25 )
        logging.debug('stop - Cleaning up')
        #self.scheduler.shutdown()
        self.poly.stop()
        sys.exit() # kill running threads



    def portal_initialize(self, portalId, portalSecret):
        logging.debug(f'portal_initialize {portalId} {portalSecret}')
        #portalId = None
        #portalSecret = None
        self.tesla_api.initializePortal(portalId, portalSecret)

    def systemPoll(self, pollList):
        logging.debug(f'systemPoll - {pollList}')
        if self.TEVcloud:
            logging.debug(f'systemPoll {self.tesla_api.authenticated()} {self.initialized}')
            if self.tesla_api.authenticated() and self.initialized:
                time_n = int(time.time())
                last_time = self.TEVcloud.teslaEV_GetTimestamp(self.EVid)
                logging.debug(f'tine now {time_n} , last_time {last_time}')
                if last_time is None:
                    code, state = self.TEVcloud.teslaEV_GetCarState(self.EVid)
                    if state:
                        self.EV_setDriver('ST', self.state2ISY(state), 25)
                        self.poly.Notices.delete('offline')
                    else:
                        self.poly.Notices['offline']='API connection Failure - please re-authenticate'
                        self.EV_setDriver('ST', 98, 25)
                            #self.TEVcloud.teslaEV_get_vehicles()
                elif isinstance(time_n, int) and isinstance(last_time, int):
                    if (time_n - last_time) > self.STATE_UPDATE_MIN * 60:
                        code, state = self.TEVcloud.teslaEV_GetCarState(self.EVid)
                        if state:
                            self.EV_setDriver('ST', self.state2ISY(state), 25)
                            self.poly.Notices.delete('offline')
                        else:
                            self.poly.Notices['offline']='API connection Failure - please re-authenticate'
                            self.EV_setDriver('ST', 98, 25)
                            #self.TEVcloud.teslaEV_get_vehicles()
                if 'longPoll' in pollList: 
                    self.longPoll()
                    if 'shortPoll' in pollList: #send short polls heart beat as shortpoll is not executed
                        self.heartbeat()
                if self.nbr_wall_conn != 0:
                        self.power_share_node.poll('all')
                if 'shortPoll' in pollList:
                    self.shortPoll()
                    if self.nbr_wall_conn != 0:
                        self.power_share_node.poll('critical')
            else:
                logging.info('Waiting for system/nodes to initialize')

    def shortPoll(self):
        try:
            logging.info('Tesla EV Controller shortPoll(HeartBeat)')
            self.heartbeat()
            if self.nbr_wall_conn != 0:
                self.power_share_node.poll('critical')


        except Exception:
            logging.info('Not all nodes ready:')

    def longPoll(self):
        try:
            logging.info('Tesla EV  Controller longPoll - connected = {}'.format(self.tesla_api.authenticated()))
            logging.debug(f'long poll list - checking for token update required')
            self.tesla_api.teslaEV_streaming_check_certificate_update(self.EVid) #We need to check if we need to update streaming server credentials
            if self.nbr_wall_conn != 0:
                self.power_share_node.poll('critical')
        except Exception:
            logging.info(f'Not all nodes ready:')


    def createSubNodes(self):
        logging.debug(f'Creating sub nodes for {self.EVid}')
        nodeAdr = 'climate'+str(self.EVid)[-9:]
        nodeName = self.poly.getValidName('Climate Info')
        nodeAdr = self.poly.getValidAddress(nodeAdr)
        #if not self.poly.getNode(nodeAdr):
        logging.info(f'Creating ClimateNode: {nodeAdr} - {self.primary} {nodeAdr} {nodeName} {self.EVid}')
        self.climateNode = teslaEV_ClimateNode(self.poly, self.primary, nodeAdr, nodeName, self.EVid, self.TEVcloud )
        time.sleep(2)
        self.node_addresses.append(nodeAdr)

        nodeAdr = 'charge'+str(self.EVid)[-10:]
        nodeName = self.poly.getValidName('Charging Info')
        nodeAdr = self.poly.getValidAddress(nodeAdr)
        self.node_addresses.append(nodeAdr)
        #if not self.poly.getNode(nodeAdr):
        logging.info(f'Creating ChargingNode: {nodeAdr} - {self.primary} {nodeAdr} {nodeName} {self.EVid}')
        self.chargeNode = teslaEV_ChargeNode(self.poly, self.primary, nodeAdr, nodeName, self.EVid, self.TEVcloud )
        time.sleep(2)
        logging.debug(f'Nbr Wall Cons create: {self.nbr_wall_conn}')
        if self.nbr_wall_conn != 0: 
            nodeAdr = 'pwrshare'+str(self.EVid)[-8:]
            nodeName = self.poly.getValidName('Powershare Info')
            nodeAdr = self.poly.getValidAddress(nodeAdr)
            logging.info(f'Creating pwrshare: {nodeAdr} - {self.primary} {nodeAdr} {nodeName} {self.PW_siteid}')
            self.power_share_node = teslaEV_PwrShareNode(self.poly, self.primary, nodeAdr, nodeName, self.EVid, self.PW_siteid, self.TEVcloud, self.TPWcloud )
            self.node_addresses.append(nodeAdr)
        #logging.debug(f'climate drivers0 {self.climateNode.drivers}')
        time.sleep(2)

    def subnodesReady(self):
        if self.power_share_node is None:
            return(self.climateNode.nodeReady and self.chargeNode.nodeReady)
        else:
            return(self.climateNode.nodeReady and self.chargeNode.nodeReady and self.power_share_node.nodeReady)

    def ready(self):
        if self.power_share_node is None:
            return(self.climateNode.nodeReady and self.chargeNode.nodeReady)
        else:
            return(self.climateNode.nodeReady and self.chargeNode.nodeReady and self.power_share_node.nodeReady)

    def update_time(self):
        logging.debug('update_time')
        try:
            temp = self.TEVcloud.teslaEV_GetTimestamp(self.EVid)
            self.EV_setDriver('GV19', temp , 151)
        except ValueError:
            self.EV_setDriver('GV19', None, 25)


    '''
    def poll (self, type ):    
        logging.info(f'Status Node Poll for {self.EVid} - poll type: {type}')        
        #pass
        
        try:
            if type in ['short']:
               #code, state  = self.TEVcloud.teslaEV_UpdateCloudInfoAwake(self.EVid)
            elif type in ['long']:
                #code, state =  self.TEVcloud.teslaEV_UpdateCloudInfo(self.EVid)
            else:
                return
            logging.debug(f'Poll data code {code} , {state}')
            self.update_all_drivers()
            self.display_update()

            #if state in[ 'online', 'offline', 'asleep', 'overload', 'error', 'on-link']:
            #    self.EV_setDriver('ST', self.state2ISY(state), 25)
                #logging.info('Car appears off-line/sleeping or overload  - not updating data')

            #else:
            #    self.EV_setDriver('ST', 99, 25)

        except Exception as e:
                logging.error(f'Status Poll exception : {e}')
    '''    

    def update_all_drivers(self):
        try:
            if self.data_flowing:
                logging.debug('updateISYdrivers')
                self.updateISYdrivers()
                logging.debug(f'climate updateISYdrivers {self.climateNode.node_ready()}')
                if self.climateNode.node_ready():
                    self.climateNode.updateISYdrivers()
                logging.debug(f'charge updateISYdrivers {self.chargeNode.node_ready()}')                
                if self.chargeNode.node_ready():
                    self.chargeNode.updateISYdrivers()
                    
                if self.nbr_wall_conn != 0: 
                    logging.debug(f'power share updateISYdrivers {self.power_share_node.node_ready()}')   
                    if self.power_share_node.node_ready():
                        self.power_share_node.updateISYdrivers()
        except Exception as e:
            logging.debug(f'All nodes may not be ready yet {e}')


    def updateISYdrivers(self):
        try:
            logging.debug(f'Update main node {self.drivers}')
            self.update_time()

            self.EV_setDriver('GV29', self.sync_state2ISY(self.tesla_api.stream_synched), 25)

            logging.info(f'updateISYdrivers - Status for {self.EVid}')
            self.EV_setDriver('GV1',self.display2ISY(self.TEVcloud.teslaEV_GetCenterDisplay(self.EVid)), 25)
            self.EV_setDriver('GV2', self.bool2ISY(self.TEVcloud.teslaEV_HomeLinkNearby(self.EVid)), 25)
            self.EV_setDriver('GV0', self.TEVcloud.teslaEV_nbrHomeLink(self.EVid), 25)

            self.EV_setDriver('GV3', self.bool2ISY(self.TEVcloud.teslaEV_GetLockState(self.EVid)), 25)
            if self.TEVcloud.teslaEV_GetDistUnit() == 1:
                self.EV_setDriver('GV4', self.TEVcloud.teslaEV_GetOdometer(self.EVid), 116)
            else:
                self.EV_setDriver('GV4', int(self.TEVcloud.teslaEV_GetOdometer(self.EVid)*1.6), 83)
            temp = self.TEVcloud.teslaEV_GetSentryState(self.EVid)
            #logging.debug(f'teslaEV_GetSentryState {temp}')
            temp_val = self.sentry2ISY(temp)
            #logging.debug(f'teslaEV_GetSentryState ISY {temp_val}')
            self.EV_setDriver('GV5', temp_val, 25)
            
            windows  = self.TEVcloud.teslaEV_GetWindowStates(self.EVid)
            #logging.debug(f'teslaEV_GetSientryState ISY {windows}')
            if 'FrontLeft' not in windows:
                windows['FrontLeft'] = None
            if 'FrontRight' not in windows:
                windows['FrontRight'] = None
            if 'RearLeft' not in windows:
                windows['RearLeft'] = None
            if 'RearRight' not in windows:
                windows['RearRight'] = None
            self.EV_setDriver('GV6', windows['FrontLeft'], 25)
            self.EV_setDriver('GV7', windows['FrontRight'], 25)
            self.EV_setDriver('GV8', windows['RearLeft'], 25)
            self.EV_setDriver('GV9', windows['RearRight'], 25)
            
            #self.EV_setDriver('GV10', self.TEVcloud.teslaEV_GetSunRoofPercent(self.EVid), 51)
            #if self.TEVcloud.teslaEV_GetSunRoofState(self.EVid) != None:
            #    self.EV_setDriver('GV10', self.openClose2ISY(self.TEVcloud.teslaEV_GetSunRoofState(self.EVid)), 25)
    
            self.EV_setDriver('GV11', self.TEVcloud.teslaEV_GetTrunkState(self.EVid), 25)
            self.EV_setDriver('GV12', self.TEVcloud.teslaEV_GetFrunkState(self.EVid), 25)

            tire_psi = self.TEVcloud.teslaEV_getTpmsPressure(self.EVid)
            self.EV_setDriver('GV23', tire_psi['tmpsFr'], 138)
            self.EV_setDriver('GV24', tire_psi['tmpsFl'], 138)
            self.EV_setDriver('GV25', tire_psi['tmpsRr'], 138)
            self.EV_setDriver('GV26', tire_psi['tmpsRl'], 138)
            #if self.TEVcloud.location_enabled():

            self.EV_setDriver('GV15', self.bool2ISY(self.TEVcloud.teslaEV_LocatedAtHome(self.EVid)), 25)
            self.EV_setDriver('GV16', self.bool2ISY(self.TEVcloud.teslaEV_LocatedAtFavorite(self.EVid)), 25)


            location = self.TEVcloud.teslaEV_GetLocation(self.EVid)
            #logging.debug(f'teslaEV_GetLocation {location}')
            if location['longitude']:
                logging.debug('GV17: {}'.format(round(location['longitude'], 2)))
                self.EV_setDriver('GV17', round(location['longitude'], 3), 56)
            else:
                logging.debug(f'GV17: NONE')
                self.EV_setDriver('GV17', None, 25)
            if location['latitude']:
                logging.debug('GV18: {}'.format(round(location['latitude'], 2)))
                self.EV_setDriver('GV18', round(location['latitude'], 3), 56)
            else:
                logging.debug('GV18: NONE')
                self.EV_setDriver('GV18', None, 25)
            #else:
            #    self.EV_setDriver('GV17', 98, 25)
            #    self.EV_setDriver('GV18', 98, 25)
        except Exception as e:
            logging.error(f'updateISYdriver main node failed: node may not be 100% ready {e}')

    def ISYupdate (self, command=None):
        logging.info(f'ISY-update status node  called')
        #code, state = self.TEVcloud.teslaEV_update_connection_status(self.EVid)
        self.update_all_drivers()
        #self.display_update()
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)
        if code in ['ok']:
             self.EV_setDriver('GV21', self.command_res2ISY(res),25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code),25)

    def evWakeUp (self, command):
        logging.info(f'EVwakeUp called')
        code, res = self.TEVcloud._teslaEV_wake_ev(self.EVid)
        logging.debug(f'Wake result {code} - {res}')
        if code in ['ok']:               
            time.sleep(2)
            self.update_all_drivers()
        if code in ['ok']:
             self.EV_setDriver('GV21', self.command_res2ISY(res),25)
             self.EV_setDriver('ST', self.state2ISY(res), 25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code),25)


    def evHonkHorn (self, command):
        logging.info(f'EVhonkHorn called')        
        code, res = self.TEVcloud.teslaEV_HonkHorn(self.EVid)
        logging.info(f'return  {code} - {res}')

   
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res),25)
            self.EV_setDriver('ST', 1, 25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code),25)
            code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
            self.EV_setDriver('ST', self.state2ISY(res), 25)


    def evFlashLights (self, command):
        logging.info(f'EVflashLights called')
        code, res = self.TEVcloud.teslaEV_FlashLights(self.EVid)
        logging.info(f'return  {code} - {res}')

        if code in ['ok']:
             self.EV_setDriver('GV21', self.command_res2ISY(res),25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code),25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)

        #self.forceUpdateISYdrivers()

    def evControlDoors (self, command):
        logging.info(f'EVctrlDoors called')
        #self.TEVcloud.teslaEV_Wake(self.EVid)
 
        doorCtrl = int(float(command.get('value')))
        if doorCtrl == 1:
            cmd = 'lock'
            #code, red =  self.TEVcloud.teslaEV_Doors(self.EVid, 'unlock')
            #self.EV_setDriver('GV3', doorCtrl )
        elif doorCtrl == 0:
            cmd = 'unlock'
            #code, res =  self.TEVcloud.teslaEV_Doors(self.EVid, 'lock')
            #self.EV_setDriver('GV3', doorCtrl )            
        else:
            logging.error(f'Unknown command for evControlDoors {command}')
            self.EV_setDriver('GV21', self.command_res2ISY('error'), 25)
            return('error', 'code wrong')
        code, res =  self.TEVcloud.teslaEV_Doors(self.EVid, cmd)
        logging.info(f'return  {code} - {res}')
        self.EV_setDriver('GV3', doorCtrl, 25)
        if code in ['ok']:
             self.EV_setDriver('GV21', self.command_res2ISY(res),25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code),25)
            self.EV_setDriver('GV3', None, 25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)


    def evPlaySound (self, command):
        logging.info(f'evPlaySound called')
        #self.TEVcloud.teslaEV_Wake(self.EVid)
        sound = int(float(command.get('value')))
        if sound == 0 or sound == 2000: 
            code, res = self.TEVcloud.teslaEV_PlaySound(self.EVid, sound)
            if code in ['ok']:
                self.EV_setDriver('GV21', self.command_res2ISY(res),25)
            else:
                self.EV_setDriver('GV21', self.code2ISY(code),25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)

    def evSentryMode (self, command):
        logging.info(f'evSentryMode called')
        #self.TEVcloud.teslaEV_Wake(self.EVid)
        ctrl = int(float(command.get('value')))
     
        code, res = self.TEVcloud.teslaEV_SentryMode(self.EVid, ctrl)
        if code in ['ok']:
             self.EV_setDriver('GV21', self.command_res2ISY(res),25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code),25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)

    # needs update
    def evControlSunroof (self, command):
        logging.info(f'evControlSunroof called')
        #self.TEVcloud.teslaEV_Wake(self.EVid)
        sunroofCtrl = int(float(command.get('value')))
        res = False
        if sunroofCtrl == 1:
            code, res = self.TEVcloud.teslaEV_SunRoof(self.EVid, 'vent')
            #self.EV_setDriver()
        elif sunroofCtrl == 0:
            code, res = self.TEVcloud.teslaEV_SunRoof(self.EVid, 'close')    
        elif sunroofCtrl == 2:
            code, res = self.TEVcloud.teslaEV_SunRoof(self.EVid, 'stop')                  
        else:
            logging.error(f'Wrong command for evSunroof: {sunroofCtrl}')
            code = 'error'
        if code in ['ok']:
             self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)


    def evOpenFrunk (self, command):
        logging.info(f'evOpenFrunk called')
        #self.TEVcloud.teslaEV_Wake(self.EVid)     
        code, res = self.TEVcloud.teslaEV_TrunkFrunk(self.EVid, 'Frunk')
        logging.debug(f'Frunk result {code} - {res}')
        if code in ['ok']:
            self.EV_setDriver('GV12', 1, 25)
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV12', None, 25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)


    def evOpenTrunk (self, command):
        logging.info('evOpenTrunk called')   
        code, res = self.TEVcloud.teslaEV_TrunkFrunk(self.EVid, 'Trunk')
        logging.debug(f'Trunk result {code} - {res}')
        if code in ['ok']:
            self.EV_setDriver('GV11', 1, 25)
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)    
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV11', None, 25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)


    def evHomelink (self, command):
        logging.info('evHomelink called')
        code, res = self.TEVcloud.teslaEV_HomeLink(self.EVid)
        if code in ['ok']:
             self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
        code, res = self.TEVcloud.teslaEV_GetCarState(self.EVid)
        self.EV_setDriver('ST', self.state2ISY(res), 25)



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


    def webhookTimeout(self):
        if self.getDriver('GV30') == 1: # Test in progress
            logging.error(f"Webhook test message timed out after { self.webhookTestTimeoutSeconds } seconds.")
            self.setDriver('GV30', 3, True, True) # 3=Timeout

    def activate(self):
        if self.getDriver('GV30') == 1: # Test in progress
            logging.info('Webhook test message received successfully.')
            self.webhookTimer.cancel()
            self.setDriver('GV30', 2, True, True) # 2=Success

    def test(self, param=None):
        try:
            self.setDriver('GV30', 1, True, True) # 1=Test in progress
            time.sleep(1)
            # Our webhook handler will route this to our activate() function
            body = {
               'event': 'webhook-test',
               'data': {'type':'test',
                        'description' : 'weebhhok test'
               }
            }

            self.TEVcloud.testWebhook(body)
            logging.info('Webhook test message sent successfully.')

            self.webhookTimer = threading.Timer(self.webhookTestTimeoutSeconds, self.webhookTimeout)
            self.webhookTimer.start()

        except Exception as error:
            logging.error(f"Test Webhook API call failed: { error }")
            self.setDriver('GV30', 4, True, True) # 4=failure

    
    id = 'controller'


    commands = { #'UPDATE': ISYupdate, 
                 #'WAKEUP' : evWakeUp,
                 'HONKHORN' : evHonkHorn,
                 'FLASHLIGHT' : evFlashLights,
                 'SENTRYMODE' : evSentryMode,
                 'DOORS' : evControlDoors,
                 'SUNROOF' : evControlSunroof,
                 'TRUNK' : evOpenTrunk,
                 'FRUNK' : evOpenFrunk,
                 'HOMELINK' : evHomelink,
                 'PLAYSOUND' : evPlaySound,
                 'TESTCON'  : test,
                }


    drivers = [
            {'driver': 'ST', 'value': 99, 'uom': 25},   #car State            
            {'driver': 'GV1', 'value': 99, 'uom': 25},  #center_display_state
            {'driver': 'GV2', 'value': 99, 'uom': 25},  # Homelink Nearby
            {'driver': 'GV0', 'value': 99, 'uom': 25},  # nbr homelink devices
            {'driver': 'GV3', 'value': 99, 'uom': 25},  #locked
            {'driver': 'GV4', 'value': 0, 'uom': 116},  #odometer
  
            {'driver': 'GV5', 'value': 0, 'uom': 25},  # Sentury Mode
            {'driver': 'GV6', 'value': 99, 'uom': 25},  #fd_window
            {'driver': 'GV7', 'value': 99, 'uom': 25},  #fp_window
            {'driver': 'GV8', 'value': 99, 'uom': 25},  #rd_window
            {'driver': 'GV9', 'value': 99, 'uom': 25},  #rp_window

            {'driver': 'GV11', 'value': 0, 'uom': 25}, #trunk
            {'driver': 'GV12', 'value': 0, 'uom': 25}, #frunk

            #{'driver': 'GV13', 'value': 0, 'uom': 25}, #door
            #{'driver': 'GV14', 'value': 0, 'uom': 25}, #door
            {'driver': 'GV15', 'value': 0, 'uom': 25}, #Located at home
            {'driver': 'GV16', 'value': 0, 'uom': 25}, #Located at favorite   

            {'driver': 'GV17', 'value': 99, 'uom': 56}, #longitude
            {'driver': 'GV18', 'value': 99, 'uom': 56}, #latitude



            {'driver': 'GV23', 'value': 0, 'uom': 138}, # tire pressure
            {'driver': 'GV24', 'value': 0, 'uom': 138}, # tire pressure
            {'driver': 'GV25', 'value': 0, 'uom': 138}, # tire pressure
            {'driver': 'GV26', 'value': 0, 'uom': 138}, # tire pressure            


            {'driver': 'GV19', 'value': 0, 'uom': 151},  #Last combined update Hours
            {'driver': 'GV21', 'value': 99, 'uom': 25}, #Last Command status
            {'driver': 'GV29', 'value': 99, 'uom': 25}, #Synchronized
            {'driver': 'GV30', 'value': 0, 'uom': 25}, # Test isy API conection result
         
            ]

    
            # ST - node started
            # GV0 Access to TeslaApi
            # GV1 Number of EVs

    '''
        <nodeDef id="controller" nls="nlsevstatus">
        <editors />
        <sts>
         <!--<st id="ST" editor="NODEST" />-->
         <st id="ST" editor="CARSTATE" />
         <st id="GV1" editor="CONSOLE" />
         <st id="GV2" editor="BOOLSTATE" />
         <st id="GV0" editor="NUMBER" />
         <st id="GV3" editor="LOCKUNLOCK" />
         <st id="GV4" editor="ODOMETER" />
         <!--<st id="GV5" editor="BOOLSTATE" />-->
         <st id="GV6" editor="WINDOW" />
         <st id="GV7" editor="WINDOW" />
         <st id="GV8" editor="WINDOW" />
         <st id="GV9" editor="WINDOW" />
         <!--<st id="GV10" editor="PERCENT" />-->
         <st id="GV11" editor="OPENCLOSE" />
         <st id="GV12" editor="OPENCLOSE" />
         <!-- <st id="GV13" editor="CARSTATE" /> -->
         <!-- <st id="GV16" editor="IDEADIST" /> !-->
         <st id="GV17" editor="LONGITUDE" />         
         <st id="GV18" editor="LATITUDE" />  
         <st id="GV19" editor="unixtime" />         
         <!--<st id="GV20" editor="MINU" />    -->
         <st id="GV21" editor="LASTCMD" />   
        </sts>
        <cmds>
         <sends>
            <cmd id="DON" /> 
            <cmd id="DOF" />          
         </sends>
         <accepts>
            <cmd id="UPDATE" /> 
            <cmd id="WAKEUP" />
            <cmd id="HONKHORN" />
            <cmd id="FLASHLIGHT" />   
            <cmd id="DOORS" > 
               <p id="" editor="LOCKUNLOCK" init="GV3" /> 
            </cmd>
            <cmd id="SUNROOF" > 
               <p id="" editor="SUNROOFCTRL" init="0" /> 
            </cmd >
            <cmd id="TRUNK" /> 
            <cmd id="FRUNK" /> 
            <cmd id="HOMELINK" /> 
            <cmd id="PLAYSOUND" > 
               <p id="" editor="SOUNDS" init="0" /> 
    '''

if __name__ == "__main__":
    try:
        logging.info(f'Starting TeslaEV Controller {VERSION}')
        polyglot = udi_interface.Interface([],{ "enableWebhook": True })

        #TeslaEVController(polyglot, 'controller', 'controller', 'Tesla EVs')
        polyglot.start(VERSION)
        #polyglot.updateProfile()
        polyglot.setCustomParamsDoc()

        TeslaApi = teslaApiAccess(polyglot,'energy_device_data energy_cmds vehicle_device_data vehicle_cmds vehicle_charging_cmds open_id offline_access')
        #TEV_cloud = teslaEVAccess(polyglot, 'energy_device_data energy_cmds open_id offline_access')
        #TEV_cloud = teslaEVAccess(polyglot, 'open_id vehicle_device_data vehicle_cmds  vehicle_charging_cmds offline_access')
        logging.debug(f'TeslaAPI {TeslaApi}')

        TEV =TeslaEVController(polyglot, 'controller', 'controller', 'Tesla EV Status', TeslaApi)
        logging.debug('before subscribe')
        #polyglot.subscribe(polyglot.STOP, TEV.stop)
        #polyglot.subscribe(polyglot.CUSTOMPARAMS, TEV.customParamsHandler)
        #polyglot.subscribe(polyglot.CONFIGDONE, TEV.configDoneHandler)
        #polyglot.subscribe(polyglot.ADDNODEDONE, TEV.node_queue)        
        #polyglot.subscribe(polyglot.LOGLEVEL, TEV.handleLevelChange)
        ##polyglot.subscribe(polyglot.NOTICES, TEV.handleNotices)
        #polyglot.subscribe(polyglot.POLL, TEV.systemPoll)        
        #polyglot.subscribe(polyglot.WEBHOOK, TEV.webhook)
        #logging.debug('Calling start')
        #polyglot.subscribe(polyglot.START, TEV.start, 'controller')
        #polyglot.subscribe(polyglot.CUSTOMNS, TEV.customNSHandler)
        #polyglot.subscribe(polyglot.OAUTH, TEV.oauthHandler)
        
        logging.debug('after subscribe')
        polyglot.ready()
        polyglot.runForever()

    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
