
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
class teslaApiAccess(teslaAccess):
    yourApiEndpoint = 'https://fleet-api.prd.na.vn.cloud.tesla.com'

    def __init__(self, polyglot, scope):
        super().__init__(polyglot, scope)
        logging.info('OAuth initializing')
        self.poly = polyglot
        self.scope = scope

        #self.customParameters = Custom(self.poly, 'customparams')
        self.stream_cert = Custom(polyglot, 'customdata')
        self.poly.subscribe(self.poly.CUSTOMDATA, self.customDataHandler)
        #self.scope_str = None
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
        self.stream_synched = False
        self.locationEn = False
        self.canActuateTrunks = False
        self.sunroofInstalled = False
        self.readSeatHeat = False
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
        self.powerShareEn = False
        self.teslaPW_cloud = None
        time.sleep(1)


    def customNsDone(self):
        return(self.customNsHandlerDone)
    
    def customDateDone(self):
        return(self.customDataHandlerDone )

    def customParamsDone(self):
        return(self.handleCustomParamsDone)

    def customDataHandler(self, data):
        logging.debug(f'customDataHandler start {self.stream_cert}')
        #self.stream_cert.load(data)
        logging.debug('handleData load - {}'.format(self.stream_cert))
        if 'issuedAt' not in  self.stream_cert.keys():
            self.stream_cert['issuedAt'] = None
            self.stream_cert['expiry'] = 0
            self.stream_cert['expectedRenewal'] = 0
            #self.stream_cert['ca'] = ''
        self.customDataHandlerDone = True


    def _teslaEV_retrieve_streaming_certificate(self):

        try:
            logging.debug('_teslaEV_retrieve_streaming_certificate')
            response = requests.get('https://my.isy.io/api/certificate')
            #logging.debug(f'certificate - response {response}')
            cert = {}
            if response.status_code == 200:
                res = response.json()
                logging.debug(f'renew response: {res}')
                if res['successful']:
                    cert['issuedAt'] = int(self.datestr_to_epoch(str(res['data']['issuedAt'])))

                    cert['expiry'] = int(self.datestr_to_epoch(str((res['data']['expiry']))))
                    cert['expectedRenewal'] = int(self.datestr_to_epoch(str((res['data']['expectedRenewal']))))
                    cert['ca'] = str(res['data']['ca'])
                    self.stream_cert = cert
                logging.debug(f'cert = {cert}')
        except Exception as e:
            logging.error(f'_teslaEV_retrieve_streaming_certificate - response {e}')  

    
    def _teslaEV_get_streaming_certificate(self):
        logging.debug('_teslaEV_get_streaming_certificate ')
        try:
            if self.stream_cert:
                if 'expectedRenewal' in self.stream_cert :
                    if self.stream_cert['expectedRenewal'] <= time.time():
                        self._teslaEV_retrieve_streaming_certificate()
                else:
                    self._teslaEV_retrieve_streaming_certificate()
            else:
                self._teslaEV_retrieve_streaming_certificate()
            return (self.stream_cert)
        except Exception as e:
            logging.error(f'_teslaEV_get_streaming_certificate - response {e}')
            return(None)


    def teslaEV_streaming_check_certificate_update(self, EV_vin, force_reset = False):        
        try: 
            logging.debug(f'teslaEV_update_streaming_certificate force reset {force_reset}')
            cert = self._teslaEV_get_streaming_certificate()
            logging.debug(f'cert = {cert}')

            if force_reset:
                logging.debug('Forced config ')
                code, res = self.teslaEV_streaming_delete_config(EV_vin)
                time.sleep(1)
                cert = self._teslaEV_get_streaming_certificate()
                code, res = self.teslaEV_streaming_create_config([EV_vin], cert['ca'])
                time.sleep(2) # give car chance to sync
            if 'expectedRenewal' in cert and cert['expectedRenewal'] <= time.time():
                self.stream_cert = cert
                logging.info('Updating Streaming configuration')
                code, res = self.teslaEV_streaming_create_config([EV_vin], cert['ca'])
                time.sleep(2) # give car chance to sync

            return(cert is not {} and not code in ['auth_error', 'overload', 'offline', 'erro'])
        except ValueError as e:  #First time - we need to create config
            logging.error(f'ERROR teslaEV_update_streaming_certificate creating config : {e}')
 
        
    
    def datestr_to_epoch(self, datestr):
        p = '%Y-%m-%dT%H:%M:%S.%fZ'
        mytime = str(datestr)
        epoch = datetime(1970, 1, 1)
        return(datetime.strptime(mytime, p) - epoch).total_seconds()



               
    def location_enabled(self):
        return(self.locationEn)
    
    def teslaEV_set_location_enabled(self, state):
        self.locationEn = ( state.upper() == 'TRUE')
        logging.debug(f'teslaEV_set_location_enabled {self.locationEn}')

    
    def teslaEV_set_power_share_enabled(self, state):
        self.powerShareEn = state
        logging.debug(f'teslaEV_set_power_share_enabled {self.powerShareEn}')

    def main_module_enabled(self, node_name):
        logging.debug(f'main_module_enabled called {node_name}')
        if node_name in self.customParameters :           
            return(int(self.customParameters[node_name]) == 1)
        else:
            self.customParameters[node_name] = 1 #add and enable by default
            self.poly.Notices['home_id'] = 'Check config to select which home/modules should be used (1 - used, 0 - not used) - then restart'
            return(True)

 
    def add_to_parameters(self,  key, value):
        '''add_to_parameters'''
        self.customParameters[key] = value

    def check_parameters(self, key, value):
        '''check_parameters'''
        if key in self.customParameters:
            return(self.customParameters[key]  == value)
        else:
            return(False)
    ###  Register car pem

    #def teslaEV_check_streaming_certificate(self):
    #    response = requests.get('https://my.isy.io/api/certificate')
    #    logging.debug(f'certificate - response {response}')
    #    if response.status_code == 200:
    #        self.stream_cert = response.json()


    def teslaEV_streaming_synched(self, EVid):
        try:
            logging.debug(f'Testing if Synched teslaEV_streaming_synched {EVid}')
            code, res  = self._callApi('GET','/vehicles/'+str(EVid) +'/fleet_telemetry_config')
            if code == 'ok':
                self.stream_synched = res['response']['synced']
            else:
                self.stream_synched = False
            logging.debug(f'teslaEV_streaming_synched {self.stream_synched} - {res}')
            return(self.stream_synched)
        except ValueError:
            return(False)


    def teslaEV_streaming_delete_config(self, EVid):
        try:
            logging.debug(f'teslaEV_streaming_delete_config {EVid}')

            code, res  = self._callApi('DELETE','/vehicles/'+str(EVid) +'/fleet_telemetry_config')
            if code == 'ok':
                return(code, res)                         
        except Exception:
            return (None, None)
        
        
    def teslaEV_streaming_create_config(self, vin_list, Cert_CA):
        logging.debug(f'teslaEV_create_config {vin_list}')
        #vinstr_list = []
        #for item in vin_list:
        #    logging.debug(f'item{item}')
        #istr =  vin_list
        #vinstr_list.append(istr)
        #logging.debug(f'vinstr_list {vinstr_list}')
        location_field = {}
        powershare_fields = {}
        stream_fields = {                  
                        'EstBatteryRange' : { 'interval_seconds': 1, 'minimum_delta': 1, 'resend_interval_seconds' : 600 },                    
                        'ChargeCurrentRequest' : { 'interval_seconds': 1 },
                        'ChargeCurrentRequestMax': { 'interval_seconds': 1 },                        
                        'ChargeAmps' : { 'interval_seconds': 1, 'minimum_delta': 0.5, },
                        'TimeToFullCharge' : { 'interval_seconds': 1, 'minimum_delta': 1,  },
                        'Soc' : { 'interval_seconds': 1, 'minimum_delta': 1 },
                        'ChargerVoltage' : { 'interval_seconds': 1, 'minimum_delta': 2, },                    
                        'FastChargerPresent' : { 'interval_seconds': 1 },
                        'ChargePortDoorOpen' : { 'interval_seconds': 1 },
                        'ChargePortLatch' : { 'interval_seconds': 1 },
                        'BatteryLevel' : { 'interval_seconds': 1, 'minimum_delta': 1,'resend_interval_seconds' : 600 },
                        #'ChargeState': { 'interval_seconds': 60 },;
                        'DetailedChargeState' : { 'interval_seconds': 1 },
                        'ChargeLimitSoc': { 'interval_seconds': 1, 'minimum_delta': 1, },
                        'InsideTemp': { 'interval_seconds': 1, 'minimum_delta': 1, },
                        'OutsideTemp': { 'interval_seconds': 1,'minimum_delta': 1,  },
                        'SeatHeaterLeft' : { 'interval_seconds': 1 },
                        'SeatHeaterRight' : { 'interval_seconds': 1 },
                        'SeatHeaterRearLeft' : { 'interval_seconds': 1 },
                        'SeatHeaterRearRight' : { 'interval_seconds': 1 },
                        'SeatHeaterRearCenter' : { 'interval_seconds': 1 },
                        'AutoSeatClimateLeft' : { 'interval_seconds': 1 },
                        'AutoSeatClimateRight' : { 'interval_seconds': 1 },
                        'HvacLeftTemperatureRequest' : { 'interval_seconds': 1 },
                        'HvacRightTemperatureRequest' : { 'interval_seconds': 1 },
                        'PreconditioningEnabled' : { 'interval_seconds': 1 },
                        'HvacSteeringWheelHeatAuto' : { 'interval_seconds': 1 },
                        'HvacSteeringWheelHeatLevel' : { 'interval_seconds': 1 },
                        'HomelinkDeviceCount' : { 'interval_seconds': 1 },
                        'HomelinkNearby' : { 'interval_seconds': 1 },                        
                        'Odometer': { 'interval_seconds': 1,'minimum_delta': 1},
                        'DoorState' : { 'interval_seconds': 1 },
     
                        'DCChargingEnergyIn': { 'interval_seconds': 1, 'minimum_delta': 5 },
                        'DCChargingPower' : { 'interval_seconds': 1, 'minimum_delta': 5 },
                        'ACChargingEnergyIn': { 'interval_seconds': 1,'minimum_delta': 5 },
                        'ACChargingPower' : { 'interval_seconds': 1 ,'minimum_delta': 5},
                        'Locked' : { 'interval_seconds': 1 },
                        'FdWindow': { 'interval_seconds': 1 },
                        'FpWindow' : { 'interval_seconds': 1 },
                        'RdWindow': { 'interval_seconds': 1 },
                        'RpWindow' : { 'interval_seconds': 1,  },

                        'TpmsPressureFl' : { 'interval_seconds': 1,'minimum_delta': 0.1 },
                        'TpmsPressureFr' : { 'interval_seconds': 1,'minimum_delta': 0.1  },
                        'TpmsPressureRl' : { 'interval_seconds': 1,'minimum_delta': 0.1  },
                        'TpmsPressureRr': { 'interval_seconds': 1,'minimum_delta': 0.1  },
                        'SettingDistanceUnit' :{ 'interval_seconds': 1 },
                        'SettingTemperatureUnit' :{ 'interval_seconds': 1 },
                        'SettingTirePressureUnit' :{ 'interval_seconds': 1 },
                        'CenterDisplay': { 'interval_seconds': 1 },
                        'DefrostMode':{ 'interval_seconds': 1 },
                        'SunroofInstalled':{ 'interval_seconds': 1 },     
                        'WiperHeatEnabled':{ 'interval_seconds': 1 },    
                        'SentryMode':{ 'interval_seconds': 1 },    


                      
                        #'Version' : { 'interval_seconds': 60, },
                        #'VehicleName': { 'interval_seconds': 60},
                        #'WindowState' : { 'interval_seconds': 60 },
                        #'ChargingState' : { 'interval_seconds': 60 },                        
                        #'ChargeCurrentRequestMax' : { 'interval_seconds': 60 },
                        #'DetailedChargeStateValue' : { 'interval_seconds': 60 },                        
                        #charger_actual_current
                        #charge_energy_added
                        #charge_miles_added_rated   
                        #charger_power                     
                        }
        if self.locationEn:
            location_field = {
                                    'LocatedAtHome' : { 'interval_seconds': 60 },
                                    'LocatedAtFavorite' : { 'interval_seconds': 60 },
                                    'Location' : { 'interval_seconds': 60 },                                    
                        }
        
        if self.powerShareEn:  # there are wall connector / power share
            powershare_fields = {
                        'PowershareHoursLeft':{ 'interval_seconds': 60,'minimum_delta': 0.016  },     
                        'PowershareInstantaneousPowerKW':{ 'interval_seconds': 60, 'minimum_delta': 0.1  },     
                        'PowershareStatus':{ 'interval_seconds': 60 },     
                        'PowershareStopReason':{ 'interval_seconds': 60 },     
                        'PowershareType':{ 'interval_seconds': 60 },  
                        }

        if  int(self.stream_cert['expiry']) >= (time.time() + 22809600) : #22809600 = 60*60*24*264 (1 day less that a year)
            exp = int(time.time() + 22809600 )
        else:
            exp = int(self.stream_cert['expiry'])
        cfg = {'vins': vin_list ,
               'config': { 'prefer_typed': True,
                    'port': 443,
                    "delivery_policy": "latest",
                    'exp': exp,
                    'alert_types': [ 'service' ],
                    'fields': stream_fields | location_field | powershare_fields, 
                    'ca' : Cert_CA,
                    'hostname': 'my.isy.io'
                    },               
            }
        payload = json.dumps(cfg)
        payload = cfg
        logging.debug(f'payload: {payload}')
        code, res  = self._callApi('POST','/vehicles/fleet_telemetry_config', payload)
        logging.debug(f' config res {code} {res}')
        return(code, res)
  
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