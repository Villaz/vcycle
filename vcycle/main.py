__author__ = 'Luis Villazon Esteban'

import multiprocessing
import logging
import os
import time
import threading
import argparse
try:
    import configuration
    import vcycle
    from db import capped
except Exception:
    import vcycle.configuration as configuration
    import vcycle.vcycle as vcycle
    from vcycle.db import capped as capped

from pymongo import MongoClient


db = None
collection_name = None
capped_name = None
configuration_file = None
connectors = {}
queue = multiprocessing.Queue()
processes = {}
locks = {}


def start_process(conf=u'/etc/vcycle/vcycle.conf'):
    global db, configuration_file, connectors, queue, processes, locks, capped_name, collection_name

    configuration_file = configuration.load(path=conf, logger=get_log())

    database_name = configuration_file['vcycle']['db']['mongo']['database']
    collection_name = configuration_file['vcycle']['db']['mongo']['collection']
    capped_name = configuration_file['vcycle']['db']['mongo']['capped_collection']
    client = MongoClient(configuration_file['vcycle']['db']['mongo']['url'])
    db = client[database_name][collection_name]

    # Create the connector objects
    load_connectors()
    create_locks()

    if capped_name not in client[database_name].collection_names():
        client[database_name].create_collection(capped_name, capped=True, size=2**20, autoIndexId=False)
        client[database_name][capped_name].insert_one({'site': '',
                                                       'experiment': '',
                                                       'hostname': '',
                                                       'state': '',
                                                       'time': -1})
    capped_collection = client[database_name][capped_name]

    for experiment in configuration_file['vcycle']['experiments']:
        for site in configuration_file['vcycle']['experiments'][experiment]['sites']:
            multiprocessing.Process(target=capped.start_listen, args=(capped_collection,
                                                                      queue,
                                                                      site,
                                                                      experiment,
                                                                      get_log("db", "db")))\
                .start()
    multiprocessing.Process(target=process_queue).start()
    multiprocessing.Process(target=do_cycle).start()



def load_connectors():
    global connectors
    for connector in configuration_file['vcycle']['connectors']:
        type = configuration_file['vcycle']['connectors'][connector]['type']
        try:
            module = __import__("connectors."+type)
            class_ = getattr(module, type)
        except ImportError:
            try:
                module = __import__("connectors.%s_connector" % type)
                class_ = getattr(module, "%s_connector" % type)
            except ImportError:
                try:
                    module = __import__("vcycle.connectors.%s" % type)
                    mod = getattr(module, 'connectors')
                    class_ = getattr(mod, type)
                except ImportError:
                    module = __import__("vcycle.connectors.%s_connector" % type)
                    mod = getattr(module, 'connectors')
                    class_ = getattr(mod, "%s_connector" % type)

        connectors[connector] = class_.create(**configuration_file['vcycle']['connectors'][connector])


def create_locks():
    global locks
    for experiment in configuration_file['vcycle']['experiments']:
        locks[experiment] = {}
        for site in configuration_file['vcycle']['experiments'][experiment]['sites']:
            locks[experiment][site] = multiprocessing.Lock()


def process_queue():

    while True:
        try:
            message = queue.get()
            get_log('server', 'server').info("Received message %s from %s", message['state'], message['hostname'])
            if 'state' in message and message['state'] in ['BOOT', 'END']:
                process_queue_message(message)
        except Exception as e:
            get_log().error(e.message)
            pass


def process_queue_message(message):
        global locks
        site = message['site']
        experiment = message['experiment']
        locks[experiment][site].acquire()
        if message['state'] == 'END':
            multiprocessing.Process(target=create_client, args=(site, experiment, message['hostname'], True, False,)).start()
        else:
            multiprocessing.Process(target=create_client, args=(site, experiment, None, False, True,)).start()


def do_cycle():
    global locks
    while True:
        for experiment in locks:
            for site in locks[experiment]:
                # If the thread didn't finish in 3 minutes, something is wrong and the thread is deleted
                key = "%s:%s" % (experiment.upper(), site.upper())
                if key in processes and processes[key]['process'].is_alive():
                    get_log(site, experiment).warn("Terminating process %s %s", site, experiment)
                    processes["%s:%s" % (experiment.upper(), site.upper())]['process'].terminate()
                    locks[experiment][site].release()
                locks[experiment][site].acquire()
                multiprocessing.Process(target=create_client, args=(site, experiment)).start()
        if 'params' in configuration_file and 'time_cycle' in configuration_file:
            time.sleep(int(configuration_file['params']['time_cycle']))
        else:
            time.sleep(3*60)


def create_client(site, experiment, hostname=None, delete=False, multiple=False):
    global locks
    connector = connectors[configuration_file['vcycle']['experiments'][experiment]['sites'][site]['connector']]
    cycle = vcycle.Cycle(client=connector,
                         db=db,
                         collection=collection_name,
                         capped=capped_name,
                         site=site,
                         experiment=experiment,
                         params=configuration_file['vcycle']['experiments'][experiment]['sites'][site],
                         logger=get_log(site, experiment))
    if delete:
        process = multiprocessing.Process(target=cycle.delete, args=(hostname,))
    if multiple:
        process = multiprocessing.Process(target=cycle.create)
    else:
        process = multiprocessing.Process(target=cycle.iterate)
    process.start()
    process.join(60)
    if process.is_alive():
        process.terminate()
    locks[experiment][site].release()


def get_log(site="server", experiment="server"):
    from datetime import date
    try:
        os.makedirs("/var/log/vcycle/%s/" % experiment)
    except OSError:
        pass
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("%s:%s" %(site,experiment))
    if len(logger.handlers) == 0:
        try:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler = logging.FileHandler("/var/log/vcycle/%s/%s-%s.log" % (experiment, site, date.today().strftime('%d%m%Y')))
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        except IOError as e:
            print str(e)
    return logger

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conf", nargs='?', default=u"/etc/vcycle/vcycle.conf", help="Path to configuration file")

    args = parser.parse_args()

    start_process()

