#!/usr/bin/env python3

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)
import time
        
               
class teslaEV_ClimateNode(udi_interface.Node):
    from  udiLib import node_queue, command_res2ISY, wait_for_node_done, tempUnitAdjust, latch2ISY, chargeState2ISY, setDriverTemp, cond2ISY,  mask2key, heartbeat, code2ISY, state2ISY, bool2ISY, online2ISY, EV_setDriver, openClose2ISY

    def __init__(self, polyglot, primary, address, name, evid,  TEV):
        super(teslaEV_ClimateNode, self).__init__(polyglot, primary, address, name)
        logging.info('_init_ Tesla ClimateNode Status Node')
        self.poly = polyglot
        self.ISYforced = False
        self.TEV = TEV
        self.EVid = evid
        self.primary = primary
        self.address = address
        self.name = name
        self.nodeReady = False
        #self.node = self.poly.getNode(address)
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)

        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        logging.info('_init_ Tesla ClimateNode Status Node COMPLETE')

    def start(self):                
        logging.debug('Start TeslaEV Climate Node')  
        #self.EV_setDriver('ST', 1)
        self.nodeReady = True
        #self.updateISYdrivers()
        #self.update_time()
        #self.tempUnit = self.TEV.teslaEV_GetTempUnit()

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def climateNodeReady (self):
        return(self.nodeReady )
    

    def poll(self):
        pass
        #logging.debug(f'Climate node {self.EVid}')
        #try:
        #    if self.TEV.carState != 'Offline':
        #        self.updateISYdrivers()
        #    else:
        #        logging.info('Car appears off-line/sleeping - not updating data')

        #except Exception as e:
        #    logging.error(f'Climate Poll exception : {e}')

    #def forceUpdateISYdrivers(self):
    #   logging.debug(f'forceUpdateISYdrivers: {self.EVid}')
    #    time.sleep(1)
    #    self.TEV.teslaEV_UpdateCloudInfo(self.EVid)
    #    self.updateISYdrivers()

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
                logging.info(f'Climate setDriverTemp {self.EVid}')
                if self.TEV.teslaEV_GetCarState(self.EVid) in ['online']:
                    self.setDriverTemp('ST', self.TEV.teslaEV_GetCabinTemp(self.EVid))
                    self.setDriverTemp('GV2', self.TEV.teslaEV_GetOutdoorTemp(self.EVid))
                    self.setDriverTemp('GV3', self.TEV.teslaEV_GetLeftTemp(self.EVid))
                    self.setDriverTemp('GV4', self.TEV.teslaEV_GetRightTemp(self.EVid))
                    seatHeat = self.TEV.teslaEV_GetSeatHeating(self.EVid)
                    if 'seat_heater_left' in seatHeat:
                        seatHeat['FrontLeft'] = seatHeat['seat_heater_left']
                    elif 'FrontLeft' not in seatHeat:
                        seatHeat['FrontLeft'] = None
                    if 'seat_heater_left' in seatHeat:
                        seatHeat['FrontRight'] = seatHeat['seat_heater_rigth']
                    elif 'FrontRight' not in seatHeat:
                        seatHeat['FrontRight'] = None
                    if 'seat_heater_left' in seatHeat:
                        seatHeat['RearLeft'] = seatHeat['seat_heater_rear_left']
                    elif 'RearLeft' not in seatHeat:
                        seatHeat['RearLeft'] = None
                    if 'seat_heater_rear_center' in seatHeat:
                        seatHeat['RearMiddle'] = seatHeat['seat_heater_rear_center']
                    elif 'RearMiddle' not in seatHeat:
                        seatHeat['RearMiddle'] = None
                    if 'seat_heater_rear_right' in seatHeat:
                        seatHeat['RearRight'] = seatHeat['seat_heater_rigth']
                    elif 'RearRight' not in seatHeat:             
                        seatHeat['RearRight'] = None
                    if 'seat_heater_third_row_left' in seatHeat:
                        seatHeat['ThirdLeft'] = seatHeat['seat_heater_third_row_left']
                    elif 'ThirdLeft' not in seatHeat:             
                        seatHeat['ThirdLeft'] = None
                    if 'seat_heater_third_row_right' in seatHeat:
                        seatHeat['ThirdRight'] = seatHeat['seat_heater_third_row_right']
                    elif 'ThirdRight' not in seatHeat:             
                        seatHeat['ThirdRight'] = None                        

                    self.EV_setDriver('GV5', self.cond2ISY(seatHeat['FrontLeft']), 25)
                    self.EV_setDriver('GV6', self.cond2ISY(seatHeat['FrontRight']), 25)
                    self.EV_setDriver('GV7', self.cond2ISY(seatHeat['RearLeft']), 25)
                    self.EV_setDriver('GV8', self.cond2ISY(seatHeat['RearMiddle']), 25)
                    self.EV_setDriver('GV9', self.cond2ISY(seatHeat['RearRight']),25)
                    self.EV_setDriver('GV10', self.bool2ISY(self.TEV.teslaEV_AutoConditioningRunning(self.EVid)), 25)
                    self.EV_setDriver('GV15', self.cond2ISY(seatHeat['ThirdLeft']),25)
                    self.EV_setDriver('GV16', self.cond2ISY(seatHeat['ThirdRight']),25)

                    self.EV_setDriver('GV11', self.bool2ISY(self.TEV.teslaEV_PreConditioningEnabled(self.EVid)), 25)
                    
                    self.setDriverTemp('GV12', self.TEV.teslaEV_MaxCabinTempCtrl(self.EVid))

                    self.setDriverTemp('GV13', self.TEV.teslaEV_MinCabinTempCtrl(self.EVid))
                    
                    self.EV_setDriver('GV14', self.bool2ISY(self.TEV.teslaEV_SteeringWheelHeatOn(self.EVid)), 25) #need to be implemented        
            else:
                logging.info(f'No new data for climateNode for ({self.EVid}) -  code: {code}' )
        except Exception as e:
            logging.error(f'updateISYdrivers climate node  failed: {e}')


    #def ISYupdate (self, command):
    #    logging.info('ISY-update called')
        #super(teslaEV_ClimateNode, self).ISYupdate()
        #code, state = self.TEV.teslaEV_update_connection_status(self.EVid)
        #code, res = self.TEV.teslaEV_UpdateCloudInfo(self.EVid)
        #super(teslaEV_ClimateNode, self).update_all_drivers(code)
        #super(teslaEV_ClimateNode, self).display_update()
        #self.EV_setDriver('GV21', self.command_res2ISY(code), 25)

    def evWindows (self, command):
        logging.info('evWindows- called')

        windowCtrl = int(float(command.get('value')))

        if windowCtrl == 1:
            code, res = self.TEV.teslaEV_Windows(self.EVid, 'vent')

        elif windowCtrl == 0:
            code, res = self.TEV.teslaEV_Windows(self.EVid, 'close')
        else:
            logging.error(f'Wrong command for evWndows: {windowCtrl}')
            code = 'error'
            res = f'Wrong command for evWndows: {windowCtrl}'
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)    
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)


    def evSunroof (self, command):
        logging.info('evSunroof called')

        sunroofCtrl = int(float(command.get('value')))
 
        if sunroofCtrl == 1:
            code, res = self.TEV.teslaEV_SunRoof(self.EVid, 'vent')
        elif sunroofCtrl == 0:
            code, res = self.TEV.teslaEV_SunRoof(self.EVid, 'close')            
        else:
            logging.error(f'Wrong command for evSunroof: {sunroofCtrl}')

            code = 'error'
            res = f'Wrong command for evSunroof: {sunroofCtrl}'
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)    
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)      


    def evAutoCondition (self, command):
        logging.info('evAutoCondition called')  

        autoCond = int(float(command.get('value')))       
        if autoCond == 1:
            code, res = self.TEV.teslaEV_AutoCondition(self.EVid, 'start')
        elif autoCond == 0:
            code, res = self.TEV.teslaEV_AutoCondition(self.EVid, 'stop')
        else:
            logging.error(f'Wrong command for evAutoCondition: {autoCond}')
            code = 'error'
            res = f'Wrong command for evAutoCondition: {autoCond}'
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV10',autoCond, 25 )
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV10',None, 25 )
        
    def evDefrostMax (self, command):
        logging.info('evDefrostMax called')
        
        defrost = int(float(command.get('value')))
    
        if defrost == 1:
            if self.TEV.teslaEV_DefrostMax(self.EVid, 'on'):
                self.EV_setDriver('GV11', 2, 25)
        elif defrost == 0:
            if self.TEV.teslaEV_DefrostMax(self.EVid, 'off'):
                self.EV_setDriver('GV11', self.teslaEV_PreConditioningEnabled(self.EVid), 25)
        else:
            logging.error(f'Wrong command for evDefrostMax: {defrost}')
            code = 'error'
            res = f'Wrong command for evDefrostMax: {defrost}'
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV11', None, 25)


    def evSetCabinTemp (self, command):
        logging.info('evSetCabinTemp called') 
        driverTemp = None
        passengerTemp = None
        query = command.get("query")
        if 'driver.uom4' in query:
            driverTemp = int(query.get('driver.uom4'))
        elif 'driver.uom17' in query:
            driverTemp = int((int(query.get('driver.uom17'))-32)*5/9)
        if 'passenger.uom4' in query:
            passengerTemp = int(query.get('passenger.uom4'))  
        elif 'passenger.uom17' in query:
            passengerTemp = int((int(query.get('passenger.uom17'))-32)*5/9)
        code, res = self.TEV.teslaEV_SetCabinTemps(self.EVid, driverTemp, passengerTemp)
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.setDriverTemp( 'GV3', driverTemp )
            self.setDriverTemp( 'GV4', passengerTemp)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV3', None, 25)
            self.EV_setDriver('GV4', None, 25)


    def evSetSeatHeat (self, command):
        logging.info('evSetSeat1Heat called')
  
        driverTemp = None
        passengerTemp = None
        query = command.get("query")
        seat_select = None
        seatTemp = None
        if 'seat.uom25' in query:
            seat_select = int(query.get('seat.uom25'))
        if 'heatlvl.uom25' in query:
            seatTemp = int(query.get('heatlvl.uom25'))  
        code, res = self.TEV.teslaEV_SetSeatHeating(self.EVid, seat_select, seatTemp)

        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            if seat_select in [0,1,2,4,5]:
                if seat_select in [1,2,3]:
                    GVstr = 'GV'+str(seat_select+5)
                else:
                    GVstr ='GV'+str(seat_select+4)
                self.setDriverTemp(GVstr, seatTemp )
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            #self.EV_setDriver('GV3', None, 25)

    def evSetSeat0Heat (self, command):
        logging.info('evSetSeat0Heat called')

        seatTemp = int(command.get('value'))  
        code, res = self.TEV.teslaEV_SetSeatHeating(self.EVid, 0, seatTemp)
                
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV5', seatTemp, 25)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV5', None, 25)


    def evSetSeat1Heat (self, command):
        logging.info('evSetSeat1Heat called')
  
        seatTemp = int(command.get('value'))  
        code, res = self.TEV.teslaEV_SetSeatHeating(self.EVid, 1, seatTemp)
                
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV6', seatTemp, 25)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV6', None, 25)

    def evSetSeat2Heat (self, command):
        logging.info('evSetSea2tHeat called')

        seatTemp = int(command.get('value'))  
        code, res = self.TEV.teslaEV_SetSeatHeating(self.EVid, 2, seatTemp)
                
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV7', seatTemp, 25)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV7', None, 25)

    def evSetSeat4Heat (self, command):
        logging.info('evSetSeat4Heat called')

        seatTemp = int(command.get('value'))  
        code, res = self.TEV.teslaEV_SetSeatHeating(self.EVid, 4, seatTemp)
                
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV8', seatTemp, 25)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV8', None, 25)

    def evSetSeat5Heat (self, command):
        logging.info('evSetSeat5Heat called') 
        seatTemp = int(command.get('value'))  
        code, res = self.TEV.teslaEV_SetSeatHeating(self.EVid, 5, seatTemp)
                
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res), 25)
            self.EV_setDriver('GV9', seatTemp, 25)
        else:
            logging.info('Not able to send command - EV is not online')
            self.EV_setDriver('GV21', self.code2ISY(code), 25)
            self.EV_setDriver('GV9', None, 25)            

    def evSteeringWheelHeat (self, command):
        logging.info('evSteeringWheelHeat called')
        wheel = int(float(command.get('value')))

        if 0<= wheel <= 3:     
            code, res = self.TEV.teslaEV_SteeringWheelHeat(self.EVid, wheel) 
        else:
            logging.error(f'Wrong command for evDefrostMax: {wheel}') 
            code = 'error'
            res = f'Wrong command for evDefrostMax: {wheel}'
        if code in ['ok']:
            self.EV_setDriver('GV21', self.command_res2ISY(res),25)
        else:
            self.EV_setDriver('GV21', self.code2ISY(code),25)


    id = 'evclimate'
    commands = { #'UPDATE' : ISYupdate, 
                 'WINDOWS' : evWindows,
                 'SUNROOF' : evSunroof,
                 'AUTOCON' : evAutoCondition,
                 'CABINTEMP' : evSetCabinTemp,
                 'DEFROST' : evDefrostMax,   
                 'SEAT'  :evSetSeatHeat,   
                 #'SEAT0' :evSetSeat0Heat,
                 #'SEAT1' :evSetSeat1Heat,
                 #'SEAT2' :evSetSeat2Heat,
                 #'SEAT4' :evSetSeat4Heat,
                 #'SEAT5' :evSetSeat5Heat,

                 'STEERINGW' : evSteeringWheelHeat,   

                }

    drivers = [
            #{'driver': 'ST', 'value': 0, 'uom': 2},
            {'driver': 'ST', 'value': 0, 'uom': 4},  #inside_temp
            #{'driver': 'GV1', 'value': 0, 'uom': 4},  #inside_temp
            {'driver': 'GV2', 'value': 0, 'uom': 4},  #outside_temp
            {'driver': 'GV3', 'value': 0, 'uom': 4},  #driver_temp_setting
            {'driver': 'GV4', 'value': 0, 'uom': 4},  #passenger_temp_setting
            {'driver': 'GV5', 'value': 0, 'uom': 25},  #seat_heater_left
            {'driver': 'GV6', 'value': 0, 'uom': 25},  #seat_heater_right
            {'driver': 'GV7', 'value': 0, 'uom': 25},  #seat_heater_rear_left
            {'driver': 'GV8', 'value': 0, 'uom': 25},  #seat_heater_rear_center
            {'driver': 'GV9', 'value': 0, 'uom': 25},  #seat_heater_rear_right
            {'driver': 'GV15', 'value': 0, 'uom': 25},  #seat_heater_third_left
            {'driver': 'GV16', 'value': 0, 'uom': 25},  #seat_heater_third_right


            {'driver': 'GV11', 'value': 0, 'uom': 25}, #is_preconditioning
            {'driver': 'GV12', 'value': 0, 'uom': 4}, #max_avail_temp
            {'driver': 'GV13', 'value': 0, 'uom': 4}, #min_avail_temp   
            {'driver': 'GV14', 'value': 99, 'uom': 25}, #Steering Wheel Heat
            {'driver': 'GV19', 'value': 0, 'uom': 20},  #Last combined update Hours           
            #{'driver': 'GV20', 'value': 0, 'uom': 20},  #Last update Hours          
            {'driver': 'GV21', 'value': 99, 'uom': 25}, #Last Command status
            ]


