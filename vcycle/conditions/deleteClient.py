__author__ = 'Luis Villazon Esteban'

try:
    from conditions import DeleteBase
    from connectors import CloudException
except:
    from vcycle.conditions import DeleteBase
    from vcycle.connectors import CloudException

import pathos.multiprocessing as mp


def testing(x):
    return x[0](x[1])

class Delete(DeleteBase):

    def __init__(self, servers=[], collection=None, site="", experiment="", client=None, info="", logger=None):
        DeleteBase.__init__(self,
                            collection=collection,
                            site=site,
                            experiment=experiment,
                            client=client,
                            info=info,
                            logger=logger)

    def drop_error_stopped_vms(self, list_servers=[]):
        deleted = []
        for vm in list_servers:
            if vm['state'] in ['ERROR', 'STOPPED', 'ENDED']:
                if self.logger:
                    self.logger.info("Deleting VM %s with bad state %s", vm['hostname'], vm['state'])
                try:
                    self.client.delete(vm['id'])
                    deleted.append(vm)
                except CloudException, ex:
                    if self.logger:
                        self.logger.warn("Error deleting vm %s", vm['hostname'])
        return DeleteBase.process_list(list_servers, deleted)

    def drop_servers_not_in_db(self, list_servers=[]):
        deleted = []
        ids = [vm['id'] for vm in list_servers]
        db_ids = [ vm['id'] for vm in self.collection.find({'id': {'$in': ids},
                                                    'site': self.site,
                                                    'experiment': self.experiment,
                                                    'state': {'$nin': ['DELETED']}})]

        pool = mp.ProcessingPool(4)
        ids = pool.map(self.client.delete, list(set(ids) - set(db_ids)))

        for id in ids:
            if self.logger:
                    self.logger.info("VM %s not in DB. Delete from provider", id)
        return DeleteBase.process_list(list_servers, [{'id':id} for id in ids])


    def drop_db_servers_not_in_provider(self, list_servers=[]):
        deleted = []
        vm_ids = [vm['id'] for vm in list_servers]
        cursor = self.collection.find({'experiment': self.experiment,
                                       'site': self.site,
                                       'state': {'$nin': ['DELETED']},
                                       'id': {'$nin': vm_ids}})
        ids_to_delete = [vm['id'] for vm in cursor]
        if self.logger:
            [self.logger.info("VM %s not in client, change state to delete", vm['hostname']) for vm in cursor]
        self.collection.update_many({'id': {'$in':ids_to_delete}},
                                    {'$set': {'state': 'DELETED'}})
        return DeleteBase.process_list(list_servers, [vm for vm in cursor])

    def db_servers_where_provider_has_status_error_stopped(self, list_servers=[]):
        deleted = []
        ids = []
        for vm in list_servers:
            if vm['state'] in ['STOPPED', 'ERROR', 'ENDED']:
                if self.logger:
                    self.logger.info("VM %s with state %s", vm['hostname'], vm['state'])
                ids.append(vm['id'])
        cursor = self.collection.find({'id': {'$in': ids},
                                       'state': {'$nin': ['DELETED','ENDED']}})

        ids_to_delete = [vm['id'] for vm in cursor]
        pool = mp.ProcessingPool(4)
        deleted_ids = pool.map(self.client.delete, ids_to_delete)
        self.collection.update_many({'id': {'$in': deleted_ids}},{'$set': {'state': 'DELETED'}})

        if self.logger:
            [self.logger.info("VM %s with provider state STOPPED/ERROR , DELETING VM", vm['hostname']) for vm in cursor]

        return DeleteBase.process_list(list_servers, [{'id': id} for id in ids])