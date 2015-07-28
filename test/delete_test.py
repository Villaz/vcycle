__author__ = 'luis'

from main import delete
from main import deleteClient

from pymongo import MongoClient
import unittest
import moment

db = MongoClient('mongodb://luis:Espronceda@ds047911.mongolab.com:47911/infinity').infinity


class Foo:
    def delete(self, params):
        pass


class Delete(unittest.TestCase):

    def test_delete_computers_in_error_stopped_ended_state(self):
        info = {'connector': {}}
        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'CREATING', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'STARTED','site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'ENDED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 5, 'hostname': 5, 'state': 'STOPPED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 6, 'hostname': 6, 'state': 'ERROR', 'site': 'test', 'experiment': 'test'})
        delete.delete_computers_in_error_stopped_ended_state(db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state':'DELETED'}).count(), 3)
        self.assertEqual(db.test.find({'state': {'$in': ['ERROR','STOPPED','ENDED']}}).count(), 0)


    def test_delete_computers_lost_heartbeat(self):
        info = {'connector': {}, 'heartbeat': 400}
        db.test.delete_many({})
        bad_heartbeat = int(moment.now().subtract('seconds', 800).epoch(rounding=True))
        good_heartbeat = int(moment.now().subtract('seconds', 100).epoch(rounding=True))
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'heartbeat':bad_heartbeat })
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'heartbeat':good_heartbeat})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'STARTED','site': 'test', 'experiment': 'test', 'heartbeat':bad_heartbeat})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'STARTED', 'site': 'test', 'experiment': 'test', 'heartbeat':good_heartbeat})
        delete.delete_computers_lost_heartbeat(db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 2)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')
        self.assertEqual(db.test.find({'hostname': 4})[0]['state'], 'STARTED')

    def test_delete_computers_not_started(self):
        info = {'connector': {}, 'boot_time': 400}
        db.test.delete_many({})
        bad_boot = int(moment.now().subtract('seconds', 800).epoch(rounding=True))
        good_boot = int(moment.now().subtract('seconds', 100).epoch(rounding=True))

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'CREATING', 'site': 'test', 'experiment': 'test', 'createdTime':bad_boot })
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'CREATING', 'site': 'test', 'experiment': 'test', 'createdTime':good_boot})

        delete.delete_computers_not_started(db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state': 'CREATING'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'CREATING')

    def test_delete_computers_booted_and_not_started(self):
        info = {'connector': {}, 'boot_time': 400, 'start_time':500}
        db.test.delete_many({})
        bad_boot = int(moment.now().subtract('seconds', 1000).epoch(rounding=True))
        good_boot = int(moment.now().subtract('seconds', 700).epoch(rounding=True))

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'createdTime':bad_boot })
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'createdTime':good_boot})

        delete.delete_computers_booted_and_not_started(db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state': 'BOOTED'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')

    def test_delete_ended_computers(self):
        info = {'connector': {}}
        db.test.delete_many({})

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'ENDED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        delete.delete_ended_computers(db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')

    def test_delete_walltime_computers(self):
        info = {'connector': {}, 'walltime':1000}
        db.test.delete_many({})
        bad_walltime = int(moment.now().subtract('seconds', 1100).epoch(rounding=True))
        good_walltime = int(moment.now().subtract('seconds', 700).epoch(rounding=True))

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test', 'createdTime': bad_walltime})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'createdTime': good_walltime})

        delete.delete_walltime_computers(db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')

    def test_drop_duplicate_vms(self):
        info = {'connector':{}}
        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        db.test.insert({'id': 2, 'hostname': 2, 'state': 'CREATING', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'ENDED', 'site': 'test', 'experiment': 'test'})

        db.test.insert({'id': 3, 'hostname': 3, 'state': 'DELETED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})

        delete.merge_duplicate_entries(db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({}).count(), 3)
        self.assertEqual(db.test.find({'id': 1})[0]['state'], 'STARTED')
        self.assertEqual(db.test.find({'id': 2})[0]['state'], 'ENDED')
        self.assertEqual(db.test.find({'id': 3})[0]['state'], 'DELETED')

    def test_drop_db_servers_not_in_provider(self):
        info = {'connector':{}}
        list_servers = [{'id': 1, 'hostname': 1}, {'id': 2, 'hostname': 2}, {'id': 3, 'hostname': 3}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        deleteClient.drop_db_servers_not_in_provider(list_servers,db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 1)
        self.assertEqual(db.test.find({'state': 'DELETED'})[0]['id'], 4)

    def test_db_servers_where_provider_has_status_error_stopped(self):
        info = {'connector':{}}
        list_servers = [{'id': 1, 'hostname': 1, 'state': 'STOPPED'},
                        {'id': 2, 'hostname': 2, 'state': 'ERROR'},
                        {'id': 3, 'hostname': 3, 'state': 'ENDED'},
                        {'id': 4, 'hostname': 4, 'state': 'CREATED'}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        deleteClient.db_servers_where_provider_has_status_error_stopped(list_servers, db.test, 'test', 'test', Foo(), info)
        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 3)
        self.assertEqual(db.test.find({'id': 4})[0]['state'], 'BOOTED')

if __name__ == '__main__':
    unittest.main()