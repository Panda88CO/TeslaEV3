#!/usr/bin/env python3

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

import time

class teslaEV_ChargeNode(udi_interface.Node):
    #from  udiLib import node_queue, wait_for_node_done, mask2key, latch2ISY, cond2ISY, heartbeat, state2ISY, bool2ISY, online2ISY, EV_setDriver, openClose2ISY
    from  udiLib import node_queue, command_res2ISY, wait_for_node_done, tempUnitAdjust, latch2ISY, chargeState2ISY, setDriverTemp, cond2ISY,  mask2key, heartbeat,  code2ISY, state2ISY, bool2ISY, online2ISY, EV_setDriver, openClose2ISY

    def __init__(self, polyglot, parent, address, name, evid,  TEV):
        super(teslaEV_ChargeNode, self).__init__(polyglot, parent, address, name)
        logging.info('_init_ Tesla Charge Node')
        self.poly = polyglot
        self.ISYforced = False
        self.EVid = evid
        self.TEV = TEV
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
        logging.info('_init_ Tesla Charge Node COMPLETE')
        
    def start(self):                
        logging.info(f'Start Tesla EV charge Node: {self.EVid}')  
        #self.EV_setDriver('ST', 1)
        self.nodeReady = True
        #self.updateISYdrivers()
        #self.update_time()

        

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def poll(self):
        pass 
        #logging.debug(f'Charge node {self.EVid}')
        #try:
        #    if self.TEV.carState != 'Offline':
        #        self.updateISYdrivers()
        #    else:
        #        logging.info('Car appears off-line/sleeping - not updating data')
        #except Exception as e:
        #    logging.error('Charge Poll exception : {e}')


    def chargeNodeReady (self):
        return(self.nodeReady )
   
    def update_time(self):
        try:
            temp = round(float(self.TEV.teslaEV_GetTimeSinceLastCarUpdate(self.EVid)/60), 0)
            self.EV_setDriver('GV19', temp ,44)   
        except ValueError:
            self.EV_setDriver('GV19', None, 25)                                                 
        '''
        try:
            temp = round(float(self.TEV.teslaEV_GetTimeSinceLastStatusUpdate(self.EVid)/60), 0)
            self.EV_setDriver('GV20', temp, 44)
        except ValueError:
            self.EV_setDriver('GV20', None, 25)          
        '''


    def updateISYdrivers(self, code):
        try:
            if code in ['ok']:
                logging.info(f'ChargeNode updateISYdrivers {self.EVid}')
                if self.TEV.teslaEV_GetCarState(self.EVid) in ['online']:                
                    self.EV_setDriver('GV1', self.bool2ISY(self.TEV.teslaEV_FastChargerPresent(self.EVid)), 25)
                    self.EV_setDriver('GV2', self.bool2ISY(self.TEV.teslaEV_ChargePortOpen(self.EVid)),25)
                    self.EV_setDriver('GV3', self.latch2ISY(self.TEV.teslaEV_ChargePortLatched(self.EVid)),25)

                    temp_range = self.TEV.teslaEV_GetBatteryRange(self.EVid)
                    if temp_range is None:
                        self.EV_setDriver('GV4', temp_range, 25)
                    else:
                        if self.TEV.teslaEV_GetDistUnit() == 1:
                            self.EV_setDriver('GV4', round(float(temp_range),1), 116)
                        else:
                            self.EV_setDriver('GV4', round(float(temp_range*1.6),1), 83)

                    self.EV_setDriver('ST', self.TEV.teslaEV_GetBatteryLevel(self.EVid) , 51)


                    temp_current = self.TEV.teslaEV_MaxChargeCurrent(self.EVid) 
                
                    self.EV_setDriver('GV5', temp_current, 1)
                    self.EV_setDriver('GV6',self.chargeState2ISY(self.TEV.teslaEV_ChargeState(self.EVid)), 25)
                    self.EV_setDriver('GV7', self.bool2ISY(self.TEV.teslaEV_ChargingRequested(self.EVid)),25)
                    self.EV_setDriver('GV8',self.TEV.teslaEV_ChargingRequested(self.EVid), 30)
                    self.EV_setDriver('GV9', self.TEV.teslaEV_GetBatteryMaxCharge(self.EVid), 51)
                    self.EV_setDriver('GV10',self.TEV.teslaEV_charger_voltage(self.EVid), 72)
                    self.EV_setDriver('GV11', self.TEV.teslaEV_charge_current_request(self.EVid),1 )
                    self.EV_setDriver('GV12', self.TEV.teslaEV_charger_actual_current(self.EVid), 1)
                    self.EV_setDriver('GV14', self.TEV.teslaEV_time_to_full_charge(self.EVid), 44)
                    self.EV_setDriver('GV15', self.TEV.teslaEV_charge_energy_added(self.EVid), 33)
                    if self.TEV.teslaEV_GetDistUnit() == 1:
                        self.EV_setDriver('GV16', self.TEV.teslaEV_charge_miles_added_rated(self.EVid), 116)
                    else:
                        self.EV_setDriver('GV16', self.TEV.teslaEV_charge_miles_added_rated(self.EVid)*1.6 , 83 )
            else:
                logging.info(f'No new data for ChargeNode for ({self.EVid}) - code: {code}')
        except Exception as e:
            logging.error(f'updateISYdrivers charge node failed: {e}')

    #def ISYupdate (self, command):
    #    logging.info('ISY-update called')
    #    code, state = self.TEV.teslaEV_update_connection_status(self.EVid)
    #    code, res = self.TEV.teslaEV_UpdateCloudInfo(self.EVid)
    #    self.updateISYdrivers()
    #    self.update_time()
    #    self.EV_setDriver('GV21', self.command_res2ISY(code), 25)
     

    def evChargePort (self, command):
        logging.info('evChargePort called')
        chargePort = int(float(command.get('value')))
        if chargePort == 1:
            code, res =  self.TEV.teslaEV_ChargePort(self.EVid, 'open')
        elif chargePort == 0:
            code, res = self.TEV.teslaEV_ChargePort(self.EVid, 'close')
        else:
            logging.debug(f'Wrong parameter passed to evChargePort : {chargePort}')
            code = 'error'
            res = f'Wrong parameter passed to evChargePort : {chargePort}'

        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV2', chargePort, 25)  
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)      
            self.EV_setDriver('GV2', None, 25)  


    def evChargeControl (self, command):
        logging.info('evChargeControl called')
        chargeCtrl = int(float(command.get('value')))

        if chargeCtrl == 1:
            code, res =  self.TEV.teslaEV_Charging(self.EVid, 'start')
            if code in ['ok']:
                self.EV_setDriver('GV6', 3, 25)
                self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            else:
                logging.info('Not able to send command - EV is not online')
                self.EV_setDriver('GV21', self.code2ISY(code), 25)      
                self.EV_setDriver('GV6', None, 25)                       
        elif chargeCtrl == 0:
            code, res =  self.TEV.teslaEV_Charging(self.EVid, 'stop')
            if code in ['ok']:
                self.EV_setDriver('GV6', 4, 25)
                self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            else:
                logging.info('Not able to send command - EV is not online')
                self.EV_setDriver('GV21', self.code2ISY(code), 25)      
                self.EV_setDriver('GV6', None, 25)              
        else:
            logging.debug(f'Wrong parameter passed to evChargeControl : {chargeCtrl}')
            self.EV_setDriver('GV6', None, 25)



    def evSetBatteryChargeLimit (self, command):
        logging.info('evSetBatteryChargeLimit called')
        batLimitPercent = int(float(command.get('value')))
        code, res =  self.TEV.teslaEV_SetChargeLimit(self.EVid, batLimitPercent)
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV9', batLimitPercent, 51) 
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)      
            self.EV_setDriver('GV9', None, 25)              



    def evSetCurrentChargeLimit (self, command):
        logging.info('evSetCurrentChargeLimit called')
        
        ampLimit = int(float(command.get('value')))

        code, res = self.TEV.teslaEV_SetChargeLimitAmps(self.EVid, ampLimit)
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('CHARGEAMPS', ampLimit, 1)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)      
            self.EV_setDriver('CHARGEAMPS', None, 25)              


    id = 'evcharge'

    commands = { #'UPDATE': ISYupdate, 
                 'CHARGEPORT' : evChargePort,
                 'CHARGECTRL' : evChargeControl,
                 'BATPERCENT' : evSetBatteryChargeLimit,
                 'CHARGEAMPS' : evSetCurrentChargeLimit,

                }

    drivers = [
            #{'driver': 'ST', 'value': 0, 'uom': 2},
            {'driver': 'ST', 'value': 0, 'uom': 51},  #battery_level
            {'driver': 'GV1', 'value': 99, 'uom': 25},  #fast_charger_present
            {'driver': 'GV2', 'value': 99, 'uom': 25},  #charge_port_door_open
            {'driver': 'GV3', 'value': 99, 'uom': 25},  #charge_port_latch

            #{'driver': 'BATLVL', 'value': 0, 'uom': 51},  #battery_level
            {'driver': 'GV4', 'value': 0, 'uom': 83}, # Estimated range - Miles
            {'driver': 'GV5', 'value': 0, 'uom': 1},  #charge_current_request_max
            {'driver': 'GV6', 'value': 99, 'uom': 25},  #charging_state
            {'driver': 'GV7', 'value': 99, 'uom': 25},  #charge_enable_request
            {'driver': 'GV8', 'value': 0, 'uom':30},  #charger_power
            {'driver': 'GV9', 'value': 0, 'uom': 51},  #bat charge_limit_soc
            {'driver': 'GV10', 'value': 0, 'uom': 72},  #charger_voltage
            {'driver': 'GV11', 'value': 0, 'uom': 1},  #charge_current_request
            {'driver': 'GV12', 'value': 0, 'uom': 1},  #charger_actual_current
            #{'driver': 'GV13', 'value': 0, 'uom': 1},  #charge_amps
            {'driver': 'GV14', 'value': 0, 'uom': 44},  #time_to_full_charge
            {'driver': 'GV15', 'value': 0, 'uom': 33},  #charge_energy_added           
            {'driver': 'GV16', 'value': 0, 'uom': 83},  #charge_miles_added_rated
            {'driver': 'GV19', 'value': 0, 'uom': 20},  #Last combined update Hours           
            #{'driver': 'GV20', 'value': 0, 'uom': 20},  #Last update Hours
            {'driver': 'GV21', 'value': 99, 'uom': 25}, #Last Command status

            ]
            


