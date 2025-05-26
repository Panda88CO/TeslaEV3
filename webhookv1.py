#!/usr/bin/env python3


import json


try:
    import udi_interface
    logging = udi_interface.LOGGER
    #logging = getlogger('yolink_init_V2')
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

def init_message(self):
    logging.debug('Init Message system')
    self.messageQueue = Queue()



def process_message(self):
    try:
        #self.messageLock.acquire()
        data = self.messageQueue.get(timeout = 10) 
        logging.debug('Received message - Q size={}'.format(self.messageQueue.qsize()))

        evID = self.TEVcloud.teslaEV_stream_get_id(data)
        logging.debug(f'EVid in data = {evID}')
        #if evID in self.EVid:
        self.TEVcloud.teslaEV_stream_process_data(data)
        if self.subnodesReady():            
            self.update_all_drivers()
      

    except Exception as e:
        logging.debug('message processing timeout - no new commands') 
        pass
        #self.messageLock.release()

    #@measure_time
def insert_message(self, msg):
    """
    Callback for broker published events
    """
    logging.debug('on_message: {}'.format(json.loads(msg.payload.decode("utf-8"))) )
    self.messageQueue.put(msg)
    qsize = self.messageQueue.qsize()
    logging.debug('Message received and put in queue (size : {})'.format(qsize))
    logging.debug('Creating threads to handle the received messages')
    threads = []
    for idx in range(0, qsize):
        threads.append(Thread(target = self.process_message ))
    [t.start() for t in threads]
    logging.debug('{} on_message threads starting'.format(qsize))