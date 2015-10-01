__author__ = 'luis'

import time
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
    def __init__(self, client=None, db=None, site=None, experiment=None, params=None, logger=None, capped=None, collection=None):
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
        self.capped = capped
        self.collection = collection
        self.site = site
        self.experiment = experiment
        self.params = params
        self.logger = logger

    def iterate(self):
        """ Starts a new iteration of the cycle.

        The iteration first print a list of all VMs deployed in the provider, with their state.
        After that the function will evaluate the state of each VM and will decide which one will be deleted from provider.
        Ones the deletion has finished, the function checks if the condition is optimal to create a new or a group
        of new VMs

         """
        states = self.list()

        try:
            self.logger.debug("Listing VMs from provider")
            list_vms_provider = self.client.list(self.params['prefix'])
            self.logger.debug("Provider returns: %s VMs" % len(list_vms_provider))
            self.logger.debug("Ended listing VMs from provider")
        except Exception, e:
            if self.logger is not None:
                self.logger.error(e.message)
            return

        # Sometimes the provider returns a wrong list of VMs
        # To avoid the deletion of good vms, if one machine is deleted in DB but exists in the client
        # the vm will be changed to a valid state.
        # If the machine is not valid will be deleted by heartbeat
        ids = [vm['id'] for vm in list_vms_provider]
        self.db.update_many({'id': {'$in': ids}, 'state': 'DELETED',
                             'boot': {'$exists': True}}, {'$set': {'state': 'BOOTED'}})
        self.db.update_many({'id': {'$in': ids}, 'state': 'DELETED',
                             'boot': {'$exists': False}}, {'$set': {'state': 'CREATING'}})

        if 'delete' in self.params and self.params['delete']:
            DeleteBase.execute(list_vms_provider,
                               collection=self.db,
                               site=self.site,
                               experiment=self.experiment,
                               client=self.client,
                               info=self.params,
                               logger=self.logger)

        if 'check' in self.params and self.params['check'] is False:
            self.__create_vm(self.params['machines_per_cycle'])
            return

        if int(self.params['max_machines']) < 1:
            return

        if states['TOTAL'] == 0 or (states['TOTAL'] > 0 and
                                    states['CREATING'] > 0 and
                                    self.__deployed_machines_less_than_maximum()):
            self.create()
        elif states['TOTAL'] > 0 and self.__deployed_machines_less_than_maximum(): # and states['CREATING'] == 0
            self.create()
        else:
            if states['TOTAL'] == 1:
                self.logger.info("One machine creating, waiting for BOOT")
            elif states['TOTAL'] > 0 and states['CREATING'] > 0:
                self.logger.info("Machines not BOOT yet, waiting")
            else:
                self.logger.info("%s deployed yet, no deploy more", states['TOTAL'])

    def create(self, created=0):
        """Creates a new or group of new VMs

            Check the conditions to create a new VM. If there are no VMs deployed in the provider, a new VM will be
            created.
            If there are more VMs , a new VM always will be create unless there is only one VM and this VM is not
            executing a job yet, or the number of VMs is equal to the maximum allowed.

        :param created: Number of vms created by the iterator. On each iteration a maximum of 2 vms are created.

        """
        vms_to_create = self.__conditions_to_create(created)
        if vms_to_create == 0:
            return
        try:
            vms_created = self.__create_vm(vms_to_create)
            self.create(created + vms_created)
        except Exception,e:
            self.logger.error(e.message) if self.logger is not None else False

    def __create_vm(self, vms_to_create=1):
        """ Create a new VM

            Parse all parameters, create the final user_data from the template and send the request to the provider.
            Ones the provider responses, the information of the created VM is stored in DB.

        """
        params_to_create = copy.deepcopy(self.params)
        params_to_create['hostname'] = params_to_create['id'] = "%s-%s" % (self.params['prefix'], str(int(moment.now().epoch())))
        params_to_create['site'] = self.site
        params_to_create['collection'] = self.collection
        params_to_create['capped'] = self.capped

        if 'experiment' in params_to_create:
            params_to_create[params_to_create['experiment']] = True
        params_to_create['experiment'] = self.experiment

        if 'params' in params_to_create:
            for param in params_to_create['params']:
                params_to_create[param] = params_to_create['params'][param]

        # If user_data starts with #! is a script not name template
        if '#!' not in params_to_create['user_data']:
            '''
            try:
                env = Environment(loader=FileSystemLoader('/etc/vcycle/contextualization/'))
            except Exception as e:
                self.logger.error(str(e))
                return
            '''
            env = Environment(loader=PackageLoader('contextualization', ''))
            template = env.get_template(params_to_create['user_data'])
            params_to_create['user_data'] = template.render(params_to_create)
            open("../tmp/%s" % params_to_create['hostname'], 'w').write(params_to_create['user_data'])

        params_to_create['logger'] = self.logger if self.logger is not None else False
        params_to_create['machines_per_cycle'] = vms_to_create
        try:
            servers = self.client.create(**params_to_create)
            for server in servers:
                try:
                    if 'public_ip' in self.params:
                        import json
                        aux = self.client.add_network_address(server['id'])
                        print json.dumps(aux, indent=2)
                except Exception as ex:
                    self.logger.error("Error creating public IP %s", str(ex))
                self.db.insert({'id': server['id'],
                                'hostname': server['hostname'],
                                'state': server['state'],
                                'site': self.site,
                                'experiment': self.experiment,
                                'createdTime': int(time.mktime(time.gmtime(time.time())))})
                self.logger.info(" VM %s has been created", server['hostname']) if self.logger is not None else False
            return len(servers)
        except CloudException as ex:
            self.logger.error(str(ex))

    def list(self):
        """ List all VMs deployed in the provider

        """
        cur = self.db.find({'site': self.site, 'experiment': self.experiment, 'state': {'$nin': ['DELETED']}})
        states = {'ERROR': 0, 'CREATING': 0, 'BOOTED': 0, 'STARTED': 0, 'ENDED': 0, 'TOTAL': 0}
        for computer in cur:
            self.logger.info("%s\t%s" % (computer['hostname'], computer['state'])) if self.logger is not None else False
            states[computer['state']] += 1
            states['TOTAL'] += 1
        if self.logger is not None:
            self.logger.info("CREATING: %s ; BOOTED: %s ; STARTED: %s ; ERROR: %s ; ENDED: %s" % (states['CREATING'],
                                                                                     states['BOOTED'],
                                                                                     states['STARTED'],
                                                                                     states['ERROR'],
                                                                                     states['ENDED']))
        return states

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

        A new vm will be created if the number of VMs created in the cycle are less than 2 or the number of VMs is
        more than one, or is one and this one is executing a job.

        :param created: Number of vms created in the cycle
        :return: True if a VM can be created. False if not
        """
        if 'machines_per_cycle' in self.params:
            machines_per_cycle = self.params['machines_per_cycle']
        else:
            machines_per_cycle = 5

        if created >= machines_per_cycle:
            if self.logger is not None:
                self.logger.info("Thread has created %s machines, The thread will end", machines_per_cycle )
            return False

        if self.__only_one_machine_not_started():
            return False

        return self.__deployed_machines_less_than_maximum()

    def __only_one_machine_not_started(self):
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

    def __no_machines_creating(self):
        cursor = self.db.aggregate([{'$match': {'site': self.site, 'experiment': self.experiment,
                                    'state': {'$nin': ['DELETED', 'ENDED', 'ERROR']}}},
                         {'$group': {'_id': {'site': "$site", 'experiment': "$experiment", 'state': "$state"},
                          'count': {'$sum': 1}}}])
        values = {}
        total = 0
        for value in cursor:
            values[value['_id']['state']] = value['count']
            total += value['count']

        if 'CREATING' not in values and total > 0:
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
            if 'machines_per_cycle' in self.params :
                if self.params['machines_per_cycle'] > self.params['max_machines'] - int(val):
                    return self.params['machines_per_cycle'] - int(val)
                else:
                    return self.params['machines_per_cycle']
            else:
                return int(self.params['max_machines']) - int(val)

        if self.logger is not None:
            self.logger.info("Number of VM %s is equal or higher than %s ; no create more VMs" % (val, self.params['max_machines']))
        return 0










