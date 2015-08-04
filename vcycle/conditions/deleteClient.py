__author__ = 'Luis Villazon Esteban'

try:
    from conditions import DeleteBase
    from connectors import CloudException
except:
    from vcycle.conditions import DeleteBase
    from vcycle.connectors import CloudException


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
        for id in ids:
            if self.collection.find({'id': id,
                                     'site': self.site,
                                     'experiment': self.experiment,
                                     'state': {'$nin': ['DELETED']}}).count() == 0:
                if self.logger:
                    self.logger.info("VM %s not in DB. Delete from provider", id)
                try:
                    self.client.delete(id)
                    deleted.append({'id': id})
                except CloudException as ex:
                    if self.logger is not None:
                        self.logger.warn(str(ex))
        return DeleteBase.process_list(list_servers, deleted)

    def drop_db_servers_not_in_provider(self, list_servers=[]):
        deleted = []
        vm_ids = [vm['id'] for vm in list_servers]
        cursor = self.collection.find({'experiment': self.experiment,
                                       'site': self.site,
                                       'state': {'$nin': ['DELETED']},
                                       'id': {'$nin': vm_ids}})
        for vm in cursor:
            deleted.append(vm)
            if self.logger:
                self.logger.info("VM %s not in client, change state to delete", vm['hostname'])
            self.collection.find_one_and_update({'hostname': vm['hostname']},
                                                {'$set': {'state': 'DELETED'}})
        return DeleteBase.process_list(list_servers, deleted)

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
        for vm in cursor:
            deleted.append(vm)
            self.client.delete(vm['id'])
            if self.logger:
                self.logger.info("VM %s with provider state STOPPED/ERROR , DELETING VM", vm['hostname'])
            self.collection.find_one_and_update({'id': vm['id']},
                                           {'$set': {'state': 'DELETED'}})
        return DeleteBase.process_list(list_servers, deleted)