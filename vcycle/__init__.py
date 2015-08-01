__author__ = 'Luis Villazon Esteban'

from multiprocessing import Queue, Lock, Process
import logging
import os
import time

from pymongo import MongoClient

from vcycle import configuration
import vcycle


class Launcher:

    collection = None
    capped_collection = None
    configuration = None
    connectors = {}
    queue = Queue()
    processes = {}
    locks = {}

    def start(self, conf=u'/etc/vcycle/vcycle.conf'):
        self.configuration = configuration.load(path=conf, logger=Launcher.get_log())
        client = MongoClient(self.configuration['vcycle']['db']['mongo']['url'])
        self.collection = client.infinity.computer_test
        self.load_connectors()

        if 'capped_servers' not in client.infinity.collection_names():
            self.db.create_collection('capped_servers', capped=True, size=2**20, autoIndexId=False)
            self.capped_collection = client.infinity.capped_servers

        # Create the clients
        for experiment in self.configuration['vcycle']['experiments']:
            for site in self.configuration['vcycle']['experiments'][experiment]['sites']:
                self.locks["%s:%s" % (experiment.upper(), site.upper())] = Lock()
        #Process(target=capped.start_listen, args=(self.capped_collection, self.queue,)).start()
        Process(target=self.process_queue).start()
        #self.do_cycle()


    def load_connectors(self):
        for connector in self.configuration['vcycle']['connectors']:
            type = self.configuration['vcycle']['connectors'][connector]['type']
            try:
                module = __import__("connectors."+type)
                class_ = getattr(module, type)
            except ImportError:
                module = __import__("connectors.%s_connector" % type)
                class_ = getattr(module, "%s_connector" % type)
            self.connectors[connector] = class_.create(**self.configuration['vcycle']['connectors'][connector])

    def process_queue(self):
        def process(message):
            site = message['site']
            experiment = message['experiment']
            if message['state'] == 'END':
                self.create_client(site, experiment, hostname=message['hostname'], delete=True)
            else:
                self.create_client(site, experiment, multiple=True)

        while True:
            try:
                message = self.queue.get()
                if 'state' in message and message['state'] in ['BOOT', 'END']:
                    Launcher.get_log().info("Received message %s from %s", message['state'], message['hostname'])
                    process = Process(target=process, args=(message,))
                    process.start()
            except Exception,e:
                Launcher.get_log().error(e.message)

    def do_cycle(self):
        while True:
            for lock in self.locks:
                # If the thread didn't finish in 3 minutes, something is wrong and the thread is deleted
                experiment, site = lock.split(":")
                key = "%s:%s" % (experiment.upper(), site.upper())
                if key in self.processes and self.processes[key]['process'].is_alive():
                    Launcher.get_log().warn("Terminating process %s %s", site, experiment)
                    self.processes["%s:%s" % (experiment.upper(), site.upper())]['process'].terminate()
                    self.locks[lock].release()
                process = Process(target=self.create_client, args=(site, experiment))
                process.start()
                self.processes["%s:%s" % (experiment, site)] = {'process': process}
            time.sleep(10*60)

    def create_client(self, site, experiment, hostname=None, multiple=True, delete=False):
        lock_key = "%s:%s" % (experiment.upper(), site.upper())
        self.locks[lock_key].acquire()
        Launcher.get_log().debug("Adquired lock %s", lock_key)
        connector = self.connectors[self.configuration['vcycle']['experiments'][experiment]['sites'][site]['connector']]
        cycle = vcycle.Cycle(client=connector,
                             db=self.db,
                             site=site,
                             experiment=experiment,
                             params=self.configuration['vcycle']['experiments'][experiment]['sites'][site],
                             logger=Launcher.get_log(site, experiment))
        if delete:
            cycle.delete(hostname)
        if not multiple:
            cycle.iterate()
        else:
            cycle.create()
        self.locks[lock_key].release()
        Launcher.get_log().debug("Released lock %s", lock_key)



    @staticmethod
    def get_log(site="server", experiment="server"):
        from datetime import date
        try:
            os.mkdir("/var/log/vcycle/%s/" % experiment)
        except OSError:
            print "Error creating log path"

        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(site)

        if len(logger.handlers) == 0:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler = logging.FileHandler("/var/log/vcycle/%s/%s-%s.log" % (experiment, site, date.today().strftime('%d%m%Y')))
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger


if __name__ == '__main__':
    l = Launcher()
    l.start(conf=u'../conf/infinity.conf')
