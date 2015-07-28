__author__ = 'luis'

import moment
import copy
from pymongo import ReturnDocument


def delete_computers_in_error_stopped_ended_state(collection, site, experiment, client, info, logger=None):
    cursor = collection.find({'site': site, 'experiment': experiment, 'state': {'$in': ['ENDED', 'ERROR', 'STOPPED']}})
    for vm in cursor:
        if logger is not None:
            logger.info("Deleting VM %s with state ENDED/ERROR/STOPPED" % vm['hostname'])
        client.delete(vm['id'])
        collection.find_one_and_update({'id': vm['id']},
                                       {'$set': {'state': 'DELETED'}},
                                       return_document=ReturnDocument.AFTER)


def delete_computers_lost_heartbeat(collection, site, experiment, client, info, logger=None):
    now = int(moment.now().subtract('seconds', info['heartbeat']).epoch(rounding=True))
    cursor = collection.find({'site': site, 'experiment': experiment, 'state': {'$in': ['STARTED','BOOTED']},
                                'heartbeat': {'$lt': now}})

    for vm in cursor:
        if logger is not None:
            logger.info("Deleting VM %s which lost heartbeat" % vm['hostname'])
        client.delete(vm['id'])
        collection.find_one_and_update({'id': vm['id']},
                                         {'$set': {'state': 'DELETED'}},
                                         return_document=ReturnDocument.AFTER)


def delete_computers_not_started(collection, site, experiment, client, info, logger=None):
    now = int(moment.now().subtract('seconds', info['boot_time']).epoch(rounding=True))
    cursor = collection.find({'site': site, 'experiment': experiment, 'state': 'CREATING', 'createdTime': {'$lt': now}})
    for vm in cursor:
        if logger is not None:
            logger.info("Deleting VM %s which not BOOT" % vm['hostname'])
        client.delete(vm['id'])
        collection.find_one_and_update({'id': vm['id']},
                                       {'$set': {'state': 'DELETED'}})


def delete_computers_booted_and_not_started(collection, site, experiment, client, info, logger=None):
    now = int(moment.now().subtract('seconds', (info['boot_time'] + info['boot_time'])).epoch(rounding=True))
    cursor = collection.find({'site': site, 'experiment': experiment, 'state': 'BOOTED', 'createdTime': {'$lt': now}})
    for vm in cursor:
        if logger is not None:
            logger.info("Deleting VM %s which not START" % vm['hostname'])
        client.delete(vm['id'])
        collection.find_one_and_update({'id': vm['id']},
                                       {'$set': {'state': 'DELETED'}})


def delete_ended_computers(collection, site, experiment, client, info, logger=None):
    cursor = collection.find({'site': site, 'experiment': experiment, 'state': 'ENDED'})
    for vm in cursor:
        if logger is not None:
            logger.info("Deleting VM %s with state ENDED" % vm['hostname'])
        client.delete(vm['id'])
        collection.find_one_and_update({'id': vm['id'], 'site': site, 'experiment': experiment},
                                         {'$set': {'state':'DELETED'}})


def delete_walltime_computers(collection, site, experiment, client, info, logger=None):
    if 'wall_time' not in info:
        return

    now = moment.now().epoch()
    cursor = collection.find({'site': site, 'experiment': experiment, 'state': {'$nin':['DELETED']}})

    for vm in cursor:
        if (now - vm['createdTime']) > info['wall_time']:
            if logger is not None:
                logger.info("Deleting VM %s with walltime" % vm['hostname'])
            client.delete(vm['id'])
            collection.find_one_and_update({'id': vm['id'], 'site': site, 'experiment': experiment},
                                             {'$set': {'state': 'DELETED'}})


def merge_duplicate_entries(collection, site, experiment, client, info, logger=None):
    cursor = collection.aggregate([{'$match': {'site': site, 'experiment': experiment}},
                          {'$group': {'_id': "$hostname", 'count': {'$sum': 1}, 'ids': {'$push': '$id'}, 'states': {'$push': '$state'}}},
                          {'$match': {'count': {'$gt': 1}}}])
    for value in cursor:
        if 'DELETED' in value['states']:
            collection.delete_many({'id': value['_id'], 'state': {'$nin': ['DELETED']}})
            for id in value['ids']:
                client.delete(id)
        elif 'ENDED' in value['states']:
            collection.delete_many({'id': value['_id'], 'state': {'$nin': ['ENDED']}})
        elif 'ERROR' in value['states']:
            collection.delete_many({'id': value['_id'], 'state': {'$nin': ['ERROR']}})
        elif 'STARTED' in value['states']:
            collection.delete_many({'id': value['_id'], 'state': {'$nin': ['STARTED']}})
        elif 'BOOTED' in value['states']:
            collection.delete_many({'id': value['_id'], 'state': {'$nin': ['BOOTED']}})