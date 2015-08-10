__author__ = 'luis'
from pymongo import MongoClient
from pymongo.cursor import CursorType
import time
#import zmq
import multiprocessing
import json




def last_value(collection):
    global last_id
    try:
        cur = collection.find({}).sort('$natural',-1).limit(1)[0]
        return cur['_id']
    except IndexError,e:
        print e
        return  -1


def get_cursor(collection, last_id):
    return collection.find({'_id': {'$gt': last_id}}, cursor_type=CursorType.EXHAUST).sort('$natural', -1)


#port = "5556"
#context = zmq.Context()
#socket = context.socket(zmq.PUB)
#socket.bind("tcp://*:%s" % port)

def start_listen(collection, queue):
    last_id = last_value(collection)
    while True:
        try:
            cur = get_cursor(collection, last_id)
            for msg in cur:
                last_id = msg['_id']
                msg.pop('_id', None)
                queue.put(msg)
            time.sleep(0.1)
        except Exception as e:
            print str(e)


#queue = multiprocessing.Queue()
#multiprocessing.Process(target=start_listen, args=(queue,)).start()
#multiprocessing.Process(target=insert).start()
#while True:
#    print "Received " + json.dumps(queue.get())