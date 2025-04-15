#!/usr/bin/env python3

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

import time

class teslaEV_PwrShareNode(udi_interface.Node):
    #from  udiLib import node_queue, wait_for_node_done, mask2key, latch2ISY, cond2ISY, heartbeat, state2ISY, bool2ISY, online2ISY, EV_setDriver, openClose2ISY
    from  udiLib import node_queue, command_res2ISY, wait_for_node_done, tempUnitAdjust, latch2ISY, chargeState2ISY, setDriverTemp, cond2ISY,  mask2key, heartbeat,  code2ISY, state2ISY, bool2ISY, online2ISY, EV_setDriver, openClose2ISY

    def __init__(self, polyglot, parent, address, name, evid,  TEVcloud):
        super(teslaEV_PwrShareNode, self).__init__(polyglot, parent, address, name)
        logging.info('_init_ Tesla Power Share Node')
        self.poly = polyglot
        self.ISYforced = False
        self.EVid = evid
        self.TEVcloud = TEVcloud
        self.address = address 
        self.name = name
        self.nodeReady = False
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)

        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.nodeReady = True
        logging.info('_init_ Tesla Charge Node COMPLETE')
        logging.debug(f'drivers ; {self.drivers}')

        
    def start(self):                
        logging.info(f'Start Tesla EV power share Node: {self.EVid}')  
        self.nodeReady = True

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def poll(self):
        pass 

    def node_ready (self):
        return(self.nodeReady )
   
    def update_time(self):
        try:
            temp = self.TEVcloud.teslaEV_GetTimestamp(self.EVid)
            self.EV_setDriver('GV19', temp, 151)   
        except ValueError:
            self.EV_setDriver('GV19', None, 25)                                                 



    def updateISYdrivers(self):
        try:
            logging.info(f'Powershare updateISYdrivers {self.EVid}')
            self.update_time()
            #if self.TEVcloud.teslaEV_GetCarState(self.EVid) in ['online']:    
            self.EV_setDriver('ST', self.TEVcloud.teslaEV_PowershareHoursLeft(self.EVid) , 20)
            self.EV_setDriver('GV1', self.TEVcloud.teslaEV_PowershareInstantaneousPowerKW(self.EVid), 33)
            self.EV_setDriver('GV2', self.TEVcloud.teslaEV_PowershareStatus(self.EVid),25)
            self.EV_setDriver('GV3', self.TEVcloud.teslaEV_PowershareStopReason(self.EVid),25)
            self.EV_setDriver('GV4', self.TEVcloud.teslaEV_PowershareType(self.EVid), 25) 
        except Exception as e:
            logging.error(f'updateISYdrivers charge node failed: nodes may not be 100% ready {e}')

    #def ISYupdate (self, command):
    #    logging.info('ISY-update called')
    #    code, state = self.TEVcloud.teslaEV_update_connection_status(self.EVid)
    #    code, res = self.TEVcloud.teslaEV_UpdateCloudInfo(self.EVid)
    #    self.updateISYdrivers()
    #    self.update_time()
    #    self.EV_setDriver('GV21', self.command_res2ISY(code), 25)
     

    id = 'pwrshare'

    #commands = {}

    drivers = [
            {'driver': 'ST', 'value': 99, 'uom': 25},  #hours left-
            {'driver': 'GV1', 'value': 99, 'uom': 25},  #InstantaneousPowerKW
            {'driver': 'GV2', 'value': 99, 'uom': 25},  #Status
            {'driver': 'GV3', 'value': 99, 'uom': 25},  #charge_port_latch
            {'driver': 'GV4', 'value': 99, 'uom': 25}, #Stop Reason
            {'driver': 'GV19', 'value': 0, 'uom': 151},  #PowerShare Typ           
            ]
            


