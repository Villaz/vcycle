__author__ = 'Luis Villazon Esteban'

import copy


def drop_error_stopped_vms(list_servers, collection, site, experiment, client, info, logger=None):
    for vm in list_servers:
        if vm['state'] in ['ERROR', 'STOPPED', 'ENDED']:
            if logger:
                logger.info("Deleting VM %s with bad state %s", vm['id'], vm['state'])
            client.delete(vm['id'])


def drop_servers_not_in_db(list_servers, collection, site, experiment, client, info, logger=None):
    ids = [vm['id'] for vm in list_servers]
    for id in ids:
        if collection.find({'id': id}).count() == 0:
            if logger:
                logger.info("VM %s not in DB. Delete from provider", id)
            client.delete(id)


def drop_db_servers_not_in_provider(list_servers, collection, site, experiment, client, info, logger=None):
    hostnames = [vm['hostname'] for vm in list_servers]
    cursor = collection.find({'experiment': experiment,
                     'site': site,
                     'state': {'$nin': ['DELETED']},
                     'hostname': {'$nin': hostnames}})
    for vm in cursor:
        if logger:
            logger.info("VM %s not in client, change state to delete", vm['hostname'])
        collection.find_one_and_update({'hostname': vm['hostname']},
                                       {'$set': {'state': 'DELETED'}})


def db_servers_where_provider_has_status_error_stopped(list_servers, collection, site, experiment, client, info, logger=None):
    hostnames = []
    for vm in list_servers:
        if vm['state'] in ['STOPPED', 'ERROR', 'ENDED']:
            if logger:
                logger.info("VM %s with state %s", vm['hostname'], vm['state'])
            hostnames.append(vm['hostname'])
    cursor = collection.find({'hostname': {'$in': hostnames},
                              'state': {'$nin': ['DELETED','ENDED']}})
    for vm in cursor:
        client.delete(vm['id'])
        if logger:
            logger.info("VM %s with provider state STOPPED/ERROR , DELETING VM", vm['hostname'])
        collection.find_one_and_update({'hostname':vm['hostname']},
                                           {'$set': {'state': 'DELETED'}})

