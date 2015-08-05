__author__ = 'luis'

import json
import requests
import inspect
import uuid
import moment
import copy
from conditions import DeleteBase
from connectors import CloudException
from jinja2 import Environment, PackageLoader , FileSystemLoader


class Cycle:
    """Vcycle Class

    Cycle has all the functionality to create, delete and list all VMs deployed in one provider.
    The class take the information from a DB and from the provider, mergers then and making decisions
    based on these knowledgment

    """
    def __init__(self, client=None, db=None, site=None, experiment=None, params=None, logger=None):
        """ Init function

        Initialize a new instance of Cycle.
        The field params has all the information needed to manage the VMs in the provider.

        :param client: client uses to communicate with the provider
        :param db: Object uses to communicate with the database
        :param site: Name of the site to interact with VMs
        :param experiment: Name of the experiment to interact with VMs
        :param params: dictionary of parameters. Contains all the necesary information to create a new VM
        :param params.prefix: Prefix uses to manage the VMs, the VMs will have the name "prefix-xxxxx".
        :param params.flavor: Flavor uses to create the VM
        :param params.image: Image uses to create the VM
        :param params.user_data: script to contextualize the VM
        :param params.max_machines: Number of the max machines to deploy in the provider
        :param logger:
         """
        self.client = client
        self.db = db
        self.site = site
        self.experiment = experiment
        self.params = params
        self.logger = logger

    def iterate(self):
        """ Starts a new iteration of the cycle.

        The iteration first print a list of all VMs deployed in the provider, with their state.
        After that the function will evaluate the state of each VM and will decide witch one will be deleted from provider.
        Ones the deletion has finished, the function checks if the condition is optimal to create a new or a group
        of new VMs

         """
        self.list()

        try:
            self.logger.debug("Listing VMs from provider")
            list_vms_provider = self.client.list(self.params['prefix'])
            self.logger.debug("Ended listing VMs from provider")
        except Exception, e:
            if self.logger is not None:
                self.logger.error(e.message)
            return

        DeleteBase.execute(list_vms_provider,
                           collection=self.db,
                           site=self.site,
                           experiment=self.experiment,
                           client=self.client,
                           info=self.params,
                           logger=self.logger)

        if not self.__machines_executing_or_only_one_machine_not_started() and \
               self.__deployed_machines_less_than_maximum():
            self.__create_vm()
            
    def create(self, created=0):
        """Creates a new or group of new VMs

            Check the conditions to create a new VM. If there are no VMs deployed in the provider, a new VM will be
            created.
            If there are more VMs , a new VM always will be create unless there is only one VM and this VM is not
            executing a job yet, or the number of VMs is equal to the maximum allowed.

        :param created: Number of vms created by the iterator. On each iteration a maximum of 5 vms are created.

        """
        if not self.__conditions_to_create(created):
            return
        try:
            self.__create_vm()
            self.create(created + 1)
        except Exception,e:
            self.logger.error(e.message) if self.logger is not None else False

    def __create_vm(self):
        """ Create a new VM

            Parse all parameters, create the final user_data from the template and send the request to the provider.
            Ones the provider responses, the information of the created VM is stored in DB.

        """
        params_to_create = copy.deepcopy(self.params)

        params_to_create['hostname'] = params_to_create['id'] = "%s-%s" % (self.params['prefix'], str(int(moment.now().epoch())))
        try:
            params_to_create['host'], params_to_create['ganglia_port'] = self.__ganglia_port()
        except:
            pass
        params_to_create['site'] = self.site
        if 'experiment' in params_to_create:
            params_to_create[params_to_create['experiment']] = True
        params_to_create['experiment'] = self.experiment

        # If user_data starts with #! is a script not name template
        if '#!' not in params_to_create['user_data']:
            try:
                env = Environment(loader=FileSystemLoader('/etc/vcycle/contextualization'))
            except Exception as e:
                self.logger.error(str(e))
                return
            #env = Environment(loader=PackageLoader('contextualization', ''))
            template = env.get_template(params_to_create['user_data'])
            params_to_create['user_data'] = template.render(params_to_create)
            #open("../tmp/%s" % str(uuid.uuid4()), 'w').write(params_to_create['user_data'])

        params_to_create['logger'] = self.logger if self.logger is not None else False

        try:
            server = self.client.create(**params_to_create)
            self.db.insert({'id': server['id'],
                            'hostname': server['hostname'],
                            'state': server['state'],
                            'site': self.site,
                            'experiment': self.experiment,
                            'createdTime': int(moment.now().epoch())})
            self.logger.info(" VM %s has been created", server['hostname']) if self.logger is not None else False
        except CloudException as ex:
            self.logger.error(str(ex))

    def list(self):
        """ List all VMs deployed in the provider

        """
        cur = self.db.find({'site': self.site, 'experiment': self.experiment, 'state': {'$nin': ['DELETED']}})
        states = {'ERROR': 0, 'CREATING': 0, 'BOOTED': 0, 'STARTED': 0, 'ENDED': 0}
        for computer in cur:
            self.logger.info("%s\t%s" % (computer['hostname'], computer['state'])) if self.logger is not None else False
            states[computer['state']] += 1
        if self.logger is not None:
            self.logger.info("CREATING: %s ; BOOTED: %s ; STARTED: %s ; ERROR: %s ; ENDED: %s" % (states['CREATING'],
                                                                                     states['BOOTED'],
                                                                                     states['STARTED'],
                                                                                     states['ERROR'],
                                                                                     states['ENDED']))

    def delete(self, hostname):
        """ Delete a VM

        :param hostname: hostname of the VM to delete

        """
        try:
            identifier = self.db.find_one({'hostname': hostname})['id']
            self.client.delete(identifier)
            self.db.find_one_and_update({'id':identifier},
                                    {'$set': {'state': 'DELETED'}})
            self.logger.info("DELETED VM %s with state ENDED", identifier) if self.logger is not None else False
        except Exception,e:
            self.logger.error(e.message) if self.logger is not None else False

    def __conditions_to_create(self, created=0):
        """Check the conditions to create a new VM

        A new vm will be created if the number of VMs created in the cycle are less than 5 or the number of VMs is
        more than one, or is one and this one is executing a job.

        :param created: Number of vms created in the cycle
        :return: True if a VM can be created. False if not
        """
        if created >= 5:
            self.logger.info("Thread has created 5 machines, The thread will end") if self.logger is not None else False
            return False

        if self.__machines_executing_or_only_one_machine_not_started():
            return False

        return self.__deployed_machines_less_than_maximum()

    def __machines_executing_or_only_one_machine_not_started(self):
        """  Check if a new VM can be created

        :return: True if there are only one machine in the provider and this one is not executing a job.
        """
        cursor = self.db.aggregate([{'$match': {'site': self.site, 'experiment': self.experiment,
                                    'state': {'$nin': ['DELETED', 'ENDED', 'ERROR']}}},
                         {'$group': {'_id': {'site': "$site", 'experiment': "$experiment", 'state': "$state"},
                          'count': {'$sum': 1}}}])
        values = {}
        total = 0
        for value in cursor:
            values[value['_id']['state']] = value['count']
            total += value['count']

        if total == 1 and 'CREATING' in values and values['CREATING'] == 1:
            if self.logger is not None:
                self.logger.info("One machine deployed but NOT STARTED yet")
            return True
        return False


    def __deployed_machines_less_than_maximum(self):
        """ Check if a VM can be created

        :return: True if the total of VMs deployed in the provider is less than the maximum allowed
        """
        val = self.db.find({'site': self.site,
                           'experiment': self.experiment,
                           'state': {'$in': ['CREATING', 'BOOTED', 'STARTED']}}).count()

        if int(val) < int(self.params['max_machines']):
            if self.logger is not None:
                self.logger.info("Number of VM %s is less than %s ; new VMs will be created" % (val, self.params['max_machines']))
            return True
        if self.logger is not None:
            self.logger.info("Number of VM %s is equal or higher than %s ; no create more VMs" % (val, self.params['max_machines']))
        return False

    def __ganglia_port(self):
        """ Returns the ganglia port used to monitorize the VM

        This method is only uses if ganglia is used to monitorize the behaviour of the VMs.
        In case the user use ganglia, this function makes a petition to ganglia server to retrieve the port where
        the VM will send the information

        :return: A list with the host and port to connect
        """
        ganglia_conf = self.params['ganglia']['conf']
        response = requests.get(ganglia_conf)
        text = response.text.replace(u"\xe2", "\"").replace(u'\xc3', '').upper()
        ganglia = json.loads(text)
        if self.site.upper() in ganglia:
            return self.params['ganglia']['host'], ganglia[self.site.upper()]['PORT']









