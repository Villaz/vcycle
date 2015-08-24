__author__ = 'luis'
from pymongo import MongoClient
from pymongo.cursor import CursorType
import time
#import zmq
import multiprocessing
import json


def last_value(collection, site , experiment):
    global last_id
    try:
        cur = collection.find({'site': site, 'experiment': experiment}).sort('$natural', -1).limit(1)[0]
        return cur['time']
    except IndexError,e:
        print e
        return -1


def get_cursor(collection, site, experiment, last_id):
    return collection.find({'time': {'$gt': last_id},
                            'site': site,
                            'experiment': experiment,
                            'hostname':{'$nin': ['vcycle-dbce-1438627543']}},
                            cursor_type=CursorType.EXHAUST).sort('$natural', -1)


#port = "5556"
#context = zmq.Context()
#socket = context.socket(zmq.PUB)
#socket.bind("tcp://*:%s" % port)

def start_listen(collection, queue, site, experiment, logger):
    last_id = last_value(collection, site, experiment)
    while True:
        try:
            cur = get_cursor(collection, site, experiment, last_id)
            for msg in cur:
                last_id = msg['time']
                msg.pop('_id', None)
                logger.debug(json.dumps(msg))
                queue.put(msg)
            time.sleep(0.1)
        except Exception as e:
            print str(e)


#queue = multiprocessing.Queue()
#multiprocessing.Process(target=start_listen, args=(queue,)).start()
#multiprocessing.Process(target=insert).start()
#while True:
#    print "Received " + json.dumps(queue.get())