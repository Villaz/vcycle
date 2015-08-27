__author__ = 'luis'

try:
    from conditions import DeleteBase
except:
    from vcycle.conditions import DeleteBase

import time
from pymongo import ReturnDocument
import pathos.multiprocessing as mp

class Delete(DeleteBase):

    def __init__(self, collection=None, site="", experiment="", client=None, info=[], logger=None):
        DeleteBase.__init__(self,
                            collection=collection,
                            site=site,
                            experiment=experiment,
                            client=client,
                            info=info,
                            logger=logger)

    def delete_computers_in_error_stopped_ended_state(self, list_servers=[]):
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': {'$in': ['ENDED', 'ERROR', 'STOPPED']}})
        ids_to_delete = [vm['id'] for vm in cursor]
        pool = mp.ProcessingPool(4)
        ids = pool.map(self.client.delete, ids_to_delete)
        self.collection.update_many({'id': {'$in': ids_to_delete}},{'$set': {'state': 'DELETED'}})
        if self.logger is not None:
            [self.logger.info("Deleting VM %s with state ENDED/ERROR/STOPPED" % vm['hostname']) for vm in cursor]

    def delete_computers_lost_heartbeat(self, list_servers=[]):
        if 'heartbeat' not in self.info:
            return
        now = int(time.mktime(time.gmtime(time.time()))) - int(self.info['heartbeat'])
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': {'$in': ['STARTED','BOOTED']},
                                       'heartbeat': {'$lt': now}})
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s which lost heartbeat" % vm['hostname'])
            self.client.delete(vm['id'])
            self.collection.find_one_and_update({'id': vm['id']},
                                                {'$set': {'state': 'DELETED'}},
                                                return_document=ReturnDocument.AFTER)

    def delete_computers_not_started(self, list_servers=[]):
        if 'boot_time' not in self.info:
            return
        now = int(time.mktime(time.gmtime(time.time()))) - int(self.info['boot_time'])
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': 'CREATING',
                                       'createdTime': {'$lt': now}})
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s which not BOOT" % vm['hostname'])
            self.client.delete(vm['id'])
            self.collection.find_one_and_update({'id': vm['id']},
                                                {'$set': {'state': 'DELETED'}})

    def delete_computers_booted_and_not_started(self, list_servers=[]):
        if 'start_time' not in self.info or 'boot_time' not in self.info:
            return
        now = int(time.mktime(time.gmtime(time.time()))) - (self.info['boot_time'] + self.info['start_time'])
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': 'BOOTED',
                                       'createdTime': {'$lt': now}})
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s which not START" % vm['hostname'])
            self.client.delete(vm['id'])
            self.collection.find_one_and_update({'id': vm['id']},
                                                {'$set': {'state': 'DELETED'}})

    def delete_ended_computers(self, list_servers=[]):
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': 'ENDED'})
        vms = []
        for vm in cursor:
            if self.logger is not None:
                self.logger.info("Deleting VM %s with state ENDED" % vm['hostname'])
            vms.append(vm)
            self.client.delete(vm['id'])
            self.collection.find_one_and_update({'id': vm['id'],
                                                 'site': self.site,
                                                 'experiment': self.experiment},
                                                {'$set': {'state': 'DELETED'}})

    def delete_walltime_computers(self, list_servers=[]):
        if 'wall_time' not in self.info:
            return

        now = int(time.mktime(time.gmtime(time.time())))
        cursor = self.collection.find({'site': self.site,
                                       'experiment': self.experiment,
                                       'state': {'$nin': ['DELETED']}})

        for vm in cursor:
            if (now - vm['createdTime']) > self.info['wall_time']:
                if self.logger is not None:
                    self.logger.info("Deleting VM %s with walltime" % vm['hostname'])
                self.client.delete(vm['id'])
                self.collection.find_one_and_update({'id': vm['id'],
                                                     'site': self.site,
                                                     'experiment': self.experiment},
                                                    {'$set': {'state': 'DELETED'}})

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


