__author__ = 'Luis Villazon Esteban'

import copy
from connectors import cloudconnector


def drop_error_stopped_vms(list_servers, collection, site, experiment, client, info, logger=None):
    for vm in list_servers:
        if vm['state'] in ['ERROR', 'STOPPED', 'ENDED']:
            if logger:
                logger.info("Deleting VM %s with bad state %s", vm['hostname'], vm['state'])
            try:
                client.delete(vm['id'])
            except cloudconnector.CloudException, ex:
                if logger:
                    logger.warn("Error deleting vm %s", vm['hostname'])


def drop_servers_not_in_db(list_servers, collection, site, experiment, client, info, logger=None):
    ids = [vm['id'] for vm in list_servers]
    for id in ids:
        if collection.find({'id': id, 'site':site, 'experiment':experiment, 'state':{'$nin':['DELETED']}}).count() == 0:
            if logger:
                logger.info("VM %s not in DB. Delete from provider", id)
            try:
                client.delete(id)
            except cloudconnector.CloudException as ex:
                if logger is not None:
                    logger.warn(str(ex))



def drop_db_servers_not_in_provider(list_servers, collection, site, experiment, client, info, logger=None):
    id = [vm['id'] for vm in list_servers]
    cursor = collection.find({'experiment': experiment,
                              'site': site,
                              'state': {'$nin': ['DELETED']},
                              'id': {'$nin': id}})
    for vm in cursor:
        if logger:
            logger.info("VM %s not in client, change state to delete", vm['hostname'])
        collection.find_one_and_update({'hostname': vm['hostname']},
                                       {'$set': {'state': 'DELETED'}})


def db_servers_where_provider_has_status_error_stopped(list_servers, collection, site, experiment, client, info, logger=None):
    ids = []
    for vm in list_servers:
        if vm['state'] in ['STOPPED', 'ERROR', 'ENDED']:
            if logger:
                logger.info("VM %s with state %s", vm['hostname'], vm['state'])
            ids.append(vm['id'])
    cursor = collection.find({'id': {'$in': ids},
                              'state': {'$nin': ['DELETED','ENDED']}})
    for vm in cursor:
        client.delete(vm['id'])
        if logger:
            logger.info("VM %s with provider state STOPPED/ERROR , DELETING VM", vm['hostname'])
        collection.find_one_and_update({'id': vm['id']},
                                           {'$set': {'state': 'DELETED'}})

