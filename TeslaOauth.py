
#!/usr/bin/env python3

### Your external service class
'''
Your external service class can be named anything you want, and the recommended location would be the lib folder.
It would look like this:

External service sample code
Copyright (C) 2023 Universal Devices

MIT License
'''
import requests
import time
import json
from threading import Lock
from datetime import timedelta, datetime
from tzlocal import get_localzone

try:
    #import udi_interface
    from udi_interface import LOGGER, Custom, OAuth
    logging = LOGGER

#    ISY = udi_interface.ISY
except ImportError:
    import logging
    logging.basicConfig(level=30)


#from udi_interface import logging, Custom, OAuth, ISY
#logging = udi_interface.logging
#Custom = udi_interface.Custom
#ISY = udi_interface.ISY



# Implements the API calls to your external service
# It inherits the OAuth class
class teslaAccess(OAuth):
    #yourApiEndpoint = 'https://fleet-api.prd.na.vn.cloud.tesla.com'
    yourApiEndpoint = 'https://my.isy.io/api/tesla'
    def __init__(self, polyglot, scope):
        super().__init__(polyglot)
        logging.info(f'OAuth initializing')
  
        self.poly = polyglot
        self.scope = scope
        self.EndpointNA= 'https://fleet-api.prd.na.vn.cloud.tesla.com'
        self.EndpointEU= 'https://fleet-api.prd.eu.vn.cloud.tesla.com'
        self.EndpointCN= 'https://fleet-api.prd.cn.vn.cloud.tesla.cn'
        self.api  = '/api/1'
        self.yourPortalEndpoint = 'https://my.isy.io/api/tesla'+self.api
        self.token_info = {}
        self.portal_connected = False
        self.cloud_access_enabled = False
        #self.state = secrets.token_hex(16)
        self.region = ''
        #self.handleCustomParamsDone = False
        #self.customerDataHandlerDone = False
        self.customNsHandlerDone = True
        self.oauthHandlerCalled = False
        self.customDataHandlerDone = False
        self.authendication_done = False
        self.return_codes = ['ok', 'offline', 'overload', 'error', 'unknown']
        self.apiLock = Lock()
        self.temp_unit = 'C'
        #self.poly.subscribe(self.poly.CUSTOMNS, self.customNsHandler)
        #self.poly.subscribe(self.poly.OAUTH, self.oauthHandler)
        self.poly = polyglot
        self.customParams = Custom(polyglot, 'customparams')
        logging.info(f'External service connectivity initialized...')

        #time.sleep(1)

        #while not self.handleCustomParamsDone:
        #    logging.debug(f'Waiting for customParams to complete - getAccessToken')
        #    time.sleep(0.2)
        # self.getAccessToken()
    
    # The OAuth class needs to be hooked to these 3 handlers
    
    def customDataHandler(self, key, data):
        logging.debug(f'customDataHandler called {data}')
        #while not self.handleCustomParamsDone:
        #    logging.debug(f'Waiting for customDataHandler to complete')
        #    time.sleep(1)       
        logging.debug('customDataHandler result: {}'.format(super().customDataHandler(data)))
        self.customDataHandlerDone = True
        logging.debug('customDataHandler Finished')


    def customNsHandler(self, key, data):
        logging.debug(f'customNsHandler called {key} {data}')
        #while not self.customParamsDone():
        #    logging.debug(f'Waiting for customNsHandler to complete')
        #    time.sleep(1)
        #self.updateOauthConfig()
        super().customNsHandler(key, data)
        logging.debug(f'customerNSHandler results: {super().customNsHandler(key, data)}')
        if key == 'oauthTokens': # stored oauthToken values processed
            self.customNsHandlerDone = True
        logging.debug(f'customNsHandler Finished')

    def oauthHandler(self, token):
        logging.debug(f'oauthHandler called')
        super().oauthHandler(token)
        #while not self.customNsDone():
        #    logging.debug(f'Waiting for initilization to complete before oAuth')
        #    time.sleep(5)

        logging.debug(f'oauthHandler result: {super().oauthHandler(token)}')
        self.oauthHandlerCalled = True
        #while not self.authendication_done :
        #time.sleep(2)

        return(True)
    def oauthHandlerRun(self):
        return(self.oauthHandlerCalled)
    def customNsDone(self):
        return(self.customNsHandlerDone)
    
    def customDateDone(self):
        return(self.customDataHandlerDone )



                
    def cloud_set_region(self, region):
        #self.customParameters.load(userParams)


        oauthSettingsUpdate = {}
        #oauthSettingsUpdate['parameters'] = {}
        oauthSettingsUpdate['token_parameters'] = {}
        # Example for a boolean field

        logging.debug(f'region {self.region}')
        oauthSettingsUpdate['scope'] = self.scope 
        oauthSettingsUpdate['auth_endpoint'] = 'https://auth.tesla.com/oauth2/v3/authorize'
        oauthSettingsUpdate['token_endpoint'] = 'https://auth.tesla.com/oauth2/v3/token'
        #oauthSettingsUpdate['redirect_uri'] = 'https://my.isy.io/api/cloudlink/redirect'
        #oauthSettingsUpdate['cloudlink'] = True
        oauthSettingsUpdate['addRedirect'] = True
        #oauthSettingsUpdate['state'] = self.state
        if region.upper() == 'NA':
            endpoint = self.EndpointNA
        elif region.upper() == 'EU':
            endpoint = self.EndpointEU
        elif region.upper() == 'CN':
            endpoint = self.EndpointCN
        else:
            logging.error(f'Unknow region specified {self.region}')
            return
           
        self.yourApiEndpoint = endpoint+self.api 
        oauthSettingsUpdate['token_parameters']['audience'] = endpoint
        
        self.updateOauthSettings(oauthSettingsUpdate)
        #time.sleep(0.1)
        logging.debug(f'getOauthSettings: {self.getOauthSettings()}')
        #logging.debug(f'Updated oAuth config 2: {}'.format(temp))
        #self.handleCustomParamsDone = True
        #self.poly.Notices.clear()



    def authenticated(self):
        #self.apiLock.acquire()
        logging.debug('authenticated : {} {}'.format(self._oauthTokens.get('expiry') != None, self._oauthTokens))
        try:
            if 'expiry' not in self._oauthTokens:            
                self.getAccessToken()
                #time.sleep(2)
            #self.apiLock.release()
            return(self._oauthTokens.get('expiry') != None)
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug(f'_callAPI oauth error: {err}')
            return (False)
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug(f'_callAPI oauth error: {err}')
            return
        #return('expiry' in self._oauthTokens)
 
    def initializePortal(self, client_id, portal_secret):
        self.portalId = client_id
        self.portal_secret = portal_secret
        self.getPortalToken(self.portalId , self.portal_secret)


    def getPortalToken(self, client_id, portal_secret):
        #logging.debug(f'getPortalToken {} {}'.format(client_id, portal_secret))
        token_refresh = True
        now = int(time.time())
        if 'expiry' in self.token_info:
            if now <= self.token_info['expiry'] - 60:
                token_refresh = False
        if token_refresh:
            headers = {
                'Content-Type' :'application/x-www-form-urlencoded',
            }

            body = {
                'grant_type': 'client_credentials',
                'client_id': client_id ,
                'client_secret' : portal_secret,            
            }
            logging.debug(f'Before post header = {headers}, body = {body}')
            response = requests.post('https://my.isy.io/o2/token', headers=headers, data=body)

            if response.status_code == 200:
                self.token_info = response.json()
                self.token_info['expiry'] =  int(time.time()) + self.token_info['expires_in']
                self.portal_connected = True
        if 'access_token' in self.token_info:
            return ( self.token_info['access_token'])
        else:
            return(None)
        
    def portal_ready(self):
        return(self.portal_connected)



    # Call your external service API
    def _callApi(self, method='GET', url=None, body=None):
        # When calling an API, get the access token (it will be refreshed if necessary)
        #self.apiLock.acquire()
        try:
            response = None
            payload = body
            #self._oAuthTokensRefresh()  #force refresh
            accessToken = self.getAccessToken()
            portalToken = self.getPortalToken(self.portalId, self.portal_secret)
            #logging.debug(f'Tokens: P={} T={}'.format(portalToken, accessToken))
            #refresh_token = self._oauthTokens.get('refresh_token')
            #logging.debug(f'call api tokens: {} {}'.format(refresh_token, accessToken))
            self.poly.Notices.clear()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug(f'_callAPI oauth error: {err}')
            return
        if accessToken is None:
            logging.error(f'Access token is not available')
            return None

        if url is None:
            logging.error(f'url is required')
            return None

        completeUrl = self.yourPortalEndpoint + url

        
        headers = {
            #'Content-Type': 'application/json',
            'Authorization': f'Bearer { portalToken }',
            'X-tesla-auth' : accessToken
            
        }

        if method in [ 'PATCH', 'POST']:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer { portalToken }',
                'X-tesla-auth' : accessToken
            }
            if body is None:
                payload = {}
            else:
                #payload = json.dumps(body)
                payload = body

        logging.debug(f' call info url={completeUrl}, header {headers}, body ={payload}')

        try:
            if method == 'GET':
                response = requests.get(completeUrl, headers=headers, json=body)
            elif method == 'DELETE':
                response = requests.delete(completeUrl, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(completeUrl, headers=headers, json=payload)
            elif method == 'POST':
                response = requests.post(completeUrl, headers=headers, json=payload)
            elif method == 'PUT':
                response = requests.put(completeUrl, headers=headers)
            logging.debug(f'request response: {response}')

            
            
            response.raise_for_status()
            if response.status_code == 200:
                try:
                    return 'ok', response.json()
                except requests.exceptions.JSONDecodeError:
                    return 'error', response.text
            elif response.status_code == 400:
                return 'error', response.text
            elif response.status_code == 408:
                return 'offline', response.text
            elif response.status_code == 429:
                return 'overload', response.text
            else:
                return 'unknown', response.text

        except requests.exceptions.HTTPError as error:
            logging.error(f"Call { method } { completeUrl } failed: { error }")
            #self.apiLock.release()
            if response.status_code == 400:
                return('error', response.text)
            else:
                return ('unknown', response.text)
        
    # Call your external service API
    def _callApiORG(self, method='GET', url=None, body=''):
        # When calling an API, get the access token (it will be refreshed if necessary)
        #self.apiLock.acquire()
        try:
            response = None
            accessToken = self.getAccessToken()
            self.poly.Notices.clear()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug(f'_callAPI oauth error: {err}')
            return
        if accessToken is None:
            logging.error(f'Access token is not available')
            return None

        if url is None:
            logging.error(f'url is required')
            return None

        completeUrl = self.yourApiEndpoint + url

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer { accessToken }'
            
        }

        if method in [ 'PATCH', 'POST'] and body is None:
            logging.error(f'body is required when using {method} {completeUrl}')
        logging.debug(f'call info url={completeUrl}, header {headers}, body ={body}')

        try:
            if method == 'GET':
                response = requests.get(completeUrl, headers=headers, json=body)
            elif method == 'DELETE':
                response = requests.delete(completeUrl, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(completeUrl, headers=headers, json=body)
            elif method == 'POST':
                response = requests.post(completeUrl, headers=headers, json=body)
            elif method == 'PUT':
                response = requests.put(completeUrl, headers=headers)
            logging.debug(f'API response: {response}')
            response.raise_for_status()
            #self.apiLock.release()
            
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response.text

        except requests.exceptions.HTTPError as error:
            logging.error(f"Call {method} {completeUrl} failed: {error}")
            #self.apiLock.release()
            return None