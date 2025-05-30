
#!/usr/bin/env python3

### Your external service class
'''
Your external service class can be named anything you want, and the recommended location would be the lib folder.
It would look like this:

External service sample code
Copyright (C) 2023 Universal Devices

MIT License
'''
import json
import requests
import time
from datetime import timedelta, datetime
from TeslaOauth import teslaAccess
from TeslaPWapi import teslaPWAccess
#from udi_interface import logging, Custom
#from oauth import OAuth
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    ISY = udi_interface.ISY
except ImportError:
    import logging
    logging.basicConfig(level=30)


#from udi_interface import LOGGER, Custom, OAuth, ISY
#logging = udi_interface.LOGGER
#Custom = udi_interface.Custom
#ISY = udi_interface.ISY



# Implements the API calls to your external service
# It inherits the OAuth class
class teslaEVAccess(object):
    yourApiEndpoint = 'https://fleet-api.prd.na.vn.cloud.tesla.com'

    def __init__(self, polyglot, tesla_api):
        #super().__init__(polyglot, t_api)
        logging.info('OAuth initializing')
        self.poly = polyglot
        self.tesla_api = tesla_api
        #self.customParameters = Custom(self.poly, 'customparams')
        #self.stream_cert = Custom(polyglot, 'customdata')
        #self.poly.subscribe(self.poly.CUSTOMDATA, self.customDataHandler) 

        self.EndpointNA= 'https://fleet-api.prd.na.vn.cloud.tesla.com'
        self.EndpointEU= 'https://fleet-api.prd.eu.vn.cloud.tesla.com'
        self.EndpointCN= 'https://fleet-api.prd.cn.vn.cloud.tesla.cn'
        self.api  = '/api/1'
        self.time_start = int(time.time())
        self.update_time = {}
        #self.time_climate = self.time_start
        #self.time_charge = self.time_start
        #self.time_status = self.time_start
        #self.state = secrets.token_hex(16)
        self.region = 'NA'
        self.handleCustomParamsDone = False
        #self.customerDataHandlerDone = False
        self.customNsHandlerDone = False
        self.customOauthHandlerDone = False
        self.CELCIUS = 0
        self.KM = 0
        #self.gui_temp_unit = None
        #self.gui_dist_unit = None
        self.temp_unit = 0
        self.dist_unit = 1
        self.carInfo = {}
        self.carStateList = ['online', 'offline', 'aleep', 'unknown', 'error']
        self.carState = 'Unknown'
       
        self.locationEn = False
        self.canActuateTrunks = False
        self.sunroofInstalled = False
        self.rearSeatHeat = False
        self.steeringWheeelHeat = False
        self.steeringWheelHeatDetected = False
        self.ev_list = []
        self.poly = polyglot
        temp = time.time() - 1 # Assume calls can be made
        self.next_wake_call = temp
        self.next_command_call = temp
        self.next_chaging_call = temp
        self.next_device_data_call = temp
        self.stream_data = {}
        self.wall_connector = 0
        self.teslaPW_cloud = None
        time.sleep(1)

    

    def extract_needed_delay(self, input_string):
        temp =  [int(word) for word in input_string.split() if word.isdigit()]
        if temp != []:
            return(temp[0])
        else:
            return(0)
        
    def teslaEV_get_vehicle_list(self) -> list:
        return(self.ev_list)
    
   
   
    def teslaEV_stream_process_data (self, data):
        try:
            temp = json.loads(data)
            #d_type = type(data)
            #logging.debug(f'teslaEV_stream_process_data  {temp}')
            #t_type = type(temp)
            #logging.debug(f'data types data {type(data)} - temp {type(temp)}')
            EVid = temp['stream']['deviceId']
            if EVid not in self.stream_data:
                self.stream_data[EVid] = {}
            if 'data' in temp['payload']:
                for item in temp['payload']['data']:
                    #logging.debug(f'item : {item}')
                    if 'key' in item:
                        self.stream_data[EVid][item['key']] = item['value']
                        logging.debug('Data: {}: {}'.format(item['key'], item['value']))
                        if item['key'] in ['SettingDistanceUnit']:
                            if item['value']['distanceUnitValue'] == 'DistanceUnitMiles':
                                self.teslaEV_SetDistUnit(1)
                            else:
                                self.teslaEV_SetDistUnit(0)
                        if item['key'] in ['SettingTemperatureUnit']:
                            if item['value']['temperatureUnitValue'] == 'TemperatureUnitFahrenheit':
                                self.teslaEV_SetTempUnit(1)
                            else:
                                self.teslaEV_SetTempUnit(0)

                self.stream_data[EVid]['created_at'] = temp['stream']['createdAt']
            #logging.debug(f'stream_data {self.stream_data}')

        except Exception as e:
            logging.error(f'Exception processing data {data} {self.stream_data} {e}')
   
   
   
    def _stream_data_found(self, EVid, key):
        try:
            #logging.debug(f'_stream_data_found {key} {key in self.stream_data[EVid]}')
            return(key in self.stream_data[EVid])
        except ValueError:
            return(False)
        

    def _stream_last_data(self, EVid):
        try:
            return(self.stream_data[EVid]['created_at'])
        except ValueError:
            return(None)

    def _stream_return_data(self, EVid, dataKey):
        try:
            #logging.debug(f'_stream_return_data {dataKey} {self.stream_data[EVid]} ')
 
            ret_val = None
            if dataKey in self.stream_data[EVid]:
                for key in self.stream_data[EVid][dataKey]:
                    #logging.debug(f'data {key} , val {self.stream_data[EVid][dataKey][key]}')
                    #keys = self.stream_data[EVid][dataKey].keys()
                    #logging.debug(f'{keys} {type(keys)}')
                    #key = keys
                    #logging.debug(f'{key} {type(key)}')
                    #val =  self.stream_data[EVid][dataKey][key] 
                    val =  self.stream_data[EVid][dataKey][key] 
                    #logging.debug(f'Items {key} {val}')
                    if  key in ['intValue',]:
                        logging.debug('intValue {}'.format(int(val)))
                        ret_val = int(val)
                    elif  key in ['doubleValue', ]:
                        logging.debug('doubleValue {}'.format(round(val, 2)))
                        ret_val = round(val, 2)
                    elif key in ['stringValue', ]:
                        logging.debug('stringValue {}'.format(str(val)))
                        ret_val = str(val)
                    elif key in ['booleanValue', ]:
                        logging.debug('booleanValue {}'.format(bool(val)))
                        ret_val = bool(val)
                    elif key in ['invalid', ]:
                        logging.debug('invalid {}'.format(bool(val)))
                        if val:
                            ret_val = 'invalid'
                        else:
                            ret_val = None
                    else:
                        logging.debug('ELSE {}'.format(self.stream_data[EVid][dataKey]))
                        ret_val = val
                return(ret_val)
            else:
                return(None)

        except Exception as E:
            logging.debug(f'Exception _stream_return_data: {dataKey}  {key} {val} {E}')
            return(None)   



    def teslaEV_stream_get_id(self, data):
        logging.debug(f'teslaEV_stream_get_id :')
        try:
            temp = json.loads(data)
            #d_type = type(data)
            #t_type = type(temp)
            #logging.debug(f'data types data {type(data)} - temp {type(temp)}')
            return(temp['stream']['deviceId'])
        except ValueError as e:
            logging.error(f'Exception teslaEV_stream_get_id {e} ')
            return (None)


    def testWebhook(self, body):
        try:
            config = self.poly.getConfig()

            uuid = config['uuid']
            slot = config['profileNum']
            completeUrl = f"https://my.isy.io/api/eisy/pg3/webhook/noresponse/{ uuid }/{ slot }"
            headers = {  }
            logging.debug(f'complete URL {completeUrl}')
            response = requests.post(completeUrl, headers=headers, json=body, timeout=5)
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            httpStatus = error.response.status_code

            # Not online?
            if httpStatus == 503:
                logging.error(f"MQTT connection not online.\nOn my.isy.io, please check Select Tool | PG3 | Remote connection. It has to be active.\nIf you don't see the option, your device does not support it. Make sure you are using an eisy at 5.6.0 or more recent, or a Polisy using PG3x.")
            # No access to uuid?
            elif httpStatus == 423:
                logging.error(f"Make sure that uuid { config['uuid'] } is in your portal account, has a license and is authorized.")
            else:
                logging.error(f"Call event url failed GET { completeUrl } failed with HTTP { httpStatus }: { error }")

            raise Exception('Error sending event to Portal webhook')

    ########################################   
   
   
    def teslaEV_get_vehicles(self):
        EVs = {}
        logging.debug(f'teslaEV_get_vehicles ')
        try:
            self.ev_list =[]
            code, temp = self.tesla_api._callApi('GET','/vehicles' )
            logging.debug(f'vehicles: {temp}')
            if code in ['ok']:
                for indx, site in enumerate(temp['response']):
                    if 'vin' in site:
                        EVs[str(site['vin'])] = site
                        # self.ev_list.append(site['id']) 
                        self.ev_list.append(site['vin']) # vin needed to send commands
                        self.carInfo[site['vin']] = site
                        # initialize start time 
                        time_now = int(time.time())
                        if 'vehicle_state' not in self.carInfo[site['vin']]:
                            self.carInfo[site['vin']]['state'] = 'unknown'
                            self.carInfo[site['vin']]['vehicle_state'] = {}
                            self.carInfo[site['vin']]['vehicle_state']['timestamp'] = time_now
                            self.carInfo[site['vin']]['climate_state'] = {}
                            self.carInfo[site['vin']]['climate_state']['timestamp'] = time_now
                            self.carInfo[site['vin']]['charge_state'] = {}
                            self.carInfo[site['vin']]['charge_state']['timestamp'] = time_now
                        if site['vin'] not in self.update_time:
                            self.update_time[site['vin']] = {}
                            self.update_time[site['vin']]['climate'] = time_now
                            self.update_time[site['vin']]['charge'] = time_now
                            self.update_time[site['vin']]['status'] = time_now
                        logging.debug('timinng info : {} {}'.format(self.carInfo[site['vin']], self.update_time[site['vin']] ))
            return(code, EVs)
        except Exception as e:
            logging.error(f'teslaEV_get_vehicles Exception : {e}')



        

    def tesla_get_energy_products(self):
        #power_walls= {}
        logging.debug('tesla_get_energy_products ')
        try:
            site_id = ''
            code, temp = self.tesla_api._callApi('GET','/products' )
            logging.debug('products: {} '.format(temp))
            if code == 'ok':
                for indx, site  in enumerate(temp['response']):
                    #site = temp['response'][indx]
                    logging.debug(f'site: {site}')
                    if 'energy_site_id' in site:
                        if site['components']['battery']:
                            if 'wall_connectors' in site['components']:
                                self.wall_connector = len(site['components']['wall_connectors'])

                        site_id = str(site['energy_site_id'])
            logging.debug(f'Nbr wall coinnectors: {self.wall_connector}')
            self.teslaPW_cloud = teslaPWAccess(self.poly, '') # scope can be empty as already connected
            return(site_id, self.wall_connector)
        except Exception as e:
            logging.error('tesla_get_energy_products Exception : {}'.format(e))
            return(site_id, self.wall_connector)
   
    def _teslaEV_wake_ev(self, EVid):
        logging.debug(f'_teslaEV_wake_ev - {EVid}')
        trys = 1
        timeNow = time.time()
        try:
            code, state = self.teslaEV_update_connection_status(EVid)
            if code == 'ok':
                if timeNow >= self.next_wake_call:
                    if state in ['asleep','offline']:
                        code, res  = self.tesla_api._callApi('POST','/vehicles/'+str(EVid) +'/wake_up')
                        logging.debug(f'wakeup: {code} - {res}')
                        if code in  ['ok']:
                            time.sleep(5)
                            code, state = self.teslaEV_update_connection_status(EVid)
                            logging.debug(f'wake_ev while loop {code} - {state}')
                            while code in ['ok'] and state not in ['online'] and trys < 5:
                                trys += 1
                                time.sleep(15)
                                code, state = self.teslaEV_update_connection_status(EVid)
                                logging.debug(f'wake_ev while loop {trys} {code} {state}')
                        if code in ['overload']:
                            delay = self.extract_needed_delay(res)
                            self.next_wake_call = timeNow + int(delay)
                    return(code, state)
                else:          
                    logging.warning(f'Too many calls to wake API - need to wait {delay} secods')
                    return(code, state)
        except Exception as e:
            logging.error(f'_teslaEV_wake_ev Exception : {e}')


    def _teslaEV_get_ev_data(self, EVid):
        logging.debug(f'get_ev_data - state {EVid}')
        if self.locationEn:
            payload = {'endpoints':'charge_state;climate_state;drive_state;location_data;vehicle_config;vehicle_state'}
        else:
            payload = {'endpoints':'charge_state;climate_state;drive_state;vehicle_config;vehicle_state'}
        code, res = self.tesla_api._callApi('GET','/vehicles/'+str(EVid) +'/vehicle_data', payload  )
        logging.debug(f'vehicel data: {code} {res}')
        return(code, res)

    def _teslaEV_send_ev_command(self, EVid , command, params=None):
        logging.debug(f'send_ev_command - command  {command} - params: {params} - {EVid}')
        payload = params
        code, res = self.tesla_api._callApi('POST','/vehicles/'+str(EVid) +'/command'+str(command),  payload )

        if code in ['ok'] and not res['response']['result']:
            # something went wrong - try again
            logging.debug('Something went wrong - trying again {}'.format(res['response']))
            time.sleep(5)
            code, res = self.tesla_api._callApi('POST','/vehicles/'+str(EVid) +'/command'+str(command),  payload ) 
            logging.debug(f'_teslaEV_send_ev_command {code} - {res}')
                    
        if code in ['overload']:
            return(code, self.get_delay(res))
        else:
           return(code, res) 

    def get_delay(self, string):
        numbers = [int(word) for word in string.split() if word.isdigit()]
        if numbers != []:
            return(numbers[0]) 

    def teslaEV_UpdateCloudInfo(self, EVid):
        logging.debug(f'teslaEV_UpdateCloudInfo: {EVid}')
        code = 'unknown'
        res = None
        try:
            code, state  = self._teslaEV_wake_ev(EVid)                
            if code == 'ok':
                logging.debug(f'Wake_up result : {state}')
                if state in ['online']:
                    code, res = self._teslaEV_get_ev_data(EVid)
                    if code == 'ok':
                        self.carInfo[EVid] = self.process_EV_data(res)
                        #self.extract_gui_info(EVid)
                        return(self.teslaEV_GetCarState(EVid))
                    else:
                        return(code, state)            
            elif code == 'overload':
                delay = self.next_wake_call - time.time()
                return(code, state)
            else:
                return(code, state)
            

        except Exception as e:
            logging.debug(f'Exception teslaEV_UpdateCloudInfo: {e}')
            return('error', e)

    def teslaEV_UpdateCloudInfoAwake(self, EVid, online_known = False):
            logging.debug(f'teslaEV_UpdateCloudInfoAwake: {EVid}')
            try:
                code, state = self.teslaEV_update_connection_status(EVid)
                if code == 'ok' and state in ['online']:
                    code, res = self._teslaEV_get_ev_data(EVid)
                    if code == 'ok':
                        self.carInfo[EVid] = self.process_EV_data(res)
                        return(self.teslaEV_GetCarState(EVid))
                    else:
                        return(code, state)
                elif code == 'overload':
                    delay = self.next_wake_call - time.time()
                    return(code, delay)
                else:
                    return(code, state)
            except Exception as e:
                logging.debug(f'Exception teslaEV_UpdateCloudInfo: {e}')
                return('error', 'error')
   
    '''
    def extract_gui_info(self, EVid):
        try:
            if 'gui_settings' in self.carInfo[EVid]:
                if self.carInfo[EVid]['gui_settings']['gui_temperature_units'] in 'F':
                    self.gui_temp_unit  = 1
                else:
                    self.gui_temp_unit  = 0
   
                if self.carInfo[EVid]['gui_settings']['gui_distance_units'] in ['mi/hr']:
                    self.gui_dist_unit = '1'
                else:
                    self.gui_dist_unit = '0'
        except Exception as e:
            logging.error(f'No gui unit found- {e}')
            self.gui_tUnit =  self.temp_unit
            self.gui_dist_unit = self.dist_unit
    '''

    def teslaEV_get_gui_info(self, EVid, unit):
        try:
            if unit == 'temp':
                if 'F' in [self.carInfo[EVid]['gui_settings']['gui_temperature_units']]:
                    return 1
                else:
                    return 0
            elif unit == 'dist':
                if ['mi/hr'] in [self.carInfo[EVid]['gui_settings']['gui_distance_units']]:
                    return 1
                else:
                    return 0
        except Exception as e:
            logging.error(f'No gui unit found- {e}')
            if unit == 'temp':
                return(1) # F
            elif unit == 'dist':
                return(1) # Miles
            else:
                return(None)

    def process_EV_data(self, carData):
        logging.debug(f'process_EV_data')
        temp = {}
        if 'response' in carData:
            if 'version' in carData['response']:
                if carData['response']['version'] == 9: # latest release
                    temp = carData['response']['data']
            else:
                temp = carData['response']
            
        else:
            temp = 'Error'
        logging.debug(f'process_EV_data: {temp}')
        return(temp)
            



    def teslaEV_GetCarState(self, EVid):
        try:
            logging.debug('teslaEV_GetCarState:')
            code, res = self.teslaEV_update_vehicle_status(EVid)
            return(code, self.carInfo[EVid]['state'])
        except Exception as e:
            logging.error(f'teslaEV_GetCarState Exception : {e}')
            return(None, None)


    def teslaEV_GetConnectionStatus(self, EVid):
        #logging.debug(f'teslaEV_GetConnectionStatus: for {EVid}')
        return(self.carInfo[EVid]['state'])

    def teslaEV_update_vehicle_status(self, EVid) -> dict:
        EVs = {}
        logging.debug(f'teslaEV_get_vehicle_info ')
        try:
            code, res = self.tesla_api._callApi('GET','/vehicles/'+str(EVid) )
            logging.debug(f'vehicle {EVid} info : {code} {res} ')
            if code in ['ok']:
                self.carInfo[res['response']['vin']] = res['response']
                return(code, res['response'])
            else:
                return(code, res)
        except Exception as e:
            logging.error(f'teslaEV_update_vehicle_status Exception : {e}')
            return(None, None)

    def teslaEV_update_connection_status(self, EVid):
        #logging.debug(f'teslaEV_GetConnectionStatus: for {EVid}')
        try:
            code, res = self.teslaEV_update_vehicle_status(EVid)
            logging.debug(f'teslaEV_update_connection_status {code} {res}')
            return(code, res['state'])
        except Exception as e:
            logging.error(f'teslaEV_update_connection_status - {e}')
            return('error', e)



    def teslaEV_GetName(self, EVid):

        try:
            logging.debug(f'teslaEV_GetName {EVid} - {self.carInfo[EVid]}')
            return(self.carInfo[EVid]['display_name'])

        except Exception as e:
            logging.debug(f'teslaEV_GetName - No EV name found - {e}')
            return(None)
        

    '''
    def teslaEV_GetInfo(self, EVid):
        if EVid in self.carInfo:

            logging.debug(f'teslaEV_GetInfo {EVid}: {self.carInfo[EVid]}')
            return(self.carInfo[EVid])
        else:
            return(None)
    '''

    def teslaEV_GetInfo(self, EVid):
       
        if EVid in self.stream_data:
            return(self.stream_data[EVid])       
        elif EVid in self.carInfo:
            logging.debug(f'teslaEV_GetInfo {EVid}: {self.carInfo[EVid]}')
            return(self.carInfo[EVid])
        else:
            return(None)
        
    def teslaEV_GetLocation(self, EVid):
        logging.debug(f'teslaEV_GetLocation {self.tesla_api.stream_synched}')
        try:
            #data_found = False
            temp = {}
            temp['longitude'] = None
            temp['latitude'] = None
            if self._stream_data_found(EVid, 'Location'):
                logging.debug('teslaEV_GetLocation stream: {} for {}'.format(EVid,self.stream_data[EVid]['Location'] ))
                if 'invalid' in  self.stream_data[EVid]['Location']:
                    if self.stream_data[EVid]['Location']['invalid']:
                        temp['longitude'] = 'invalid'
                        temp['latitude'] = 'invalid'
                else:
                    temp['longitude'] = self.stream_data[EVid]['Location']['locationValue']['longitude']
                    temp['latitude'] = self.stream_data[EVid]['Location']['locationValue']['latitude']
              
            return(temp)
        except Exception as e:
            logging.debug(f'teslaEV_GetLocation - location error {e}')
            return(temp)


    def teslaEV_SetDistUnit(self, dUnit):
        logging.debug(f'teslaEV_SetDistUnit: {dUnit}')
        self.dist_unit = dUnit

    def teslaEV_GetDistUnit(self):
        return(self.dist_unit)

    def teslaEV_SetTempUnit(self, tUnit):
        logging.debug(f'teslaEV_SetDistUnit: {tUnit}')
        self.temp_unit = tUnit

    def teslaEV_GetTempUnit(self):
        return(self.temp_unit)


    def teslaEV_SetRegion(self, tRegion):
        logging.debug(f'teslaEV_SetRegion: {tRegion}')
        self.region = tRegion

    


    
    '''
    def teslaEV_GetTimeSinceLastCarUpdate(self, EVid):
        try:
            logging.debug(f'teslaEV_GetTimeSinceLastCarUpdate')
            timeNow = int(time.time())
            lst = [self.teslaEV_GetTimeSinceLastClimateUpdate(EVid),self.teslaEV_GetTimeSinceLastChargeUpdate(EVid), self.teslaEV_GetTimeSinceLastStatusUpdate(EVid), timeNow-self.time_start]
            logging.debug(f'Time list {lst}')
            timeMinimum =  min(filter(lambda x: x is not None, lst)) if any(lst) else None
            #timeMinimum = min( self.teslaEV_GetTimeSinceLastClimateUpdate(EVid),self.teslaEV_GetTimeSinceLastChargeUpdate(EVid), self.teslaEV_GetTimeSinceLastStatusUpdate(EVid) )
            logging.debug(f'Time Now {timeNow} Last UPdate {timeMinimum}')
            return(float(timeMinimum))
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetTimeSinceLastCarUpdate - {e}')
            return(0)
    '''

####################
# powershare Data
####################

    def teslaEV_PowershareHoursLeft(self, EVid):
        return (self._stream_return_data(EVid,'PowershareHoursLeft' ))
    

    def teslaEV_PowershareInstantaneousPowerKW(self, EVid):
        return (self._stream_return_data(EVid,'PowershareInstantaneousPowerKW'))   

    def teslaEV_PowershareStatus(self, EVid):
        logging.debug(f'teslaEV_PowershareStatus for {EVid} {self.stream_data[EVid]}')
        #return(self._stream_return_data(EVid, 'ChargePortDoorOpen'))
        try:
            if self._stream_data_found(EVid, 'PowershareStatus'):
                if 'invalid' in  self.stream_data[EVid]['PowershareStatus']:
                    if self.stream_data[EVid]['PowershareStatus']['invalid']:
                        return('invalid')
                else:
                    return(self.stream_data[EVid]['PowershareStatus']['powershareStateValue'])
            else:
               return(None)
        #     return(self.carInfo[EVid]['charge_state']['charge_port_door_open']) 
        except Exception as e:
            logging.debug(f'Exception teslaEV_PowershareStatus - {e}')
            return(None)  

    def teslaEV_PowershareStopReason(self, EVid):
        logging.debug(f'PowershareStopReason for {EVid} {self.stream_data[EVid]}')
        #return(self._stream_return_data(EVid, 'ChargePortDoorOpen'))
        try:
            if self._stream_data_found(EVid, 'PowershareStopReason'):
                if 'invalid' in  self.stream_data[EVid]['PowershareStopReason']:
                    if self.stream_data[EVid]['PowershareStopReason']['invalid']:
                        return('invalid')
                else:
                    return(self.stream_data[EVid]['PowershareStopReason']['powershareStopReasonValue'])
            else:
               return(None)
        #     return(self.carInfo[EVid]['charge_state']['charge_port_door_open']) 
        except Exception as e:
            logging.debug(f'Exception teslaEV_PowershareStatus - {e}')
            return(None)  



    def teslaEV_PowershareType(self, EVid):
        logging.debug(f'PowershareType for {EVid} {self.stream_data[EVid]}')
        #return(self._stream_return_data(EVid, 'ChargePortDoorOpen'))
        try:
            if self._stream_data_found(EVid, 'PowershareType'):
                if 'invalid' in  self.stream_data[EVid]['PowershareType']:
                    if self.stream_data[EVid]['PowershareType']['invalid']:
                        return('invalid')
                else:
                    return(self.stream_data[EVid]['PowershareType']['powershareTypeValue'])
            else:
               return(None)
        #     return(self.carInfo[EVid]['charge_state']['charge_port_door_open']) 
        except Exception as e:
            logging.debug(f'Exception teslaEV_PowershareStatus - {e}')
            return(None)  




####################
# Charge Data
####################


    def teslaEV_GetChargeTimestamp(self, EVid):
        try:
            if self.stream_data[EVid]:
                return(self._stream_last_data(EVid))
            else:
                return(None)      
                #return(self.carInfo['charge_state']['timestamp'])
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetChargeTimestamp - {e}')
            return(None)


    '''
    def teslaEV_GetIdealBatteryRange(self, EVid):
        try:
            if 'ideal_battery_range' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['ideal_battery_range'],2))
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetIdealBatteryRange - {e}')
            return(None)
    '''


    def teslaEV_charge_current_request_max(self, EVid):
        return (self._stream_return_data(EVid,'ChargeCurrentRequestMax' ))

    def teslaEV_charge_current_request(self, EVid):
        return(self._stream_return_data(EVid,'ChargeCurrentRequest'))
    
            

    
    def teslaEV_charger_actual_current(self, EVid):
        return(self._stream_return_data(EVid,'DCChargingPower'))


    def teslaEV_charge_amps(self, EVid):
        return(self._stream_return_data(EVid,'ChargeAmps'))


        
    def teslaEV_time_to_full_charge(self, EVid):
        return(self._stream_return_data(EVid,'TimeToFullCharge'))


    def teslaEV_charge_energy_added(self, EVid):
        #try:
        return(self._stream_return_data(EVid,'DCChargingEnergyIn'))

    

    def teslaEV_charger_voltage(self, EVid):
        return(self._stream_return_data(EVid,'ChargerVoltage'))
      
        
    def teslaEV_GetTimeSinceLastChargeUpdate(self, EVid):
        try:
            timeNow = int(time.time())
            logging.debug('Time Now {} Last UPdate {} , {} - '.format(timeNow,self.update_time[EVid], self.carInfo[EVid] ))
            logging.debug('state : {}'.format(self.carInfo[EVid]['state']))
            if 'timestamp' in self.carInfo[EVid]['charge_state'] and self.carInfo[EVid]['state'] in ['online']:
                self.update_time[EVid]['charge'] = float(self.carInfo[EVid]['charge_state']['timestamp']/1000)
                return(int(timeNow - self.update_time[EVid]['charge']))
            else:
                return(timeNow-self.update_time[EVid]['charge'] )
        except Exception as e:
            logging.debug(f'Exception - not online teslaEV_GetTimeSinceLastChargeUpdate - {e}')
            return(timeNow-self.update_time[EVid]['charge'] )
        
    def teslaEV_FastChargerPresent(self, EVid):
        #logging.debug(f'teslaEV_FastchargerPresent for {EVid}')
        return(self._stream_return_data(EVid,'FastChargerPresent'))


  
    def teslaEV_ChargePortOpen(self, EVid):
        logging.debug(f'teslaEV_ChargePortOpen for {EVid} {self.stream_data[EVid]}')
        #return(self._stream_return_data(EVid, 'ChargePortDoorOpen'))
        try:
            if self._stream_data_found(EVid, 'ChargePortDoorOpen'):
                if 'invalid' in  self.stream_data[EVid]['ChargePortDoorOpen']:
                    if self.stream_data[EVid]['ChargePortDoorOpen']['invalid']:
                        return('invalid')
                else:
                    return(self.stream_data[EVid]['ChargePortDoorOpen']['booleanValue'])
            else:
               return(None)
        #     return(self.carInfo[EVid]['charge_state']['charge_port_door_open']) 
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargePortOpen - {e}')
            return(None)  

    def teslaEV_ChargePortLatched(self, EVid):
        logging.debug(f'teslaEV_ChargePortLatched for {EVid} {self.stream_data[EVid]}')
        #return(self._stream_return_data(EVid, 'ChargePortLatch'))
        try:
            res = None
            if self._stream_data_found(EVid, 'ChargePortLatch'):
                if 'invalid' in  self.stream_data[EVid]['ChargePortLatch']:
                    logging.debug('teslaEV_ChargePortLatched - invalid detected {}'.format(self.stream_data[EVid]['ChargePortLatch']))
                    logging.debug('teslaEV_ChargePortLatched - value {}'.format(self.stream_data[EVid]['ChargePortLatch']['invalid']))
                    if self.stream_data[EVid]['ChargePortLatch']['invalid']:
                       res = 'invalid'

                else:
                    res = self.stream_data[EVid]['ChargePortLatch']['chargePortLatchValue']
            logging.debug(f'teslaEV_ChargePortLatched - return {res}')
            return(res)
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargePortLatched - {e}')
            self.stream_data[EVid]['ChargePortLatch']['chargePortLatchValue'] = 'ChargePortLatchUnknown'
            return(None)  

    def teslaEV_GetBatteryRange(self, EVid):
        return(self._stream_return_data(EVid, 'EstBatteryRange'))
        #try:
        #    #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
        #    if self._stream_data_found(EVid, 'EstBatteryRange'):
        #        return(round(self.stream_data[EVid]['EstBatteryRange']['doubleValue'],0))
        #    else:
        #        return(None)
        #        #return(round(self.carInfo[EVid]['charge_state']['battery_range'],0)) 
        #except Exception as e:
        #    logging.debug(f'Exception teslaEV_GetBatteryRange - {e}')
        #    return(None)  
        
    def teslaEV_GetBatteryLevel(self, EVid):
        return(self._stream_return_data(EVid, 'Soc'))
            
        #try: #use SOC value for available sueful battery level 
        #    #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
        #    #if self._stream_data_found(EVid, 'BatteryLevel'):
        #    if self._stream_data_found(EVid, 'Soc'):    
        #        return(round(self.stream_data[EVid]['Soc']['doubleValue'],2))
        #    else:
        #        return(None)
        #        #return(round(self.carInfo[EVid]['charge_state']['battery_level'],1)) 
        #except Exception as e:
        #    logging.debug(f'Exception teslaEV_GetBatteryLevel - {e}')
        #    return(None)  
        
    def teslaEV_MaxChargeCurrent(self, EVid):
        #logging.debug(f'teslaEV_MaxChargeCurrent for {EVid}')
        return(self._stream_return_data(EVid, 'ChargeCurrentRequestMax'))
        #try:
        #    if self._stream_data_found(EVid, 'ChargeCurrentRequestMax'):
        #        return(self.stream_data[EVid]['ChargeCurrentRequestMax']['intValue'])
        #    else:
        #        return(None)
        #        #return( self.carInfo[EVid]['charge_state']['charge_current_request_max'])             
        #except Exception as e:
        #    logging.debug(f'Exception teslaEV_MaxChargeCurrent - {e}')
        #    return(None)       

    def teslaEV_ChargeState(self, EVid):
        #return(self._stream_return_data(EVid, 'DetailedChargeState'))
        logging.debug(f'teslaEV_GetChargingState for {EVid}')
        try:
            if self._stream_data_found(EVid, 'DetailedChargeState'):
                if 'invalid' in  self.stream_data[EVid]['DetailedChargeState']:
                    if self.stream_data[EVid]['DetailedChargeState']['invalid']:
                        return('invalid')
                else:
                    return(self.stream_data[EVid]['DetailedChargeState']['detailedChargeStateValue'])
            else:
                return(None)
        #        #return( self.carInfo[EVid]['charge_state']['charging_state'])  
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargeState - {e}')
            return(None)     
        
    def teslaEV_ChargingRequested(self, EVid):
        #logging.debug(f'teslaEV_ChargingRequested for {EVid}')
        return(self._stream_return_data(EVid, 'ChargeCurrentRequest'))
        #try:
        #    if self._stream_data_found(EVid, 'ChargeCurrentRequest'):
        #        return(self.stream_data[EVid]['ChargeCurrentRequest']['intValue'])
        #    else:
        #        return(None)
        #        #return(  self.carInfo[EVid]['charge_state']['charge_enable_request'])  
        #except Exception as e:
        #    logging.debug(f'Exception teslaEV_ChargingRequested - {e}')
        #    return(None)  
    
    def teslaEV_GetChargingPower(self, EVid):
        return(self._stream_return_data(EVid, 'DCChargingPower'))
        #try:
        #    
        #    #logging.debug(f'teslaEV_GetChargingPower for {EVid}')
        #    res = []
        #    if self._stream_data_found(EVid, 'DCChargingPower'):
        #        res.append( round(self.stream_data[EVid]['DCChargingPower']['doubleValue'],1))
        #    if self._stream_data_found(EVid, 'ACChargingPower'):
        #        res.append(round(self.stream_data[EVid]['ACChargingPower']['doubleValue'],1))
        #    res_l = [x for x in res if x is not None]
        #    max_pwr = max(res_l)
        #    if max_pwr:
        #        return(max_pwr)
        #    else:
        #        return(None)    
        #        #return(round(self.carInfo[EVid]['charge_state']['charger_power'],1)) 
        #
        #except Exception as e:
        #    logging.debug(f'Exception teslaEV_GetChargingPower - {e}')
        #    return(None)              

    def teslaEV_GetBatteryMaxCharge(self, EVid):
        return(self._stream_return_data(EVid, 'ChargeLimitSoc'))
        #try:
        #    #logging.debug(f'teslaEV_GetBatteryMaxCharge for {EVid}')
        #    if self._stream_data_found(EVid, 'ChargeLimitSoc'):
        #        return(self.stream_data[EVid]['ChargeLimitSoc']['intValue'])
        #    else:
        #        return(None)
        #        #return(round(self.carInfo[EVid]['charge_state']['charge_limit_soc'],0)) 

        #except Exception as e:
        #    logging.debug(f'Exception teslaEV_GetBatteryMaxCharge - {e}')
        #    return(None)              
           
    def teslaEV_ChargePort(self, EVid, ctrl):
        logging.debug(f'teslaEV_ChargePort {ctrl} for {EVid}')

        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:
                if ctrl == 'open':
                    code, res = self._teslaEV_send_ev_command(EVid,'/charge_port_door_open') 
                elif ctrl == 'close':
                    code, res = self._teslaEV_send_ev_command(EVid,'/charge_port_door_close') 
                else:
                    return('error', 'unknown command sent {ctrl}')
                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')

    
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargePort for vehicle id {EVid}: {e}')
            return('error', e)

    def teslaEV_Charging(self, EVid, ctrl):
        logging.debug(f'teslaEV_Charging {ctrl} for {EVid}')
 

        try:
    
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:
                if ctrl == 'start':  
                    code, res = self._teslaEV_send_ev_command(EVid, '/charge_start' )
                elif ctrl == 'stop':
                    code, res = self._teslaEV_send_ev_command(EVid, '/charge_stop' )
                else:
                    logging.debug(f'Unknown teslaEV_Charging command passed for vehicle id (start, stop) {EVid}: {ctrl}')
                    return('error', f'unknown command sent {ctrl}')
                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')

        except Exception as e:
            logging.debug(f'Exception teslaEV_Charging for vehicle id {EVid}: {e}')
            return('error', e)



    def teslaEV_SetChargeLimit (self, EVid, limit):
        logging.debug(f'teslaEV_SetChargeLimit {limit} for {EVid}')
        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    
                if int(limit) > 100 or int(limit) < 0:
                    logging.error(f'Invalid seat heat level passed (0-100%) : {limit}')
                    return('error', 'Illegal range passed')

  
                payload = { 'percent':int(limit)}    
                code, res = self._teslaEV_send_ev_command(EVid, '/set_charge_limit',  payload ) 
                if code in  ['ok']:

                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')
        except Exception as e:
            logging.debug(f'Exception teslaEV_SetChargeLimit for vehicle id {EVid}: {e}')      
            return('error', e)



    def teslaEV_SetChargeLimitAmps (self, EVid, limit):
        logging.debug(f'teslaEV_SetChargeLimitAmps {limit} for {EVid} -')
        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    
       
                if limit > 300 or limit < 0:
                    logging.error(f'Invalid seat heat level passed (0-300A) : {limit}')
                    return('error', 'Illegal range passed')
                payload = { 'charging_amps': int(limit)}    
                code, res = self._teslaEV_send_ev_command(EVid, '/set_charging_amps', payload ) 
                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')

        except Exception as e:
            logging.debug(f'Exception teslaEV_SetChargeLimitAmps for vehicle id {EVid}: {e}')

            
            return('error', e)




####################
# Climate Data
####################


    def teslaEV_GetClimateTimestamp(self, EVid):
        try:
            if self.stream_data[EVid]:
                return(self._stream_last_data(EVid))
            else:      
                return(self.carInfo[EVid]['climate_state']['timestamp'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetClimateTimestamp - {e}')
            return(None)

    '''
    def teslaEV_GetTimeSinceLastClimateUpdate(self, EVid):
        try:
            timeNow = int(time.time())

            logging.debug('Time Now {} Last UPdate {} , {} - '.format(timeNow,self.update_time[EVid], self.carInfo[EVid] ))
            logging.debug('state : {}'.format(self.carInfo[EVid]['state']))           
            if 'timestamp' in self.carInfo[EVid]['climate_state'] and self.carInfo[EVid]['state'] in ['online']:
                self.update_time[EVid]['climate'] = float(self.carInfo[EVid]['climate_state']['timestamp']/1000)
                return(int(timeNow - self.update_time[EVid]['climate']))
            else:
                return(timeNow - self.update_time[EVid]['climate'])
        except Exception as e:
            logging.debug(f' Exception - not online teslaEV_GetTimeSinceLastClimateUpdate - {e}')
            return(int(timeNow - self.update_time[EVid]['climate']))
    '''
    def teslaEV_GetCabinTemp(self, EVid):
        return(self._stream_return_data(EVid, 'InsideTemp'))
        #try:
        #    logging.debug('teslaEV_GetCabinTemp for {} '.format(EVid))
        #    if self._stream_data_found(EVid, 'InsideTemp'):
        #        return(round(self.stream_data[EVid]['InsideTemp']['doubleValue'],1))
        #    else:
        #        return(None)
        #        #return(round(self.carInfo[EVid]['climate_state']['inside_temp'],1)) 
        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_GetCabinTemp - {e}')
        #    return(None)
        
    def teslaEV_GetOutdoorTemp(self, EVid):
        return(self._stream_return_data(EVid, 'OutsideTemp'))
        #try:
        #    logging.debug('teslaEV_GetOutdoorTemp for {}'.format(EVid))
        #    if self._stream_data_found(EVid, 'OutsideTemp'):
        #        return(round(self.stream_data[EVid]['OutsideTemp']['doubleValue'],1))
        #    else:
        #        return(None)
        #        #return(round(self.carInfo[EVid]['climate_state']['outside_temp'],1)) 
        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_GetOutdoorTemp - {e}')
        #    return(None)
        
    def teslaEV_GetLeftTemp(self, EVid):
        return(self._stream_return_data(EVid, 'HvacLeftTemperatureRequest'))

        #try:
        #    #logging.debug(f'teslaEV_GetLeftTemp for {EVid}')
        #    if self._stream_data_found(EVid, 'HvacLeftTemperatureRequest'):
        #        return(round(self.stream_data[EVid]['HvacLeftTemperatureRequest']['doubleValue'],1))
        #    else:
        #        return(None)
                #return(round(self.carInfo[EVid]['climate_state']['driver_temp_setting'],1))   

        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_GetLeftTemp - {e}')
        #    return(None)            

    def teslaEV_GetRightTemp(self, EVid):
        return(self._stream_return_data(EVid, 'HvacRightTemperatureRequest'))
        #try:
        #    #logging.debug(f'teslaEV_GetRightTemp for {EVid}')
        #    if self._stream_data_found(EVid, 'HvacRightTemperatureRequest'):
        #        return(round(self.stream_data[EVid]['HvacRightTemperatureRequest']['doubleValue'],1))
        #    else:
        #        return(None)
        #        #return(round(self.carInfo[EVid]['climate_state']['passenger_temp_setting'],1))   

        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_GetRightTemp - {e}')
        #    return(None)            

    def teslaEV_GetSeatHeating(self, EVid):
        try:
        #logging.debug(f'teslaEV_GetSeatHeating for {EVid}')
            temp = {}
            #temp['FrontLeft'] = None
            #temp['FrontRight'] = None
            #temp['RearLeft'] = None
            #temp['RearMiddle'] = None
            #temp['RearRight'] = None
            #if self._stream_data_found(EVid, 'SeatHeaterLeft'):
            temp['FrontLeft'] = self._stream_return_data(EVid, 'SeatHeaterLeft')
            #    self.stream_data[EVid]['SeatHeaterLeft']['intValue']
            #else:
            #    temp['FrontLeft'] = self.carInfo[EVid]['climate_state']['seat_heater_left']
            #if self._stream_data_found(EVid, 'SeatHeaterRight'):
            temp['FrontRight'] = self._stream_return_data(EVid, 'SeatHeaterRight')
            #else:
            #    temp['FrontRight'] = self.carInfo[EVid]['climate_state']['seat_heater_right']   
            #if self._stream_data_found(EVid, 'SeatHeaterRearLeft'):
            temp['RearLeft'] = self._stream_return_data(EVid, 'SeatHeaterRearLeft')
            #else:
            #    temp['RearLeft'] = self.carInfo[EVid]['climate_state']['seat_heater_rear_left']   
            #if self._stream_data_found(EVid, 'SeatHeaterRearCenter'):
            temp['RearMiddle'] = self._stream_return_data(EVid, 'SeatHeaterRearCenter')
            #else:
            #    temp['RearMiddle'] = self.carInfo[EVid]['climate_state']['seat_heater_rear_center']           
            #if self._stream_data_found(EVid, 'SeatHeaterRearRight'):
            temp['RearRight'] = self._stream_return_data(EVid, 'SeatHeaterRearRight')
            #else:
            #    temp['RearRight'] = self.carInfo[EVid]['climate_state']['seat_heater_rear_right']           
            return(temp)
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetSeatHeating - {e}')
            return(temp)            
 
############################   NEED TO RECONSIDER 
    def teslaEV_AutoConditioningRunning(self, EVid):
        
        try:
            if self._stream_return_data(EVid, 'AutoSeatClimateRight') or self._stream_return_data(EVid, 'AutoSeatClimateLeft'):
                return (self.stream_data[EVid]['AutoSeatClimateRight']['booleanValue'] or self.stream_data[EVid]['AutoSeatClimateLeft']['booleanValue'])
            else:
                return(None)
                #return( self.carInfo[EVid]['climate_state']['is_auto_conditioning_on']) 
        except Exception as e:
            logging.debug(f' Exception teslaEV_AutoConditioningRunning - {e}')
            return(None)      

    def teslaEV_PreConditioningEnabled(self, EVid):
        #logging.debug(f'teslaEV_PreConditioningEnabled for {EVid}')
        return(self._stream_return_data(EVid, 'PreconditioningEnabled'))
        #try:
        #    if self._stream_data_found(EVid, 'PreconditioningEnabled'):
        #        return(self.stream_data[EVid]['PreconditioningEnabled']['booleanValue'])
        #    else:
        #        return(None)
        #        #return(self.carInfo[EVid]['climate_state']['is_preconditioning'])
        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_PreConditioningEnabled - {e}')
        #    return(None)      
    '''
    def teslaEV_MaxCabinTempCtrl(self, EVid):
        #logging.debug(f'teslaEV_MaxCabinTempCtrl for {EVid}')
        try:
            if 'max_avail_temp' in self.carInfo[EVid]['climate_state']:
                return(round(self.carInfo[EVid]['climate_state']['max_avail_temp'],1))   
            else:
                return(None)
        except Exception as e:
            logging.debug(f' Exception teslaEV_MaxCabinTempCtrl - {e}')
            return(None)
        
        
    def teslaEV_MinCabinTempCtrl(self, EVid):
        #logging.debug(f'teslaEV_MinCabinTempCtrl for {EVid}')
        try:
            if 'min_avail_temp' in self.carInfo[EVid]['climate_state']:
                return(round(self.carInfo[EVid]['climate_state']['min_avail_temp'],1))   
            else:
                return(None)
        except Exception as e:
            logging.debug(f' Exception teslaEV_MinCabinTempCtrl - {e}')
            return(None)
    '''    
    def teslaEV_SteeringWheelHeatOn(self, EVid):
        #logging.debug(f'teslaEV_SteeringWheelHeatOn for {EVid}')
        return(self._stream_return_data(EVid, 'HvacSteeringWheelHeatLevel'))
        #try:
        #    if self._stream_data_found(EVid, 'HvacSteeringWheelHeatLevel'):
        #        return(self.stream_data[EVid]['HvacSteeringWheelHeatLevel']['intValue'])
        #    elif self._stream_data_found(EVid, 'HvacSteeringWheelHeatAuto'):
        #        return(self.stream_data[EVid]['HvacSteeringWheelHeatLevel']['booleanValue'])
        #    else:
        #        return(None)
        #        #return(self.carInfo[EVid]['climate_state']['steering_wheel_heater'])         
        #except Exception as e:
        #    logging.debug(f'teslaEV_SteeringWheelHeatOn Exception : {e}')
        #    return(None)

    def teslaEV_Windows(self, EVid, cmd):
        logging.debug(f'teslaEV_Windows {cmd} for {EVid}')

        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    
                #self.teslaEV_GetLocation()
                if cmd != 'vent' and cmd != 'close':
                    logging.error(f'Wrong command passed (vent or close) to teslaEV_Windows: {cmd}')
                    return('error', 'Wrong parameter passed: {cmd}')
                payload = {'lat':self.carInfo[EVid]['drive_state']['latitude'],
                            'lon':self.carInfo[EVid]['drive_state']['longitude'],
                            'command': cmd}        
                code, res = self._teslaEV_send_ev_command(EVid, '/window_control', payload ) 

                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')
        except Exception as e:
            logging.debug(f'Exception teslaEV_Windows for vehicle id {EVid}: {e}')       
            return('error', e)


    def teslaEV_SunRoof(self, EVid, cmd):
        logging.debug(f'teslaEV_SunRoof {cmd} for {EVid}')

        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:                
                if cmd not in ['vent','close', 'stop'] :
                    logging.error(f'Wrong command passed to (vent or close) to teslaEV_SunRoof: {cmd}')
                    return('error', 'Wrong parameter passed: {cmd}')
                payload = { 'state': cmd}     
                code, res = self._teslaEV_send_ev_command(EVid, '/sun_roof_control', payload )    
                if code in  ['ok']:

                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')
            
        except Exception as e:
            logging.debug(f'Exception teslaEV_SunRoof for vehicle id {EVid}: {e}')            
            return('error', e)


    def teslaEV_AutoCondition(self, EVid, ctrl):
        logging.debug(f'teslaEV_AutoCondition {ctrl} for {EVid}')

        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    
                if ctrl == 'start':  
                    code, res = self._teslaEV_send_ev_command(EVid, '/auto_conditioning_start') 
                elif ctrl == 'stop':
                    code, res = self._teslaEV_send_ev_command(EVid, '/auto_conditioning_stop') 
                else:
                    logging.debug(f'Unknown AutoCondition command passed for vehicle id {EVid}: {ctrl}')
                    return('error', 'Wrong parameter passed: {ctrl}')
                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')

        except Exception as e:
            logging.debug(f'Exception teslaEV_AutoCondition for vehicle id {EVid}: {e}')
            return('error', e)
            



    def teslaEV_SetCabinTemps(self, EVid, driverTempC, passergerTempC):
        logging.debug(f'teslaEV_SetCabinTemps {driverTempC} / {passergerTempC} for {EVid}')
    
        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    

                payload = {'driver_temp' : int(driverTempC), 'passenger_temp':int(passergerTempC) }      
                code, res = self._teslaEV_send_ev_command(EVid,'/set_temps', payload ) 
                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')

    
        except Exception as e:
            logging.debug(f'Exception teslaEV_SetCabinTemps for vehicle id {EVid}: {e}')
            return('error', e)


    def teslaEV_DefrostMax(self, EVid, ctrl):
        logging.debug(f'teslaEV_DefrostMax {ctrl} for {EVid}')
 
        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:                
                payload = {}    
                if ctrl == 'on':
                    payload = {'on':True,'manual_override':True }  
                elif  ctrl == 'off':
                    payload = {'on':False,'manual_override':True }  
                else:
                    logging.error(f'Wrong parameter for teslaEV_DefrostMax (on/off) for vehicle id {EVid} : {ctrl}')
                    return(False)
      
                code, res = self._teslaEV_send_ev_command(EVid, '/set_preconditioning_max', payload ) 
                if code in  ['ok']:

                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')

        except Exception as e:
            logging.debug(f'Exception teslaEV_DefrostMax for vehicle id {EVid}: {e}')

            return('error', e)


    def teslaEV_SetSeatHeating (self, EVid, seat, levelHeat):
        logging.debug(f'teslaEV_SetSeatHeating {levelHeat}, {seat} for {EVid}')
        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    

                seats = [0, 1, 2,3, 4, 5, 6, 7, 8 ] 
                rearSeats =  [2, 4, 5 ] 
                thirdrow = [3,6,7,8]
                if not 0 <= int(levelHeat) <= 3:
                    logging.error(f'Invalid seat heat level passed (0-3) : {levelHeat}')
                    return('error', 'Invalid seat heat level passed (0-3) : {levelHeat}')
                if seat not in seats: 
                    logging.error(f'Invalid seatpassed 0,1, 2, 4, 5 : {seat}')
                    return('error','Invalid seatpassed 0,1, 2, 4, 5 : {seat}')  
                elif not self.rearSeatHeat and seat in rearSeats:
                    logging.error(f'Rear seat heat not supported on this car')
                    return ('error', 'Rear seat heat not supported on this car')  

                payload = { 'heater': seat, 'level':int(levelHeat)}    
                code, res = self._teslaEV_send_ev_command(EVid, '/remote_seat_heater_request', payload ) 
                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    logging.error(f'Non 200 response: {code} {res}')
                    return(code, res)
            else:
                return('error', 'error')

        except Exception as e:
            logging.debug(f'Exception teslaEV_SetSeatHeating for vehicle id {EVid}: {e}')
            return('error', e)


    def teslaEV_SteeringWheelHeat(self, EVid, ctrl):
        logging.debug(f'teslaEV_SteeringWheelHeat {ctrl} for {EVid}')

        try:
            if self.steeringWheelHeatDetected:
                code, state = self.teslaEV_update_connection_status(EVid) 
                if state in ['asleep', 'offline']:
                    code, state = self._teslaEV_wake_ev(EVid)
                if state in ['online']:    

                    payload = {}    
                    if  0<= int(ctrl) <=3:
                        payload = {'level':int(ctrl)}  
                    else:
                        logging.error(f'Wrong paralf.carInfo[id]meter for teslaEV_SteeringWheelHeat (on/off) for vehicle id {EVid} : {ctrl}')
                        return('error', 'Wrong parameter passed: {ctrl}')

                    code, res = self._teslaEV_send_ev_command(EVid, '/remote_steering_wheel_heater_request', payload ) 
                    if code in  ['ok']:
   
                        return(code, res['response']['result'])
                    else:
                        logging.error(f'Non 200 response: {code} {res}')
                        return(code, res)
                else:
                    return('error', 'error')

            else:
                logging.error(f'Steering Wheet does not seem to support heating')
                return('error', 'Steering Wheet does not seem to support heating')
        except Exception as e:
            logging.debug(f'Exception teslaEV_SteeringWheelHeat for vehicle id {EVid}: {e}')
            return('error', e)

####################
# Status Data
####################
  
    def teslaEV_GetVersion(self, EVid):
        try:
            logging.debug('teslaEV_GetVersion')
            if self._stream_data_found(EVid, 'Version'):
                return(self.stream_data[EVid]['Version']['stringValue'])
            else:
                return(None)
        except Exception as e:
            return(None)
        

    def teslaEV_GetCenterDisplay(self, EVid):

        #logging.debug(f'teslaEV_GetCenterDisplay: for {EVid}')

        try:
            if self._stream_data_found(EVid, 'CenterDisplay'):
                if 'invalid' in  self.stream_data[EVid]['CenterDisplay']:
                    if self.stream_data[EVid]['CenterDisplay']['invalid']:
                        return('invalid')
                else:
                    return(self.stream_data[EVid]['CenterDisplay']['displayStateValue'])
            else:
                return(None)
                #return(self.carInfo[EVid]['vehicle_state']['center_display_state'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetCenterDisplay - {e}')
            return(None)

    def teslaEV_GetTimestamp(self, EVid):
        try:
            if self.stream_data[EVid]:
                return(self._stream_last_data(EVid))
            else: 
                return(None)     
                #return(self.carInfo[EVid]['vehicle_state']['timestamp'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetStatusTimestamp - {e}')
            return(None)

    ''''
    def teslaEV_GetTimeSinceLastStatusUpdate(self, EVid):
        try:
            timeNow = int(time.time())
            logging.debug('Time Now {} Last UPdate {} , {} - '.format(timeNow,self.update_time[EVid], self.carInfo[EVid] ))
            logging.debug('state : {}'.format(self.carInfo[EVid]['state']))            
            if 'timestamp' in self.carInfo[EVid]['vehicle_state'] and self.carInfo[EVid]['state'] in ['online']:
                self.update_time[EVid]['status'] = float(self.carInfo[EVid]['vehicle_state']['timestamp']/1000)
                return(int(timeNow - self.update_time[EVid]['status'] ))
            else:
                return(timeNow - self.update_time[EVid]['status'])
        except Exception as e:
            logging.debug(f' Exception - not online teslaEV_GetTimeSinceLastStatusUpdate - {e}')
            return(timeNow - self.update_time[EVid]['status'])
    '''


    def teslaEV_LocatedAtHome(self, EVid):
        #logging.debug(f'teslaEV_HomeLinkNearby: for {EVid}')
        return(self._stream_return_data(EVid, 'LocatedAtHome'))
    
    def teslaEV_LocatedAtFavorite(self, EVid):
        #logging.debug(f'teslaEV_HomeLinkNearby: for {EVid}')
        return(self._stream_return_data(EVid, 'LocatedAtFavorite'))    

    def teslaEV_HomeLinkNearby(self, EVid):
        #logging.debug(f'teslaEV_HomeLinkNearby: for {EVid}')
        return(self._stream_return_data(EVid, 'HomelinkNearby'))
        #try:
        #    if self._stream_data_found(EVid, 'HomelinkNearby'):
        #        return(self.stream_data[EVid]['HomelinkNearby']['booleanValue'])
        #    else:
        #        return(None)
        #        #return(self.carInfo[EVid]['vehicle_state']['homelink_nearby'])
        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_HomeLinkNearby - {e}')
        #    return(None)

    def teslaEV_nbrHomeLink(self, EVid):
        return(self._stream_return_data(EVid, 'HomelinkDeviceCount'))
        #logging.debug(f'teslaEV_nbrHomeLink: for {EVid}')

        #try:
        #    if self._stream_data_found(EVid, 'HomelinkDeviceCount'):
        #        return(self.stream_data[EVid]['HomelinkDeviceCount']['intValue'])
        #    else:
        #        return(None)
        3        #return(self.carInfo[EVid]['vehicle_state']['homelink_device_count'])
        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_nbrHomeLink - {e}')
        #    return(None)

    def teslaEV_GetLockState(self, EVid):
        #logging.debug(f'teslaEV_GetLockState: for {EVid}')
        return(self._stream_return_data(EVid, 'Locked'))
        #try:
        #    if self._stream_data_found(EVid, 'Locked'):
        #        return(self.stream_data[EVid]['Locked']['booleanValue'])
        #    else:
        #        return(None)
        #        #return(self.carInfo[EVid]['vehicle_state']['locked'])
        #except Exception as e:
        #    logging.debug(f' Exception teslaEV_GetLockState - {e}')
        #return(None)

    def _window_state2ISY(self, state):
        try:
            if state in ['WindowStateClosed', None]:
                return(0)
            else:
                return(1)
        except Exception:
            return(None)


    def teslaEV_GetWindowStates(self, EVid):
        #logging.debug(f'teslaEV_GetWindoStates: for {EVid}')
        try:
            temp = {}
            if self._stream_return_data(EVid, 'FdWindow'):
                temp['FrontLeft'] = self._window_state2ISY(self.stream_data[EVid]['FdWindow']['windowStateValue'])
            #elif  'fd_window' in self.carInfo[EVid]['vehicle_state']:
            #    temp['FrontLeft'] = self.carInfo[EVid]['vehicle_state']['fd_window']
            else:
                temp['FrontLeft'] = None
            if self._stream_return_data(EVid, 'FpWindow'):
                temp['FrontRight'] = self._window_state2ISY(self.stream_data[EVid]['FpWindow']['windowStateValue'])
            #elif 'fp_window' in self.carInfo[EVid]['vehicle_state']:
            #    temp['FrontRight'] = self.carInfo[EVid]['vehicle_state']['fp_window']
            else:
                temp['FrontRight'] = None
            if self._stream_return_data(EVid, 'RdWindow'):
                temp['RearLeft'] = self._window_state2ISY(self.stream_data[EVid]['RdWindow']['windowStateValue'])
            #elif 'rd_window' in self.carInfo[EVid]['vehicle_state']:
            #    temp['RearLeft'] = self.carInfo[EVid]['vehicle_state']['rd_window']
            else:
                temp['RearLeft'] = None
            if self._stream_return_data(EVid, 'RpWindow'):
                temp['RearRight'] = self._window_state2ISY(self.stream_data[EVid]['RpWindow']['windowStateValue'])       
            #elif 'rp_window' in self.carInfo[EVid]['vehicle_state']:
            #    temp['RearRight'] = self.carInfo[EVid]['vehicle_state']['rp_window']
            else:
                temp['RearRight'] = None
            logging.debug(f'teslaEV_GetWindoStates {EVid} {temp}')
            return(temp)
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetWindoStates - {e}')
            return(temp)
        

    def teslaEV_GetOdometer(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetOdometer: for {EVid}')
            if self._stream_return_data(EVid, 'Odometer'):
                return(round(self.stream_data[EVid]['Odometer']['doubleValue'],2))
            else:
                return(None)
                #return(round(self.carInfo[EVid]['vehicle_state']['odometer'], 2))

        except Exception as e:
            logging.debug(f' Exception teslaEV_GetOdometer - {e}')
            return(None)
        

    def teslaEV_GetSentryState(self, EVid):
        try:
            if self._stream_data_found(EVid, 'SentryMode'):
                if 'invalid' in  self.stream_data[EVid]['SentryMode']:
                    if self.stream_data[EVid]['SentryMode']['invalid']:
                        return('invalid')
                else:
                    return(str(self.stream_data[EVid]['SentryMode']['sentryModeStateValue']))
            else:
                return(None)
                #return(self.carInfo[EVid]['vehicle_state']['center_display_state'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetSentryState - {e}')
            return(None)
        '''
        try:
            #logging.debug(f'teslaEV_GetOdometer: for {EVid}')
            if self._stream_return_data(EVid, 'SentryMode'):
                return(self.stream_data[EVid]['SentryMode']['sentryModeStateValue'])
            else:
                return(None)
                #return(round(self.carInfo[EVid]['vehicle_state']['odometer'], 2))

        except Exception as e:
            logging.debug(f' Exception teslaEV_GetSentryState - {e}')
            return(None)

        '''


    #def teslaEV_GetSunRoofPercent(self, EVid):
    #    try:
    #        #logging.debug(f'teslaEV_GetSunRoofState: for {EVid}')
    #        if 'sun_roof_percent_open' in self.carInfo[EVid]['vehicle_state']:
    #            return(round(self.carInfo[EVid]['vehicle_state']['sun_roof_percent_open']))
    #        else:
    #            return(None)
    #    except Exception as e:
    #       logging.debug(f' Exception teslaEV_GetSunRoofPercent - {e}')
    #        return(None)
        
    def teslaEV_GetSunRoofState(self, EVid):
        #logging.debug(f'teslaEV_GetSunRoofState: for {EVid}')
        try:
            if 'sun_roof_state' in self.carInfo[EVid]['vehicle_config'] and self.sunroofInstalled:
                return(round(self.carInfo[EVid]['vehicle_state']['sun_roof_state']))
            else:
                return(None)
        except Exception as e:
            logging.error(f'teslaEV_GetSunRoofState Excaption: {e}')
            return(None)


    def teslaEV_getDoorState(self, EVid, door_type):
        if self._stream_data_found(EVid, 'DoorState'):
            logging.debug('DoorsState : {}'.format(self.stream_data[EVid]['DoorState']))
            if 'Doors' in self.stream_data[EVid]['DoorState']:
                if self.stream_data[EVid]['DoorState']['Doors'] in [door_type]:
                    return(self.stream_data[EVid]['DoorState']['Doors'][door_type])


    def teslaEV_GetAllDoorState(self, EVid):
        try:
            if self._stream_data_found(EVid, 'DoorState'):
                logging.debug('DoorsState : {}'.format(self.stream_data[EVid]['DoorState']))
                if 'Doors' in self.stream_data[EVid]['DoorState']:
                    if self.stream_data[EVid]['DoorState']['doorValue'] in ['DriverFront', 'DriverRear', 'PassengerFront', 'PassengerRear', 'TrunkFront','TrunkFront',] :
                        return(self.stream_data[EVid]['DoorState']['doorValue'])
                    else:
                        return(None)
        except Exception as e:
            logging.debug(f'teslaEV_GetTrunkState Exception: {e}')
            return(None)
        

    def teslaEV_GetTrunkState(self, EVid):
        #logging.debug(f'teslaEV_GetTrunkState: for {EVid}')
        try:
            if self._stream_data_found(EVid, 'DoorState'):
                logging.debug('DoorsState : {}'.format(self.stream_data[EVid]['DoorState']))
                if 'doorValue' in self.stream_data[EVid]['DoorState']:
                    found = False
                    for door in self.stream_data[EVid]['DoorState']['doorValue']:
                        if door in ['TrunkRear']:
                            found = True
                    if found:
                        return(1)
                    else:
                        return(0)
            #if self.carInfo[EVid]['vehicle_state']['rt'] == 0:
            #    return(0)
            #elif self.carInfo[EVid]['vehicle_state']['rt'] == 1:
            #    return(1)
            else:
                return(None)
        except Exception as e:
            logging.debug(f'teslaEV_GetTrunkState Exception: {e}')
            return(None)

    def teslaEV_GetFrunkState(self, EVid):
        #logging.debug(f'teslaEV_GetFrunkState: for {EVid}')
        try:
            if self._stream_data_found(EVid, 'DoorState'):
                logging.debug('DoorsState : {}'.format(self.stream_data[EVid]['DoorState']))
                if 'doorValue' in self.stream_data[EVid]['DoorState']:
                    found = False
                    for door in self.stream_data[EVid]['DoorState']['doorValue']:
                        if door in ['TrunkFront']:
                            found = True
                    if found:
                        return(1)
                    else:
                        return(0)

                else:
                    return(None)
            else:
                return(None)
        except Exception as e:
            logging.debug(f'teslaEV_GetFrunkState Exception: {e}')
            return(None)
        
    def teslaEV_getTpmsPressure(self, EVid):
        try:
            temp = {}
            temp['tmpsFr'] = round(14.5*self._stream_return_data(EVid, 'TpmsPressureFr'),2)
            temp['tmpsFl'] = round(14.5*self._stream_return_data(EVid, 'TpmsPressureFl'),2)
            temp['tmpsRr'] = round(14.5*self._stream_return_data(EVid, 'TpmsPressureRr'),2)                       
            temp['tmpsRl'] = round(14.5*self._stream_return_data(EVid, 'TpmsPressureRl'),2)
            return(temp)
        except Exception:
            temp['tmpsFr'] = None
            temp['tmpsFl'] = None
            temp['tmpsRr'] = None                       
            temp['tmpsRl'] = None
            return(temp)

###############
# Controls
################
    def teslaEV_FlashLights(self, EVid):
        logging.debug(f'teslaEV_GetVehicleInfo: for {EVid}')       

        try:

            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:             
                state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:   
                code, temp = self._teslaEV_send_ev_command(EVid, '/flash_lights')  
                logging.debug(f'temp {temp}')
            #temp = r.json()
                if  code in ['ok']:
                    temp['response']['result']
                    return(code, temp['response']['result'])
                else:
                    return(code, temp)
            else:
                return(code, state)
        except Exception as e:
            logging.debug(f'Exception teslaEV_FlashLight for vehicle id {EVid}: {e}')
            return('error', e)


    def teslaEV_HonkHorn(self, EVid):
        logging.debug(f'teslaEV_HonkHorn for {EVid}')

        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            logging.debug(f'teslaEV_HonkHorn {code} - {state}')
            if state in ['asleep', 'offline']:             
                state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    
          
                code, temp = self._teslaEV_send_ev_command(EVid, '/honk_horn')   
                logging.debug(f'teslaEV_HonkHorn {code} - {temp}')
                #temp = r.json()

                if code in ['ok']:
                    return(code, temp['response']['result'])
                else:
                    return(code, temp)
            else:
                return('error', state)
    
        except Exception as e:
            logging.debug(f'Exception teslaEV_HonkHorn for vehicle id {EVid}: {e}')           
            return('error', e)


    def teslaEV_PlaySound(self, EVid, sound):
        logging.debug(f'teslaEV_PlaySound for {EVid}')

        try:

            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:             
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    
                payload = {'sound' : sound}        
                code, res = self._teslaEV_send_ev_command(EVid, '/remote_boombox', payload ) 
                logging.debug(f'teslaEV_PlaySound {res}')
                #temp = r.json()
                if code in  ['ok']:

                    return(code, res['response']['result'])
                else:
                    return(code, res)
            else:
                return('error', 'error')
    
        except Exception as e:
            logging.debug(f'Exception teslaEV_PlaySound for vehicle id {EVid}: {e}')
            return('error', e)

    def teslaEV_SentryMode(self, EVid, ctrl):
        logging.debug(f'teslaEV_SentryMode for {EVid} {ctrl}')

        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:             
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:
                payload = {'on' : ctrl == 1}        
                code, res = self._teslaEV_send_ev_command(EVid, '/set_sentry_mode', payload ) 
                logging.debug(f'teslaEV_SentryMode {res}')
                #temp = r.json()
                if code in  ['ok']:
                    return(code, res['response']['result'])
                else:
                    return(code, res)
            else:
                return('error', 'error')
    
        except Exception as e:
            logging.debug(f'Exception teslaEV_PlaySound for vehicle id {EVid}: {e}')
            return('error', e)


    def teslaEV_Doors(self, EVid, ctrl):
        logging.debug(f'teslaEV_Doors {ctrl} for {EVid}')

        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:             
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:    
                if ctrl == 'unlock':  
                    code, res = self._teslaEV_send_ev_command(EVid, '/door_unlock')
                elif ctrl == 'lock':
                    code, res = self._teslaEV_send_ev_command(EVid, '/door_lock' )
                else:
                    logging.debug(f'Unknown door control passed: {ctrl}')
                    return('error', 'Unknown door control passed: {ctrl}')
                if code in ['ok']:
                    return(code, res['response']['result'])
                else:
                    return(code, state)
            else:
                return('error', state)

        except Exception as e:
            logging.error(f'Exception teslaEV_Doors for vehicle id {EVid}: {e}')
     
            return('error', e)


    def teslaEV_TrunkFrunk(self, EVid, frunkTrunk):
        logging.debug(f'teslaEV_Doors {frunkTrunk} for {EVid}')
        
        try:
            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:             
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:   
                if frunkTrunk.upper() == 'FRUNK' or frunkTrunk.upper() == 'FRONT':
                    cmd = 'front' 
                elif frunkTrunk.upper()  == 'TRUNK' or frunkTrunk.upper() == 'REAR':
                        cmd = 'rear' 
                else:
                    logging.debug(f'Unknown trunk command passed: {cmd}')
                    return('error', 'Unknown trunk command passed: {cmd}')
                payload = {'which_trunk':cmd}      
                code, res = self._teslaEV_send_ev_command(EVid, '/actuate_trunk', payload ) 

                if code in ['ok']:
                    return(code, res['response']['result'])
                else:
                    return(code, state)
            else:
                return('error', state)
                    
        except Exception as e:
            logging.debug(f'Exception teslaEV_TrunkFrunk for vehicle id {EVid}: {e}')
            return('error', e)


    def teslaEV_HomeLink(self, EVid):
        logging.debug(f'teslaEV_HomeLink for {EVid}')


        try:

            code, state = self.teslaEV_update_connection_status(EVid) 
            if state in ['asleep', 'offline']:             
                code, state = self._teslaEV_wake_ev(EVid)
            if state in ['online']:   
            
                payload = {'lat':self.carInfo[EVid]['drive_state']['latitude'],
                        'lon':self.carInfo[EVid]['drive_state']['longitude']}    
                code, res = self._teslaEV_send_ev_command(EVid, '/trigger_homelink', payload ) 
                if code in ['ok']:

                    return(code, res['response']['result'])
                else:
                    return(code, state)
            else:
                return('error', state)

        except Exception as e:
            logging.debug(f'Exception teslaEV_HomeLink for vehicle id {EVid}: {e}')
       
            return('error', e)

#############################
#    TeslaPW call through
#############################
'''        
    def tesla_set_storm_mode(self, site_id, mode) -> None:
        logging.debug(f'EV tesla_set_storm_mode : {site_id} {mode}')
        self.teslaPW_cloud.tesla_set_storm_mode(site_id, mode)

    def update_date_time(self, site_id) -> None:
        logging.debug(f'EV update_date_time : {site_id}')
        self.teslaPW_cloud.update_date_time(site_id)

    def teslaPW_GetTimestamp(self, site_id) -> None:
        logging.debug(f'EV teslaEV_GetTimestamp : {site_id}')
        self.teslaPW_cloud.teslaEV_GetTimestamp(site_id)


    def tesla_get_today_history(self, site_id, day_str) -> None:
        logging.debug(f'EV tesla_get_today_history : {site_id} {day_str}')
        self.teslaPW_cloud.tesla_get_today_history(site_id, day_str)

    def tesla_get_yesterday_history(self, site_id, day_str) -> None:
        logging.debug(f'EV tesla_get_yesterday_history : {site_id} {day_str}')
        self.teslaPW_cloud.tesla_get_yesterday_history(site_id, day_str)

    def tesla_get_2day_history(self, site_id, day_str) -> None:
        logging.debug(f'EV tesla_get_2day_history : {site_id} {day_str}')
        self.teslaPW_cloud.tesla_get_2day_history(site_id, day_str)

    def teslaUpdateCloudData(self , site_id, mode):
        logging.debug(f'EV teslaUpdateCloudData : {site_id} {mode}')
        self.teslaPW_cloud.teslaUpdateCloudData(site_id, mode)

    def tesla_set_operation(self , site_id, command):
        logging.debug(f'EV tesla_set_operation : {site_id} {command}')
        self.teslaPW_cloud.tesla_set_operation(site_id, command)

    def tesla_set_backup_percent(self , site_id, command):
        logging.debug(f'EV tesla_set_backup_percent : {site_id} {command}')
        self.teslaPW_cloud.tesla_set_backup_percent(site_id, command)

    def tesla_set_grid_import_export(self , site_id, enable, mode):
        logging.debug(f'EV tesla_set_grid_import_export : {site_id} {enable} {mode}') 
        self.teslaPW_cloud.tesla_set_grid_import_export(site_id, enable, mode)

    def tesla_live_grid_service_active(self, site_id) -> None:
        logging.debug(f'EV tesla_live_grid_service_active : {site_id}')
        self.teslaPW_cloud.tesla_live_grid_service_active(site_id)

    def teslaExtractOperationMode(self, site_id) -> None:
        logging.debug(f'EV teslaExtractOperationMode : {site_id}')
        self.teslaPW_cloud.teslaExtractOperationMode(site_id)

    def tesla_grid_staus(self, site_id) -> None:
        logging.debug(f'EV tesla_grid_staus : {site_id}')
        self.teslaPW_cloud.tesla_grid_staus(site_id)

    def tesla_home_energy_total(self, site_id, day):
        logging.debug(f'EV tesla_home_energy_total : {site_id} {day}')
        self.teslaPW_cloud.tesla_home_energy_total(site_id, day)

    def tesla_battery_energy_export(self, site_id, day):
        logging.debug(f'EV tesla_battery_energy_export : {site_id} {day}')
        self.teslaPW_cloud.tesla_battery_energy_export(site_id, day)

    def tesla_battery_energy_import(self, site_id, day):
        logging.debug(f'EV tesla_battery_energy_import : {site_id}  {day}')
        self.teslaPW_cloud.tesla_battery_energy_import(site_id, day)                                        

    def tesla_grid_energy_export(self, site_id, day):
        logging.debug(f'EV tesla_grid_energy_export : {site_id} {day}')
        self.teslaPW_cloud.tesla_grid_energy_export(site_id, day)

    def tesla_grid_energy_import(self, site_id, day):
        logging.debug(f'EV tesla_grid_energy_import : {site_id} {day}')
        self.teslaPW_cloud.tesla_grid_energy_import(site_id, day)                                        

    def tesla_set_off_grid_vehicle_charging(self, site_id, value):
        logging.debug(f'EV tesla_set_off_grid_vehicle_charging : {site_id} {value}')
        self.teslaPW_cloud.tesla_set_off_grid_vehicle_charging(site_id, value)

    def teslaExtractBackupPercent(self, site_id) -> None:
        logging.debug(f'EV teslaExtractBackupPercent : {site_id}')
        self.teslaPW_cloud.teslaExtractBackupPercent(site_id)       
 

    def teslaExtractStormMode(self, site_id) -> None:
        logging.debug(f'EV teslaExtractStormMode : {site_id}')
        self.teslaPW_cloud.teslaExtractStormMode(site_id)             
'''        