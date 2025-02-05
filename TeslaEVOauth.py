
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
class teslaEVAccess(teslaAccess):
    yourApiEndpoint = 'https://fleet-api.prd.na.vn.cloud.tesla.com'

    def __init__(self, polyglot, scope):
        super().__init__(polyglot, scope)
        logging.info('OAuth initializing')
        self.poly = polyglot
        self.scope = scope
        self.stream_cert = {}
        self.customParameters = Custom(self.poly, 'customparams')
        self.poly.subscribe(self.poly.CUSTOMDATA, self.customDataHandler) 
        self.stream_cert = Custom(self.poly, 'customdata')
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
        time.sleep(1)


    def customNsDone(self):
        return(self.customNsHandlerDone)
    
    def customDateDone(self):
        return(self.customDataHandlerDone )

    def customParamsDone(self):
        return(self.handleCustomParamsDone)

    def customDataHandler(self, data):
        logging.debug('customDataHandler')
        self.stream_cert.load(data)
        logging.debug('handleData load - {}'.format(self.stream_cert))
        if 'issuedAt' not in  self.stream_cert.keys():
                self.stream_cert['issuedAt'] = None
                self.stream_cert['expiry'] = None
                self.stream_cert['expectedRenewal'] = None
                self.stream_cert['ca'] = ''
        self.customDataHandlerDone = True

    
    def teslaEV_get_streaming_certificate(self):
        response = requests.get('https://my.isy.io/api/certificate')
        logging.debug(f'certificate - response {response}')
        cert = {}
        if response.status_code == 200:
            res = response.json()
            if res['successful']:
                cert['issuedAt'] = int(self.datestr_to_epoch(str(res['data']['issuedAt'])))
                cert['expiry'] = int(self.datestr_to_epoch(str((res['data']['expiry']))))
                cert['expectedRenewal'] = int(self.datestr_to_epoch(str((res['data']['expectedRenewal']))))
                cert['ca'] = str(res['data']['ca'])
        return (cert)
    

    def teslaEV_check_streaming_certificate_update(self):
        logging.debug('teslaEV_update_streaming_certificate')
        temp = self.teslaEV_get_streaming_certificate()
        logging.debug(f'temp certificat {temp} org {self.stream_cert}')
        if not self.stream_cert['issuedAt']:
            self.stream_cert = temp
            return(True)
        elif temp['issuedAt'] > self.stream_cert['issuedAt']:
            self.stream_cert = temp
            return(True)
        else:
            return(False)
        
    
    def datestr_to_epoch(self, datestr):
        p = '%Y-%m-%dT%H:%M:%S.%fZ'
        mytime = str(datestr)
        epoch = datetime(1970, 1, 1)
        return(datetime.strptime(mytime, p) - epoch).total_seconds()



               
    def location_enabled(self):
        return(self.locationEn)
    
    def teslaEV_set_location_enabled(self, state):
        self.locationEn = ( state.upper() == 'TRUE')

    
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




    def teslaEV_create_streaming_config(self, vin_list):
        logging.debug(f'teslaEV_create_config {vin_list}')
        #vinstr_list = []
        #for item in vin_list:
        #    logging.debug(f'item{item}')
        #istr =  vin_list
        #vinstr_list.append(istr)
        #logging.debug(f'vinstr_list {vinstr_list}')
        
        cfg = {'vins': vin_list ,
               'config': { 'prefer_typed': True,
                    'port': 443,
                    'exp': int(self.stream_cert['expiry']),
                    'alert_types': [ 'service' ],
                    'fields': {
                        'IdealBatteryRange' : { 'interval_seconds': 60, 'minimum_delta': 1 },
                        'EstBatteryRange' : { 'interval_seconds': 60, 'minimum_delta': 1 },                    
                        'ChargeCurrentRequest' : { 'interval_seconds': 60 },
                        'ChargeCurrentRequestMax': { 'interval_seconds': 60 },                        
                        'ChargeAmps' : { 'interval_seconds': 60,'minimum_delta': 1 },
                        'TimeToFullCharge' : { 'interval_seconds': 60 },
                        'ChargerVoltage' : { 'interval_seconds': 60, 'minimum_delta': 1 },                    
                        'FastChargerPresent' : { 'interval_seconds': 60 },
                        'ChargePort' : { 'interval_seconds': 60 },
                        'ChargePortLatch' : { 'interval_seconds': 60 },
                        'BatteryLevel' : { 'interval_seconds': 60, 'minimum_delta': 1 },
                        'ChargeState': { 'interval_seconds': 60 },
                        'ChargeLimitSoc': { 'interval_seconds': 60 },
                        'InsideTemp': { 'interval_seconds': 60, 'minimum_delta': 1, },
                        'OutsideTemp': { 'interval_seconds': 60,'minimum_delta': 1,  },
                        'SeatHeaterLeft' : { 'interval_seconds': 60 },
                        'SeatHeaterRight' : { 'interval_seconds': 60 },
                        'SeatHeaterRearLeft' : { 'interval_seconds': 60 },
                        'SeatHeaterRearRight' : { 'interval_seconds': 60 },
                        'SeatHeaterRearCenter' : { 'interval_seconds': 60 },
                        'AutoSeatClimateLeft' : { 'interval_seconds': 60 },
                        'AutoSeatClimateRight' : { 'interval_seconds': 60 },
                        'HvacLeftTemperatureRequest' : { 'interval_seconds': 60 },
                        'HvacRightTemperatureRequest' : { 'interval_seconds': 60 },
                        'PreconditioningEnabled' : { 'interval_seconds': 60 },
                        'HvacSteeringWheelHeatAuto' : { 'interval_seconds': 60 },
                        'HvacSteeringWheelHeatLevel' : { 'interval_seconds': 60 },
                        'HomelinkDeviceCount' : { 'interval_seconds': 600 },
                        'HomelinkNearby' : { 'interval_seconds': 60 },                        
                        'Odometer': { 'interval_seconds': 60,'minimum_delta': 1},
                        'DoorState' : { 'interval_seconds': 60 },
                        'Location' : { 'interval_seconds': 60 },
                        'DCChargingEnergyIn': { 'interval_seconds': 60 },
                        'DCChargingPower' : { 'interval_seconds': 60 },
                        'ACChargingEnergyIn': { 'interval_seconds': 60 },
                        'ACChargingPower' : { 'interval_seconds': 60 },
                        'Locked' : { 'interval_seconds': 60 },
                        'FdWindow': { 'interval_seconds': 60 },
                        'FpWindow' : { 'interval_seconds': 60 },
                        'RdWindow': { 'interval_seconds': 60 },
                        'RpWindow' : { 'interval_seconds': 60 },
                        'VehicleName': { 'interval_seconds': 600},
                        'Version' : { 'interval_seconds': 600, },
                        'TpmsPressureFl' : { 'interval_seconds': 60 },
                        'TpmsPressureFr' : { 'interval_seconds': 60 },
                        'TpmsPressureRl' : { 'interval_seconds': 60 },
                        'TpmsPressureRr': { 'interval_seconds': 60 },

                        #'WindowState' : { 'interval_seconds': 60 },
                        #'ChargingState' : { 'interval_seconds': 60 },                        
                        #'ChargeCurrentRequestMax' : { 'interval_seconds': 60 },
                        #'DetailedChargeStateValue' : { 'interval_seconds': 60 },                        
                        #charger_actual_current
                        #charge_energy_added
                        #charge_miles_added_rated   
                        #charger_power                     
                        },
                    'ca' : self.stream_cert['ca'],
                    'hostname': 'my.isy.io'
                    },
                
            }
        
        cfg1={
            "vins": ["5YJ3E1EA5RF721953"],
            "config": {
            "prefer_typed": True,
            "port": 443,
            "exp": 1763824091,
            "alert_types": ["service"],
            "fields": {
                "VehicleSpeed": { "interval_seconds": 10 },
                "Location": { "interval_seconds": 10 },
                "DoorState": { "interval_seconds": 1 },
                "Odometer": { "interval_seconds": 60 },
                "Locked": { "interval_seconds": 1 },
                "EstBatteryRange": { "interval_seconds": 60 }
            },
            'ca' : self.stream_cert['ca'],            
            #"ca": "-----BEGIN CERTIFICATE-----\nMIIEXjCCA0agAwIBAgITB3MSSkvL1E7HtTvq8ZSELToPoTANBgkqhkiG9w0BAQsF\nADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6\nb24gUm9vdCBDQSAxMB4XDTIyMDgyMzIyMjUzMFoXDTMwMDgyMzIyMjUzMFowPDEL\nMAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEcMBoGA1UEAxMTQW1hem9uIFJT\nQSAyMDQ4IE0wMjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALtDGMZa\nqHneKei1by6+pUPPLljTB143Si6VpEWPc6mSkFhZb/6qrkZyoHlQLbDYnI2D7hD0\nsdzEqfnuAjIsuXQLG3A8TvX6V3oFNBFVe8NlLJHvBseKY88saLwufxkZVwk74g4n\nWlNMXzla9Y5F3wwRHwMVH443xGz6UtGSZSqQ94eFx5X7Tlqt8whi8qCaKdZ5rNak\n+r9nUThOeClqFd4oXych//Rc7Y0eX1KNWHYSI1Nk31mYgiK3JvH063g+K9tHA63Z\neTgKgndlh+WI+zv7i44HepRZjA1FYwYZ9Vv/9UkC5Yz8/yU65fgjaE+wVHM4e/Yy\nC2osrPWE7gJ+dXMCAwEAAaOCAVowggFWMBIGA1UdEwEB/wQIMAYBAf8CAQAwDgYD\nVR0PAQH/BAQDAgGGMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjAdBgNV\nHQ4EFgQUwDFSzVpQw4J8dHHOy+mc+XrrguIwHwYDVR0jBBgwFoAUhBjMhTTsvAyU\nlC4IWZzHshBOCggwewYIKwYBBQUHAQEEbzBtMC8GCCsGAQUFBzABhiNodHRwOi8v\nb2NzcC5yb290Y2ExLmFtYXpvbnRydXN0LmNvbTA6BggrBgEFBQcwAoYuaHR0cDov\nL2NydC5yb290Y2ExLmFtYXpvbnRydXN0LmNvbS9yb290Y2ExLmNlcjA/BgNVHR8E\nODA2MDSgMqAwhi5odHRwOi8vY3JsLnJvb3RjYTEuYW1hem9udHJ1c3QuY29tL3Jv\nb3RjYTEuY3JsMBMGA1UdIAQMMAowCAYGZ4EMAQIBMA0GCSqGSIb3DQEBCwUAA4IB\nAQAtTi6Fs0Azfi+iwm7jrz+CSxHH+uHl7Law3MQSXVtR8RV53PtR6r/6gNpqlzdo\nZq4FKbADi1v9Bun8RY8D51uedRfjsbeodizeBB8nXmeyD33Ep7VATj4ozcd31YFV\nfgRhvTSxNrrTlNpWkUk0m3BMPv8sg381HhA6uEYokE5q9uws/3YkKqRiEz3TsaWm\nJqIRZhMbgAfp7O7FUwFIb7UIspogZSKxPIWJpxiPo3TcBambbVtQOcNRWz5qCQdD\nslI2yayq0n2TXoHyNCLEH8rpsJRVILFsg0jc7BaFrMnF462+ajSehgj12IidNeRN\n4zl+EoNaWdpnWndvSpAEkq2P\n-----END CERTIFICATE-----\n-----BEGIN CERTIFICATE-----\nMIIEkjCCA3qgAwIBAgITBn+USionzfP6wq4rAfkI7rnExjANBgkqhkiG9w0BAQsF\nADCBmDELMAkGA1UEBhMCVVMxEDAOBgNVBAgTB0FyaXpvbmExEzARBgNVBAcTClNj\nb3R0c2RhbGUxJTAjBgNVBAoTHFN0YXJmaWVsZCBUZWNobm9sb2dpZXMsIEluYy4x\nOzA5BgNVBAMTMlN0YXJmaWVsZCBTZXJ2aWNlcyBSb290IENlcnRpZmljYXRlIEF1\ndGhvcml0eSAtIEcyMB4XDTE1MDUyNTEyMDAwMFoXDTM3MTIzMTAxMDAwMFowOTEL\nMAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv\nb3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj\nca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM\n9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw\nIFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6\nVOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L\n93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm\njgSubJrIqg0CAwEAAaOCATEwggEtMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/\nBAQDAgGGMB0GA1UdDgQWBBSEGMyFNOy8DJSULghZnMeyEE4KCDAfBgNVHSMEGDAW\ngBScXwDfqgHXMCs4iKK4bUqc8hGRgzB4BggrBgEFBQcBAQRsMGowLgYIKwYBBQUH\nMAGGImh0dHA6Ly9vY3NwLnJvb3RnMi5hbWF6b250cnVzdC5jb20wOAYIKwYBBQUH\nMAKGLGh0dHA6Ly9jcnQucm9vdGcyLmFtYXpvbnRydXN0LmNvbS9yb290ZzIuY2Vy\nMD0GA1UdHwQ2MDQwMqAwoC6GLGh0dHA6Ly9jcmwucm9vdGcyLmFtYXpvbnRydXN0\nLmNvbS9yb290ZzIuY3JsMBEGA1UdIAQKMAgwBgYEVR0gADANBgkqhkiG9w0BAQsF\nAAOCAQEAYjdCXLwQtT6LLOkMm2xF4gcAevnFWAu5CIw+7bMlPLVvUOTNNWqnkzSW\nMiGpSESrnO09tKpzbeR/FoCJbM8oAxiDR3mjEH4wW6w7sGDgd9QIpuEdfF7Au/ma\neyKdpwAJfqxGF4PcnCZXmTA5YpaP7dreqsXMGz7KQ2hsVxa81Q4gLv7/wmpdLqBK\nbRRYh5TmOTFffHPLkIhqhBGWJ6bt2YFGpn6jcgAKUj6DiAdjd4lpFw85hdKrCEVN\n0FE6/V1dN2RMfjCyVSRCnTawXZwXgWHxyvkQAiSr6w10kY17RSlQOYiypok1JR4U\nakcjMS9cmvqtmg5iUaQqqcT5NJ0hGA==\n-----END CERTIFICATE-----\n-----BEGIN CERTIFICATE-----\nMIIEdTCCA12gAwIBAgIJAKcOSkw0grd/MA0GCSqGSIb3DQEBCwUAMGgxCzAJBgNV\nBAYTAlVTMSUwIwYDVQQKExxTdGFyZmllbGQgVGVjaG5vbG9naWVzLCBJbmMuMTIw\nMAYDVQQLEylTdGFyZmllbGQgQ2xhc3MgMiBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0\neTAeFw0wOTA5MDIwMDAwMDBaFw0zNDA2MjgxNzM5MTZaMIGYMQswCQYDVQQGEwJV\nUzEQMA4GA1UECBMHQXJpem9uYTETMBEGA1UEBxMKU2NvdHRzZGFsZTElMCMGA1UE\nChMcU3RhcmZpZWxkIFRlY2hub2xvZ2llcywgSW5jLjE7MDkGA1UEAxMyU3RhcmZp\nZWxkIFNlcnZpY2VzIFJvb3QgQ2VydGlmaWNhdGUgQXV0aG9yaXR5IC0gRzIwggEi\nMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDVDDrEKvlO4vW+GZdfjohTsR8/\ny8+fIBNtKTrID30892t2OGPZNmCom15cAICyL1l/9of5JUOG52kbUpqQ4XHj2C0N\nTm/2yEnZtvMaVq4rtnQU68/7JuMauh2WLmo7WJSJR1b/JaCTcFOD2oR0FMNnngRo\nOt+OQFodSk7PQ5E751bWAHDLUu57fa4657wx+UX2wmDPE1kCK4DMNEffud6QZW0C\nzyyRpqbn3oUYSXxmTqM6bam17jQuug0DuDPfR+uxa40l2ZvOgdFFRjKWcIfeAg5J\nQ4W2bHO7ZOphQazJ1FTfhy/HIrImzJ9ZVGif/L4qL8RVHHVAYBeFAlU5i38FAgMB\nAAGjgfAwge0wDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAYYwHQYDVR0O\nBBYEFJxfAN+qAdcwKziIorhtSpzyEZGDMB8GA1UdIwQYMBaAFL9ft9HO3R+G9FtV\nrNzXEMIOqYjnME8GCCsGAQUFBwEBBEMwQTAcBggrBgEFBQcwAYYQaHR0cDovL28u\nc3MyLnVzLzAhBggrBgEFBQcwAoYVaHR0cDovL3guc3MyLnVzL3guY2VyMCYGA1Ud\nHwQfMB0wG6AZoBeGFWh0dHA6Ly9zLnNzMi51cy9yLmNybDARBgNVHSAECjAIMAYG\nBFUdIAAwDQYJKoZIhvcNAQELBQADggEBACMd44pXyn3pF3lM8R5V/cxTbj5HD9/G\nVfKyBDbtgB9TxF00KGu+x1X8Z+rLP3+QsjPNG1gQggL4+C/1E2DUBc7xgQjB3ad1\nl08YuW3e95ORCLp+QCztweq7dp4zBncdDQh/U90bZKuCJ/Fp1U1ervShw3WnWEQt\n8jxwmKy6abaVd38PMV4s/KCHOkdp8Hlf9BRUpJVeEXgSYCfOn8J3/yNTd126/+pZ\n59vPr5KW7ySaNRB6nJHGDn2Z9j8Z3/VyVOEVqQdZe4O/Ui5GjLIAZHYcSNPYeehu\nVsyuLAOQ1xk4meTKCRlb/weWsKh/NEnfVqn3sF/tM+2MR7cwA130A4w=\n-----END CERTIFICATE-----\n",
            "hostname": "my.isy.io"
            },

        }

        payload = json.dumps(cfg)
        payload = cfg
        logging.debug(f'payload: {payload}')
        code, res  = self._callApi('POST','/vehicles/fleet_telemetry_config', payload)
        logging.debug(f' config res {code} {res}')
   
    def extract_needed_delay(self, input_string):
        temp =  [int(word) for word in input_string.split() if word.isdigit()]
        if temp != []:
            return(temp[0])
        else:
            return(0)
        
    def teslaEV_get_vehicle_list(self) -> list:
        return(self.ev_list)
    
    def teslaEV_get_vehicles(self):
        EVs = {}
        logging.debug(f'teslaEV_get_vehicles ')
        try:
            self.ev_list =[]
            code, temp = self._callApi('GET','/vehicles' )
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
    
   
    def _teslaEV_wake_ev(self, EVid):
        logging.debug(f'_teslaEV_wake_ev - {EVid}')
        trys = 1
        timeNow = time.time()
        try:
            code, state = self.teslaEV_update_connection_status(EVid)
            if code == 'ok':
                if timeNow >= self.next_wake_call:
                    if state in ['asleep','offline']:
                        code, res  = self._callApi('POST','/vehicles/'+str(EVid) +'/wake_up')
                        logging.debug(f'wakeup: {code} - {res}')
                        if code in  ['ok']:
                            time.sleep(5)
                            code, state = self.teslaEV_update_connection_status(EVid)
                            logging.debug(f'wake_ev while loop {code} - {state}')
                            while code in ['ok'] and state not in ['online'] and trys < 5:
                                trys += 1
                                time.sleep(5)
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
        code, res = self._callApi('GET','/vehicles/'+str(EVid) +'/vehicle_data', payload  )
        logging.debug(f'vehicel data: {code} {res}')




        return(code, res)

    def _teslaEV_send_ev_command(self, EVid , command, params=None):
        logging.debug(f'send_ev_command - command  {command} - params: {params} - {EVid}')
        payload = params
        code, res = self._callApi('POST','/vehicles/'+str(EVid) +'/command'+str(command),  payload )

        if code in ['ok'] and not res['response']['result']:
            # something went wrong - try again
            logging.debug('Something went wrong - trying again {}'.format(res['response']))
            time.sleep(5)
            code, res = self._callApi('POST','/vehicles/'+str(EVid) +'/command'+str(command),  payload ) 
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
                        return(code, self.teslaEV_GetCarState(EVid))
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
                        return(code, self.teslaEV_GetCarState(EVid))
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
            logging.debug('teslaEV_GetCarState: {}'.format(self.carInfo[EVid]['state']))

            return(self.carInfo[EVid]['state'])
        except Exception as e:
            logging.error(f'teslaEV_GetCarState Exception : {e}')
            return(None)


    def teslaEV_GetConnectionStatus(self, EVid):
        #logging.debug(f'teslaEV_GetConnectionStatus: for {EVid}')
        return(self.carInfo[EVid]['state'])

    def teslaEV_update_vehicle_status(self, EVid) -> dict:
        self.products= {}
        EVs = {}
        logging.debug(f'teslaEV_get_vehicle_info ')
        try:
            code, res = self._callApi('GET','/vehicles/'+str(EVid) )
            logging.debug(f'vehicle {EVid} info : {code} {res} ')
            if code in ['ok']:
                self.carInfo[res['response']['vin']] = res['response']
                return(code, res['response'])
            else:
                return(code, res)
        except Exception as e:
            logging.error(f'teslaEV_update_vehicle_status Exception : {e}')
    

    def teslaEV_update_connection_status(self, EVid):
        #logging.debug(f'teslaEV_GetConnectionStatus: for {EVid}')
        try:
            code, res = self.teslaEV_update_vehicle_status(EVid)
            logging.debug(f'teslaEV_update_connection_status {code} {res}')
            return(code, self.carInfo[EVid]['state'])
        except Exception as e:
            logging.error(f'teslaEV_update_connection_status - {e}')
            return('error', e)

    def teslaEV_GetName(self, EVid):
        try:
            return(self.carInfo[EVid]['vehicle_state']['vehicle_name'])

        except Exception as e:
            logging.debug(f'teslaEV_GetName - No EV name found - {e}')
            return(None)


    def teslaEV_GetInfo(self, EVid):
        if EVid in self.carInfo:

            logging.debug(f'teslaEV_GetInfo {EVid}: {self.carInfo[EVid]}')
            return(self.carInfo[EVid])
        else:
            return(None)


    def teslaEV_GetLocation(self, EVid):
        try:
            temp = {}
            temp['longitude'] = None
            temp['latitude'] = None
            logging.debug('teslaEV_GetLocation: {} for {}'.format(EVid,self.carInfo[EVid]['drive_state'] ))
            if 'longitude' in self.carInfo[EVid]['drive_state']:
                temp['longitude'] = self.carInfo[EVid]['drive_state']['longitude']
                temp['latitude'] = self.carInfo[EVid]['drive_state']['latitude']
            elif 'active_route_longitude'in self.carInfo[EVid]['drive_state']:
                temp['longitude'] = self.carInfo[EVid]['drive_state']['active_route_longitude']
                temp['latitude'] = self.carInfo[EVid]['drive_state']['active_route_latitude']                
            return(temp)
        except Exception as e:
            logging.error(f'teslaEV_GetLocation - location error')
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

####################
# Charge Data
####################


    def teslaEV_GetChargeTimestamp(self, EVid):
        try:
            return(self.carInfo['charge_state']['timestamp'])
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetChargeTimestamp - {e}')
            return(None)


    def teslaEV_GetIdelBatteryRange(self, EVid):
        try:
            if 'ideal_battery_range' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['ideal_battery_range'],2))
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetIdelBatteryRange - {e}')
            return(None)



    def teslaEV_charge_current_request_max(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'charge_current_request_max' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charge_current_request_max'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_charge_current_request_max - {e}')
            return(None)            

    def teslaEV_charge_current_request(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'charge_current_request' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charge_current_request'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_charge_current_request - {e}')
            return(None)            
            

    def teslaEV_charger_actual_current(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'charger_actual_current' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charger_actual_current'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_charger_actual_current - {e}')
            return(None)              

    def teslaEV_charge_amps(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'charge_amps' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charge_amps'],1)) 
            else:
                return(None)      
        except Exception as e:
            logging.debug(f'Exception teslaEV_charge_amps - {e}')
            return(None)         

    def teslaEV_time_to_full_charge(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'time_to_full_charge' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['time_to_full_charge']*60,0)) 
            else:
                return(None)            
        except Exception as e:
            logging.debug(f'Exception teslaEV_time_to_full_charge - {e}')
            return(None)         
        
    def teslaEV_charge_energy_added(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'charge_energy_added' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charge_energy_added'],1)) 
            else:
                return(None)  
        except Exception as e:
            logging.debug(f'Exception teslaEV_charge_energy_added - {e}')
            return(None)                        

    def teslaEV_charge_miles_added_rated(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'time_to_full_charge' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charge_miles_added_rated'],1)) 
            else:
                return(None)            
        except Exception as e:
            logging.debug(f'Exception teslaEV_charge_miles_added_rated - {e}')
            return(None)                        

    def teslaEV_charger_voltage(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'charger_voltage' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charger_voltage'],0)) 
            else:
                return(None)       
        except Exception as e:
            logging.debug(f'Exception teslaEV_charger_voltage - {e}')
            return(None)                  

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
        try:
            return(self.carInfo[EVid]['charge_state']['fast_charger_present'])
        except Exception as e:
            logging.debug(f'Exception teslaEV_FastChargerPresent - {e}')
            return(None)  
  
    def teslaEV_ChargePortOpen(self, EVid):
        #logging.debug(f'teslaEV_ChargePortOpen for {EVid}')
        try:
            return(self.carInfo[EVid]['charge_state']['charge_port_door_open']) 
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargePortOpen - {e}')
            return(None)  

    def teslaEV_ChargePortLatched(self, EVid):
        #logging.debug(f'teslaEV_ChargePortOpen for {EVid}')
        try:
            return(self.carInfo[EVid]['charge_state']['charge_port_latch']) 
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargePortLatched - {e}')
            return(None)  
        
    def teslaEV_GetBatteryRange(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'battery_range' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['battery_range'],0)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetBatteryRange - {e}')
            return(None)  
        
    def teslaEV_GetBatteryLevel(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryLevel for {EVid}')
            if 'battery_level' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['battery_level'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetBatteryLevel - {e}')
            return(None)  
        
    def teslaEV_MaxChargeCurrent(self, EVid):
        #logging.debug(f'teslaEV_MaxChargeCurrent for {EVid}')
        try:
            return( self.carInfo[EVid]['charge_state']['charge_current_request_max'])             
        except Exception as e:
            logging.debug(f'Exception teslaEV_MaxChargeCurrent - {e}')
            return(None)       

    def teslaEV_ChargeState(self, EVid):
        #logging.debug(f'teslaEV_GetChargingState for {EVid}')
        try:
            return( self.carInfo[EVid]['charge_state']['charging_state'])  
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargeState - {e}')
            return(None)     
        
    def teslaEV_ChargingRequested(self, EVid):
        #logging.debug(f'teslaEV_ChargingRequested for {EVid}')
        try:
            return(  self.carInfo[EVid]['charge_state']['charge_enable_request'])  
        except Exception as e:
            logging.debug(f'Exception teslaEV_ChargingRequested - {e}')
            return(None)  
    
    def teslaEV_GetChargingPower(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetChargingPower for {EVid}')
            if 'charger_power' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charger_power'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetChargingPower - {e}')
            return(None)              

    def teslaEV_GetBatteryMaxCharge(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetBatteryMaxCharge for {EVid}')
            if 'charge_limit_soc' in self.carInfo[EVid]['charge_state']:
                return(round(self.carInfo[EVid]['charge_state']['charge_limit_soc'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f'Exception teslaEV_GetBatteryMaxCharge - {e}')
            return(None)              
           
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
            logging.error(f'Exception teslaEV_ChargePort for vehicle id {EVid}: {e}')
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
            logging.error(f'Exception teslaEV_AteslaEV_ChargingutoCondition for vehicle id {EVid}: {e}')
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
            logging.error(f'Exception teslaEV_SetChargeLimit for vehicle id {EVid}: {e}')      
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
            logging.error(f'Exception teslaEV_SetChargeLimitAmps for vehicle id {EVid}: {e}')

            
            return('error', e)




####################
# Climate Data
####################


    def teslaEV_GetClimateTimestamp(self, EVid):
        try:
            return(self.carInfo[EVid]['climate_state']['timestamp'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetClimateTimestamp - {e}')
            return(None)

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

    def teslaEV_GetCabinTemp(self, EVid):
        try:
            logging.debug('teslaEV_GetCabinTemp for {} - {}'.format(EVid, self.carInfo[EVid]['climate_state']['inside_temp'] ))
            if 'inside_temp' in self.carInfo[EVid]['climate_state']:
                return(round(self.carInfo[EVid]['climate_state']['inside_temp'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetCabinTemp - {e}')
            return(None)
        
    def teslaEV_GetOutdoorTemp(self, EVid):
        try:
            logging.debug('teslaEV_GetOutdoorTemp for {} = {}'.format(EVid, self.carInfo[EVid]['climate_state']['outside_temp']))
            if 'outside_temp' in self.carInfo[EVid]['climate_state']:
                return(round(self.carInfo[EVid]['climate_state']['outside_temp'],1)) 
            else:
                return(None)
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetOutdoorTemp - {e}')
            return(None)
        
    def teslaEV_GetLeftTemp(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetLeftTemp for {EVid}')
            if 'driver_temp_setting' in self.carInfo[EVid]['climate_state']:
                return(round(self.carInfo[EVid]['climate_state']['driver_temp_setting'],1))   
            else:
                return(None) 
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetLeftTemp - {e}')
            return(None)            

    def teslaEV_GetRightTemp(self, EVid):
        try:
            #logging.debug(f'teslaEV_GetRightTemp for {EVid}')
            if 'passenger_temp_setting' in self.carInfo[EVid]['climate_state']:
                return(round(self.carInfo[EVid]['climate_state']['passenger_temp_setting'],1))   
            else:
                return(None)
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetRightTemp - {e}')
            return(None)            

    def teslaEV_GetSeatHeating(self, EVid):
        try:
        #logging.debug(f'teslaEV_GetSeatHeating for {EVid}')
            temp = {}
            if 'seat_heater_left' in self.carInfo[EVid]['climate_state']:
                temp['FrontLeft'] = self.carInfo[EVid]['climate_state']['seat_heater_left']
            if 'seat_heater_right' in self.carInfo[EVid]['climate_state']:
                temp['FrontRight'] = self.carInfo[EVid]['climate_state']['seat_heater_right']   
            if 'seat_heater_rear_left' in self.carInfo[EVid]['climate_state']:
                temp['RearLeft'] = self.carInfo[EVid]['climate_state']['seat_heater_rear_left']   
            if 'seat_heater_rear_center' in self.carInfo[EVid]['climate_state']:
                temp['RearMiddle'] = self.carInfo[EVid]['climate_state']['seat_heater_rear_center']           
            if 'seat_heater_rear_right' in self.carInfo[EVid]['climate_state']:
                temp['RearRight'] = self.carInfo[EVid]['climate_state']['seat_heater_rear_right']           
            return(temp)
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetSeatHeating - {e}')
            return(temp)            
 

    def teslaEV_AutoConditioningRunning(self, EVid):
        try:

            return( self.carInfo[EVid]['climate_state']['is_auto_conditioning_on']) 
        except Exception as e:
            logging.debug(f' Exception teslaEV_AutoConditioningRunning - {e}')
            return(None)      

    def teslaEV_PreConditioningEnabled(self, EVid):
        #logging.debug(f'teslaEV_PreConditioningEnabled for {EVid}')
        try:
            return(self.carInfo[EVid]['climate_state']['is_preconditioning'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_PreConditioningEnabled - {e}')
            return(None)      

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
        
    def teslaEV_SteeringWheelHeatOn(self, EVid):
        #logging.debug(f'teslaEV_SteeringWheelHeatOn for {EVid}')
        try:
            return(self.carInfo[EVid]['climate_state']['steering_wheel_heater'])         
        except Exception as e:
            logging.error(f'teslaEV_SteeringWheelHeatOn Exception : {e}')
            return(None)

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
            logging.error(f'Exception teslaEV_Windows for vehicle id {EVid}: {e}')       
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
            logging.error(f'Exception teslaEV_SunRoof for vehicle id {EVid}: {e}')            
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
            logging.error(f'Exception teslaEV_AutoCondition for vehicle id {EVid}: {e}')
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
            logging.error(f'Exception teslaEV_SetCabinTemps for vehicle id {EVid}: {e}')
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
            logging.error(f'Exception teslaEV_DefrostMax for vehicle id {EVid}: {e}')

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
                if int(levelHeat) > 3 or int(levelHeat) < 0:
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
            logging.error(f'Exception teslaEV_SetSeatHeating for vehicle id {EVid}: {e}')
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
            logging.error(f'Exception teslaEV_SteeringWheelHeat for vehicle id {EVid}: {e}')
            return('error', e)

####################
# Status Data
####################
  
    def teslaEV_GetCenterDisplay(self, EVid):

        #logging.debug(f'teslaEV_GetCenterDisplay: for {EVid}')

        try:
            return(self.carInfo[EVid]['vehicle_state']['center_display_state'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetCenterDisplay - {e}')
            return(None)

    def teslaEV_GetStatusTimestamp(self, EVid):
        try:
            return(self.carInfo[EVid]['vehicle_state']['timestamp'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetStatusTimestamp - {e}')
            return(None)

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

    def teslaEV_HomeLinkNearby(self, EVid):
        #logging.debug(f'teslaEV_HomeLinkNearby: for {EVid}')
        try:
            return(self.carInfo[EVid]['vehicle_state']['homelink_nearby'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_HomeLinkNearby - {e}')
            return(None)

    def teslaEV_nbrHomeLink(self, EVid):
        logging.debug(f'teslaEV_nbrHomeLink: for {EVid}')
        try:
            return(self.carInfo[EVid]['vehicle_state']['homelink_device_count'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_nbrHomeLink - {e}')
            return(None)

    def teslaEV_GetLockState(self, EVid):
        #logging.debug(f'teslaEV_GetLockState: for {EVid}')
        try:
            return(self.carInfo[EVid]['vehicle_state']['locked'])
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetLockState - {e}')
            return(None)
    def teslaEV_GetWindoStates(self, EVid):
        #logging.debug(f'teslaEV_GetWindoStates: for {EVid}')
        try:
            temp = {}
            if 'fd_window' in self.carInfo[EVid]['vehicle_state']:
                temp['FrontLeft'] = self.carInfo[EVid]['vehicle_state']['fd_window']
            else:
                temp['FrontLeft'] = None
            if 'fp_window' in self.carInfo[EVid]['vehicle_state']:
                temp['FrontRight'] = self.carInfo[EVid]['vehicle_state']['fp_window']
            else:
                temp['FrontRight'] = None
            if 'rd_window' in self.carInfo[EVid]['vehicle_state']:
                temp['RearLeft'] = self.carInfo[EVid]['vehicle_state']['rd_window']
            else:
                temp['RearLeft'] = None
            if 'rp_window' in self.carInfo[EVid]['vehicle_state']:
                temp['RearRight'] = self.carInfo[EVid]['vehicle_state']['rp_window']
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
            if 'odometer' in self.carInfo[EVid]['vehicle_state']:
                return(round(self.carInfo[EVid]['vehicle_state']['odometer'], 2))
            else:
                return(0.0)
        except Exception as e:
            logging.debug(f' Exception teslaEV_GetOdometer - {e}')
            return(None)
        

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

    def teslaEV_GetTrunkState(self, EVid):
        #logging.debug(f'teslaEV_GetTrunkState: for {EVid}')
        try:
            if self.carInfo[EVid]['vehicle_state']['rt'] == 0:
                return(0)
            elif self.carInfo[EVid]['vehicle_state']['rt'] == 1:
                return(1)
            else:
                return(None)
        except Exception as e:
            logging.error(f'teslaEV_GetTrunkState Excaption: {e}')
            return(None)

    def teslaEV_GetFrunkState(self, EVid):
        #logging.debug(f'teslaEV_GetFrunkState: for {EVid}')
        try:
            if self.carInfo[EVid]['vehicle_state']['ft'] == 0:
                return(0)
            elif self.carInfo[EVid]['vehicle_state']['ft'] == 1:
                return(1)
            else:
                return(None)
        except Exception as e:
            logging.error(f'teslaEV_GetFrunkState Excaption: {e}')
            return(None)
        

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
            logging.error(f'Exception teslaEV_FlashLight for vehicle id {EVid}: {e}')
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
            logging.error(f'Exception teslaEV_HonkHorn for vehicle id {EVid}: {e}')           
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
            logging.error(f'Exception teslaEV_PlaySound for vehicle id {EVid}: {e}')
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
            logging.error(f'Trying to reconnect')            
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
            logging.error(f'Exception teslaEV_TrunkFrunk for vehicle id {EVid}: {e}')
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
            logging.error(f'Exception teslaEV_HomeLink for vehicle id {EVid}: {e}')
       
            return('error', e)

