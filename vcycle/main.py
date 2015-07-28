__author__ = 'Luis Villazon Esteban'

from pymongo import MongoClient
import yaml
import multiprocessing
import logging
import os
import vcycle
import time
from db import capped


def parse_params(site, experiment):
    for option in configuration['vcycle']['experiments'][experiment]:
        if option == 'sites':
            continue
        if option == 'ganglia':
            ganglia = configuration['vcycle']['experiments'][experiment]['ganglia']
            configuration['vcycle']['experiments'][experiment]['ganglia'] = configuration['vcycle']['ganglia'][ganglia]
        configuration['vcycle']['experiments'][experiment]['sites'][site][option] = configuration['vcycle']['experiments'][experiment][option]

    configuration['vcycle']['experiments'][experiment]['sites'][site]['db'] = configuration['vcycle']['db']['mongo']['url']
    connector = configuration['vcycle']['experiments'][experiment]['sites'][site]['connector']

    #load files
    for option in configuration['vcycle']['experiments'][experiment]['sites'][site]:
        aux = configuration['vcycle']['experiments'][experiment]['sites'][site]
        if isinstance(aux[option], basestring) and aux[option].startswith('file://'):
            file = aux[option].replace('file://','')
            configuration['vcycle']['experiments'][experiment]['sites'][site][option] = open(file).read()


def load_connectors():
    connectors = {}
    for connector in configuration['vcycle']['connectors']:
        type = configuration['vcycle']['connectors'][connector]['type']
        module = __import__("connectors."+type)
        class_ = getattr(module, type)
        connectors[connector] = class_.create(**configuration['vcycle']['connectors'][connector])
    return connectors


def init_processing(site, experiment):
    connector = connectors[configuration['vcycle']['experiments'][experiment]['sites'][site]['connector']]
    cycle = vcycle.Cycle(client=connector,
                         db=db,
                         site=site,
                         experiment=experiment,
                         params=configuration['vcycle']['experiments'][experiment]['sites'][site],
                         logger=get_log(site, experiment))
    cycle.iterate()


def process_queue(queue, lock):
    while True:
        try:
            message = queue.get()
            if 'state' in message and message['state'] in ['BOOT', 'END']:
                get_log('server', 'server').info("Received message %s from %s", message['state'], message['hostname'])
                site = message['site']
                experiment = message['experiment']

                locks["%s:%s" % (experiment.upper(), site.upper())].acquire()
                connector = connectors[configuration['vcycle']['experiments'][experiment]['sites'][site]['connector']]
                cycle = vcycle.Cycle(client=connector,
                                     db=db,
                                     site=site,
                                     experiment=experiment,
                                     params=configuration['vcycle']['experiments'][experiment]['sites'][site],
                                     logger=get_log(site, experiment))
                if message['state'] == 'END':
                    cycle.delete(message['hostname'])
                cycle.create()
                locks["%s:%s" % (experiment.upper(), site.upper())].release()
        except Exception,e:
            get_log('main','main').error(e.message)
            pass


def do_cycle(processes, locks):
    def init(experiment, site, lock):
        locks[lock].acquire()
        connector = connectors[configuration['vcycle']['experiments'][experiment]['sites'][site]['connector']]
        cycle = vcycle.Cycle(client=connector,
                             db=db,
                             site=site,
                             experiment=experiment,
                             params=configuration['vcycle']['experiments'][experiment]['sites'][site],
                             logger=get_log(site, experiment))
        cycle.iterate()
        locks[lock].release()

    time.sleep(5*60)
    while True:
        for lock in locks:
            #If the thread didn't finish in 3 minutes, something is wrong and the thread is deleted
            experiment, site = lock.split(":")
            if processes["%s:%s" % (experiment.upper(), site.upper())]['process'].is_alive():
                processes["%s:%s" % (experiment.upper(), site.upper())]['process'].terminate()
            process = multiprocessing.Process(target=init, args=(experiment, site, lock,))
            process.start()
            processes["%s:%s" % (experiment, site)]['process'] = process
        time.sleep(5*60)


def get_log(site, experiment):
    from datetime import date
    try:
        os.mkdir("/var/log/vcycle/%s/" % experiment)
    except OSError:
        pass
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(site)
    if len(logger.handlers) == 0:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.FileHandler("%s-%s.log" % (site, date.today().strftime('%d%m%Y')))
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def start_process():
    import threading

    queue = multiprocessing.Queue()
    processes = {}
    locks = {}

    try:
        configuration = yaml.load(open('./conf/infinity.conf'))
    except Exception as ex:
        get_log("server","server").error(str(ex))

    client = MongoClient(configuration['vcycle']['db']['mongo']['url'])
    db = client.infinity.computer_test

    # Create the connector objects
    connectors = load_connectors()

    if 'capped_servers' not in client.infinity.collection_names():
        db.create_collection('capped_servers',capped=True, size=2**20, autoIndexId=False)
    capped_collection = client.infinity.capped_servers

    # Parse configuration File
    for experiment in configuration['vcycle']['experiments']:
        for site in configuration['vcycle']['experiments'][experiment]['sites']:
            parse_params(site, experiment)

    # Create the clients
    for experiment in configuration['vcycle']['experiments']:
        for site in configuration['vcycle']['experiments'][experiment]['sites']:
            process = multiprocessing.Process(target=init_processing, args=(site, experiment))
            process.start()
            processes["%s:%s" % (experiment.upper(), site.upper())] = {'process': process}
            locks["%s:%s" % (experiment.upper(), site.upper())] = threading.Lock()
            pass

    multiprocessing.Process(target=capped.start_listen, args=(capped_collection, queue,)).start()
    multiprocessing.Process(target=process_queue, args=(queue, locks,)).start()
    do_cycle(processes, locks)


if __name__ == "__main__":
    start_process()

