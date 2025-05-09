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

    def __init__(self, polyglot, parent, address, name, evid,  pwid, TEVcloud, TPWcloud):
        super(teslaEV_PwrShareNode, self).__init__(polyglot, parent, address, name)
        logging.info('_init_ Tesla Power Share Node')
        self.poly = polyglot
        self.ISYforced = False
        self.EVid = evid
        self.PWid = pwid
        self.TEVcloud = TEVcloud
        self.TPWcloud = TPWcloud
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

        self.ps_state={
            'PowershareStateUnknown':0,
            'PowershareStateInactive':1,
            'PowershareStateHandshaking':2,
            'PowershareStateInit':3,
            'PowershareStateEnabled':4,
            'PowershareStateEnabledReconnectingSoon':5,
            'PowershareStateStopped':6,
            None:99,
        }
        self.ps_stop_reason= {
            'PowershareStopReasonStatusUnknown':0,
            'PowershareStopReasonStatusNone':1,
            'PowershareStopReasonStatusSOCTooLow':2,
            'PowershareStopReasonStatusRetry':3,
            'PowershareStopReasonStatusFault': 4,
            'PowershareStopReasonStatusUser':5,
            'PowershareStopReasonStatusReconnecting':6,
            'PowershareStopReasonStatusAuthentication':7,
            None:99}
        
        self.ps_type = {
            'PowershareTypeStatusUnknown':0,
            'PowershareTypeStatusNone':1,
            'PowershareTypeStatusLoad':2,
            'PowershareTypeStatusHome':3,
            None:99}

        self.operationMode = {  
            'backup':0 ,
            'self_consumption' : 1 , 
            'autonomous' : 2, 
            'site_ctrl' : 3 }
        self.TOU_MODES = ["economics", "balanced"]
        self.gridstatus = {'on_grid':0, 'islanded_ready':1, 'islanded':2, 'transition ot grid':3}
        code, vehicles = self.TEVcloud.teslaEV_get_vehicles()
        logging.info('_init_ Tesla Charge Node COMPLETE')
        logging.debug(f'drivers ; {self.drivers}')
        
        
    def start(self):                
        logging.info(f'Start Tesla EV power share Node: {self.EVid}')  
        self.nodeReady = True

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def poll(self, mode):
        logging.debug(f'PowerShare Poll called {mode}')
        if mode == 'critical':
            self.TPWcloud.teslaUpdateCloudData(self.PWid, 'critical') 
        elif mode == 'all':
            self.TPWcloud.teslaUpdateCloudData(self.PWid, 'all') 

        self.updateISYPWdrivers()

    def node_ready (self):
        return(self.nodeReady )
    
    def update_time(self):
        try:
            temp = self.TEVcloud.teslaEV_GetTimestamp(self.EVid)
            self.EV_setDriver('GV19', temp, 151)   
        except ValueError:
            self.EV_setDriver('GV19', None, 25)        

    def setStormMode(self, command):
        logging.debug('setStormMode : {}'.format(command))
        value = int(command.get('value'))
        self.TPWcloud.tesla_set_storm_mode(self.PWid, value == 1)
        self.EV_setDriver('GV23', value)
        
    def setOperatingMode(self, command):
        try:
            logging.debug('setOperatingMode: {}'.format(command))
            value = int(command.get('value'))
            self.TPWcloud.tesla_set_operation(self.PWid, self.operationMode[value])
            self.EV_setDriver('GV22', value)
        except KeyError:
            self.EV_setDriver('GV22', 99)
    
    def setBackupPercent(self, command):
        logging.debug('setBackupPercent: {}'.format(command))
        value = float(command.get('value'))
        self.TPWcloud.tesla_set_backup_percent(self.PWid, value )
        self.EV_setDriver('GV21', value)

    #def setTOUmode(self, command):
    #    logging.debug('setTOUmode')
    #    value = int(command.get('value'))
    #    self.TPW.setTPW_touMode(value)
    #   self.PW_setDriver('GV4', value)
    
    def set_grid_mode(self, command):
        logging.info('set_grid_mode{}'.format(command))
        query = command.get("query")
        imp_mode = int(query.get("import.uom25"))
        exp_mode = int(query.get("export.uom25"))
        self.TPWcloud.tesla_set_grid_import_export(self.PWid, imp_mode == 1, exp_mode) 
        self.EV_setDriver('GV25', int(query.get("import.uom25")))
        self.EV_setDriver('GV26', exp_mode)

    def set_EV_charge_reserve(self, command):
        logging.debug('setTPW_EV_offgrid_charge_reserve {}'.format(command))
        value = int(command.get('value'))
        self.TPWcloud.tesla_set_off_grid_vehicle_charging(self.PWid, value)
        self.EV_setDriver('GV27', value, 51)


    def ISYupdate (self, command):
        logging.debug('ISY-update called  Setup Node')
        #self.TEVcloud.pollSystemData(self.PWid, 'all')
        self.poll('all')
        self.updateISYdrivers()
            #self.reportDrivers()

    def updateISYdrivers(self):
        try:
            logging.info(f'Powershare updateISYdrivers {self.EVid} {self.drivers}')
            self.update_time()
            #if self.TEVcloud.teslaEV_GetCarState(self.EVid) in ['online']:    
            self.EV_setDriver('ST', self.TEVcloud.teslaEV_PowershareHoursLeft(self.EVid) , 20)
            ev_name = self.TPWcloud.tesla_powershare_connected_ev(self.PWid)
            logging.debug(f'Connected ev {ev_name}')
            self.poly.setDriver('GV0', ev_name)
            self.EV_setDriver('GV1', self.TEVcloud.teslaEV_PowershareInstantaneousPowerKW(self.EVid), 33)
            self.EV_setDriver('GV2', self.ps_state[self.TEVcloud.teslaEV_PowershareStatus(self.EVid)],25)
            self.EV_setDriver('GV3', self.ps_stop_reason[self.TEVcloud.teslaEV_PowershareStopReason(self.EVid)],25)
            self.EV_setDriver('GV4', self.ps_type[self.TEVcloud.teslaEV_PowershareType(self.EVid)], 25) 
            '''
            try:
                self.EV_setDriver('GV5', self.operationMode[self.TEVcloud.teslaExtractOperationMode(self.PWid)])
            except KeyError:
                self.EV_setDriver('GV5', None)
            try: 
                self.EV_setDriver('GV6', self.gridstatus[self.TEVcloud.tesla_grid_staus(self.PWid)])
            except KeyError:
                self.EV_setDriver('GV6', None)
               
            self.EV_setDriver('GV7', self.TEVcloud.tesla_live_grid_service_active(self.PWid))
            self.EV_setDriver('GV8', self.TEVcloud.tesla_home_energy_total(self.PWid, 'today'), 33)

            self.EV_setDriver('GV10', self.TEVcloud.tesla_battery_energy_export(self.PWid, 'today'), 33)       
            self.EV_setDriver('GV11', self.TEVcloud.tesla_battery_energy_import(self.PWid, 'today'), 33)
            self.EV_setDriver('GV12', self.TEVcloud.tesla_grid_energy_export(self.PWid, 'today'), 33) 
            self.EV_setDriver('GV13', self.TEVcloud.tesla_grid_energy_import(self.PWid, 'today'), 33)
            self.EV_setDriver('GV14', self.TEVcloud.tesla_grid_energy_export(self.PWid, 'today')- self.TEVcloud.tesla_grid_energy_import(self.PWid, 'today'), 33)
            self.EV_setDriver('GV15', self.TEVcloud.tesla_home_energy_total(self.PWid, 'yesterday'), 33)
            self.EV_setDriver('GV17', self.TEVcloud.tesla_battery_energy_export(self.PWid, 'yesterday'), 33)       
            self.EV_setDriver('GV18', self.TEVcloud.tesla_battery_energy_import(self.PWid, 'yesterday'), 33)
            self.EV_setDriver('GV20', self.TEVcloud.tesla_grid_energy_export(self.PWid, 'yesterday'), 33) 
            self.EV_setDriver('GV21', self.TEVcloud.tesla_grid_energy_import(self.PWid, 'yesterday'), 33)
            self.EV_setDriver('GV22', self.TEVcloud.tesla_grid_energy_export(self.PWid, 'yesterday')- self.TEVcloud.tesla_grid_energy_import(self.PWid, 'yesterday'), 33)
            self.EV_setDriver('GV23', self.TEVcloud.teslaExtractBackupPercent(self.site_id))
            self.EV_setDriver('GV24', self.TEVcloud.teslaExtractOperationMode(self.site_id))
            self.EV_setDriver('GV25', self.TEVcloud.teslaExtractStormMode(self.site_id))
            '''
        except Exception as e:
            logging.error(f'updateISYdrivers charge node failed: nodes may not be 100% ready {e}')


    def updateISYPWdrivers(self):
        try:
            logging.info(f'Powershare updateISYPWdrivers {self.EVid} {self.PWid} {self.drivers}')
            #self.update_time()
            #if self.TEVcloud.teslaEV_GetCarState(self.EVid) in ['online']:    
            #self.EV_setDriver('ST', self.TEVcloud.teslaEV_PowershareHoursLeft(self.EVid) , 20)
            #self.EV_setDriver('GV1', self.TEVcloud.teslaEV_PowershareInstantaneousPowerKW(self.EVid), 33)
            #self.EV_setDriver('GV2', self.ps_state[self.TEVcloud.teslaEV_PowershareStatus(self.EVid)],25)
            #self.EV_setDriver('GV3', self.ps_stop_reason[self.TEVcloud.teslaEV_PowershareStopReason(self.EVid)],25)
            #self.EV_setDriver('GV4', self.ps_type[self.TEVcloud.teslaEV_PowershareType(self.EVid)], 25) 

            try:
                self.EV_setDriver('GV5', self.operationMode[self.TPWcloud.teslaExtractOperationMode(self.PWid)])
            except KeyError:
                self.EV_setDriver('GV5', None)
            try: 
                self.EV_setDriver('GV6', self.gridstatus[self.TPWcloud.tesla_grid_staus(self.PWid)])
            except KeyError:
                self.EV_setDriver('GV6', None)

            self.EV_setDriver('GV7', self.TPWcloud.tesla_live_grid_service_active(self.PWid))
            self.EV_setDriver('GV8', self.TPWcloud.tesla_home_energy_total(self.PWid, 'today'), 33)

            self.EV_setDriver('GV10', self.TPWcloud.tesla_battery_energy_export(self.PWid, 'today'), 33)       
            self.EV_setDriver('GV11', self.TPWcloud.tesla_battery_energy_import(self.PWid, 'today'), 33)
            exportPwr = self.TPWcloud.tesla_grid_energy_export(self.PWid, 'today')
            self.EV_setDriver('GV12', exportPwr, 33) 
            importPwr =  self.TPWcloud.tesla_grid_energy_import(self.PWid, 'today')
            self.EV_setDriver('GV13',importPwr, 33)
            if importPwr is not None and exportPwr is not None:
                self.EV_setDriver('GV14', exportPwr- importPwr, 33)
            else:
                self.EV_setDriver('GV14', 99, 25)
            self.EV_setDriver('GV15', self.TPWcloud.tesla_home_energy_total(self.PWid, 'yesterday'), 33)
            self.EV_setDriver('GV17', self.TPWcloud.tesla_battery_energy_export(self.PWid, 'yesterday'), 33)       
            self.EV_setDriver('GV18', self.TPWcloud.tesla_battery_energy_import(self.PWid, 'yesterday'), 33)
            exportPwr = self.TPWcloud.tesla_grid_energy_export(self.PWid, 'yesterday')
            self.EV_setDriver('GV20', exportPwr, 33) 
            importPwr =  self.TPWcloud.tesla_grid_energy_import(self.PWid, 'yesterday')
            self.EV_setDriver('GV21',importPwr, 33)
            if importPwr is not None and exportPwr is not None:
                self.EV_setDriver('GV22', exportPwr- importPwr, 33)
            else:
                self.EV_setDriver('GV22', 99, 25)
            self.EV_setDriver('GV23', self.TPWcloud.teslaExtractBackupPercent(self.PWid))
            self.EV_setDriver('GV24', self.TPWcloud.teslaExtractOperationMode(self.PWid))
            self.EV_setDriver('GV25', self.TPWcloud.teslaExtractStormMode(self.PWid))
        except Exception as e:
            logging.error(f'updateISYPWdrivers charge node failed: nodes may not be 100% ready {e}')

    #def ISYupdate (self, command):
    #    logging.info('ISY-update called')
    #    code, state = self.TEVcloud.teslaEV_update_connection_status(self.EVid)
    #    code, res = self.TEVcloud.teslaEV_UpdateCloudInfo(self.EVid)
    #    self.updateISYPWdrivers()
    #    self.update_time()
    #    self.EV_setDriver('GV21', self.command_res2ISY(code), 25)
     

    id = 'pwrshare'

    commands = { 'UPDATE': ISYupdate
                ,'BACKUP_PCT'   : setBackupPercent
                ,'STORM_MODE'   : setStormMode
                ,'OP_MODE'      : setOperatingMode
                ,'GRID_MODE'    : set_grid_mode
                ,'EV_CHRG_MODE' : set_EV_charge_reserve
                }

    drivers = [
            {'driver': 'ST', 'value': 99, 'uom': 25},  #hours left-
            {'driver': 'GV0', 'value': 'None', 'uom': 145},      
            {'driver': 'GV1', 'value': 99, 'uom': 25},  #InstantaneousPowerKW
            {'driver': 'GV2', 'value': 99, 'uom': 25},  #Status
            {'driver': 'GV3', 'value': 99, 'uom': 25},  #charge_port_latch
            {'driver': 'GV4', 'value': 99, 'uom': 25}, #Stop Reason
            {'driver': 'GV5', 'value': 99, 'uom': 25},  
            {'driver': 'GV6', 'value': 99, 'uom': 25},  
            {'driver': 'GV7', 'value': 99, 'uom': 25},  
            #{'driver': 'GV29', 'value': 99, 'uom': 25}, 
            {'driver': 'GV8', 'value': 99, 'uom': 25}, 

            #{'driver': 'GV9', 'value': 0, 'uom': 33}, 
            {'driver': 'GV10', 'value': 0, 'uom': 33},  
            {'driver': 'GV11', 'value': 0, 'uom': 33},  
            {'driver': 'GV12', 'value': 0, 'uom': 33},
            {'driver': 'GV13', 'value': 0, 'uom': 33}, 
            {'driver': 'GV14', 'value': 0, 'uom': 33}, 
            {'driver': 'GV15', 'value': 0, 'uom': 33}, 

            {'driver': 'GV17', 'value': 0, 'uom': 33}, 
            {'driver': 'GV18', 'value': 0, 'uom': 33}, 

            {'driver': 'GV20', 'value': 0, 'uom': 33}, 
            {'driver': 'GV21', 'value': 0, 'uom': 33},


            {'driver': 'GV22', 'value': 0, 'uom': 0},
            {'driver': 'GV23', 'value': 0, 'uom': 58},
            {'driver': 'GV24', 'value': 0, 'uom': 0}, 
            {'driver': 'GV25', 'value': 0, 'uom': 58}, 
            {'driver': 'GV19', 'value': 0, 'uom': 151},  #PowerShare Typ   
            {'driver': 'GV29', 'value': 0, 'uom': 151},  #PowerShare Typ   

            ]
            


