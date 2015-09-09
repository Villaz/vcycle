__author__ = 'luis'

try:
    from conditions import DeleteBase
except:
    from vcycle.conditions import DeleteBase

import time
from pymongo import ReturnDocument


class Delete(DeleteBase):

    def __init__(self, collection=None, site="", experiment="", client=None, info=[], logger=None):
        DeleteBase.__init__(self,
                            collection=collection,
                            site=site,
                            experiment=experiment,
                            client=client,
                            info=info,
                            logger=logger)

    def delete_vms_if_higher_than_max_vms(self, list_servers=[]):
        ids_to_delete = []
        total_machines = self.collection.count({'site': self.site,
                                                'experiment': self.experiment,
                                                'state': {'$in': ['CREATING', 'BOOTED', 'STARTED']}})
        for state in ['CREATING', 'BOOTED', 'STARTED']:
            creating_machines = self.collection.find({'site': self.site,
                                                'experiment': self.experiment,
                                                'state': state})
            for machine in creating_machines:
                if self.info['max_machines'] < (total_machines - len(ids_to_delete)):
                    self.logger.info("Deleting VM %s because %s higher than %s" % (machine['hostname'],
                                                                                (total_machines - len(ids_to_delete)),
                                                                                self.info['max_machines']))
                    self.client.delete(machine['id'])
                    ids_to_delete.append(machine['id'])
                else:
                    break
            if (total_machines - len(ids_to_delete)) <= self.info['max_machines']:
                break
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})

    def delete_computers_in_error_stopped_ended_state(self, list_servers=[]):
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': {'$in': ['ENDED', 'ERROR', 'STOPPED']}})
        ids_to_delete = []
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s with state ENDED/ERROR/STOPPED" % vm['hostname'])
            self.client.delete(vm['id'])
            ids_to_delete.append(vm['id'])
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})

    def delete_computers_lost_heartbeat(self, list_servers=[]):
        if 'heartbeat' not in self.info:
            return
        now = int(time.mktime(time.gmtime(time.time()))) - int(self.info['heartbeat'])
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': {'$in': ['STARTED','BOOTED']},
                                       'heartbeat': {'$lt': now}})
        ids_to_delete = []
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s which lost heartbeat" % vm['hostname'])
            self.client.delete(vm['id'])
            ids_to_delete.append(vm['id'])
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})

    def delete_computers_not_started(self, list_servers=[]):
        if 'boot_time' not in self.info:
            return
        now = int(time.mktime(time.gmtime(time.time()))) - int(self.info['boot_time'])
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': 'CREATING',
                                       'createdTime': {'$lt': now}})
        ids_to_delete = []
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s which not BOOT" % vm['hostname'])
            self.client.delete(vm['id'])
            ids_to_delete.append(vm['id'])
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})

    def delete_computers_booted_and_not_started(self, list_servers=[]):
        if 'start_time' not in self.info or 'boot_time' not in self.info:
            return
        now = int(time.mktime(time.gmtime(time.time()))) - (self.info['boot_time'] + self.info['start_time'])
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': 'BOOTED',
                                       'createdTime': {'$lt': now}})
        ids_to_delete = []
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s which not START" % vm['hostname'])
            self.client.delete(vm['id'])
            ids_to_delete.append(vm['id'])
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})

    def delete_ended_computers(self, list_servers=[]):
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': 'ENDED'})
        ids_to_delete = []
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s with state ENDED" % vm['hostname'])
            ids_to_delete.append(vm['id'])
            self.client.delete(vm['id'])
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})

    def delete_walltime_computers(self, list_servers=[]):
        if 'wall_time' not in self.info:
            return

        now = int(time.mktime(time.gmtime(time.time())))
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': {'$nin': ['DELETED']}})
        ids_to_delete = []
        for vm in cursor:
            if (now - vm['createdTime']) > self.info['wall_time']:
                if self.logger is not None:
                    self.logger.info("Deleting VM %s with walltime" % vm['hostname'])
                self.client.delete(vm['id'])
                ids_to_delete.append(vm['id'])
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})

    def merge_duplicate_entries(self, list_servers=[]):
        cursor = self.collection.aggregate([{'$match': {'site': self.site, 'experiment': self.experiment}},
                          {'$group': {'_id': "$hostname", 'count': {'$sum': 1},
                                      'ids': {'$push': '$id'}, 'states': {'$push': '$state'}}},
                          {'$match': {'count': {'$gt': 1}}}])

        for value in cursor:
            if 'DELETED' in value['states']:
                self.collection.delete_many({'hostname': value['_id'], 'state': {'$nin': ['DELETED']}})
                for id in value['ids']:
                    self.client.delete(id)
            elif 'ENDED' in value['states']:
                self.collection.delete_many({'hostname': value['_id'], 'state': {'$nin': ['ENDED']}})
            elif 'ERROR' in value['states']:
                self.collection.delete_many({'hostname': value['_id'], 'state': {'$nin': ['ERROR']}})
            elif 'STARTED' in value['states']:
                self.collection.delete_many({'hostname': value['_id'], 'state': {'$nin': ['STARTED']}})
            elif 'BOOTED' in value['states']:
                self.collection.delete_many({'hostname': value['_id'], 'state': {'$nin': ['BOOTED']}})


