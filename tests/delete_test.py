__author__ = 'luis'

from vcycle.conditions import delete
from vcycle.conditions import deleteClient

from pymongo import MongoClient
import unittest
import moment
import time

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

        d = delete.Delete(collection=db.test, site='test' ,experiment='test', client=Foo(), info=info)
        d.delete_computers_in_error_stopped_ended_state()
        self.assertEqual(db.test.find({'state':'DELETED'}).count(), 3)
        self.assertEqual(db.test.find({'state': {'$in': ['ERROR', 'STOPPED','ENDED']}}).count(), 0)

    def test_delete_computers_lost_heartbeat(self):
        info = {'connector': {}, 'heartbeat': 400}
        db.test.delete_many({})
        bad_heartbeat = int(time.mktime(time.gmtime(time.time()))) - 800
        good_heartbeat = int(time.mktime(time.gmtime(time.time()))) - 100
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'heartbeat':bad_heartbeat })
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'heartbeat':good_heartbeat})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'STARTED','site': 'test', 'experiment': 'test', 'heartbeat':bad_heartbeat})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'STARTED', 'site': 'test', 'experiment': 'test', 'heartbeat':good_heartbeat})

        d = delete.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        d.delete_computers_lost_heartbeat()

        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 2)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')
        self.assertEqual(db.test.find({'hostname': 4})[0]['state'], 'STARTED')

    def test_delete_computers_not_started(self):
        info = {'connector': {}, 'boot_time': 400}
        db.test.delete_many({})
        bad_boot = int(time.mktime(time.gmtime(time.time()))) - 800
        good_boot = int(time.mktime(time.gmtime(time.time()))) - 100

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'CREATING', 'site': 'test', 'experiment': 'test', 'createdTime':bad_boot })
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'CREATING', 'site': 'test', 'experiment': 'test', 'createdTime':good_boot})

        d = delete.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        d.delete_computers_not_started()

        self.assertEqual(db.test.find({'state': 'CREATING'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'CREATING')

    def test_delete_computers_booted_and_not_started(self):
        info = {'connector': {}, 'boot_time': 400, 'start_time':500}
        db.test.delete_many({})
        bad_boot = int(time.mktime(time.gmtime(time.time()))) - 1000
        good_boot = int(time.mktime(time.gmtime(time.time()))) - 700

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'createdTime':bad_boot })
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test', 'createdTime':good_boot})

        d = delete.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        d.delete_computers_booted_and_not_started()

        self.assertEqual(db.test.find({'state': 'BOOTED'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')

    def test_delete_ended_computers(self):
        info = {'connector': {}}
        db.test.delete_many({})

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'ENDED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        d = delete.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        d.delete_ended_computers()

        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')

    def test_delete_walltime_computers(self):
        info = {'connector': {}, 'wall_time': 1000}
        db.test.delete_many({})
        bad_walltime =  int(time.mktime(time.gmtime(time.time()))) - 1100
        good_walltime = int(time.mktime(time.gmtime(time.time()))) - 700

        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED',
                        'site': 'test', 'experiment': 'test', 'createdTime': bad_walltime})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED',
                        'site': 'test', 'experiment': 'test', 'createdTime': good_walltime})

        d = delete.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        d.delete_walltime_computers()

        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 1)
        self.assertEqual(db.test.find({'hostname': 2})[0]['state'], 'BOOTED')

    def test_drop_duplicate_vms(self):
        info = {'connector': {}}
        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        db.test.insert({'id': 2, 'hostname': 2, 'state': 'CREATING', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'ENDED', 'site': 'test', 'experiment': 'test'})

        db.test.insert({'id': 3, 'hostname': 3, 'state': 'DELETED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})

        d = delete.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        d.merge_duplicate_entries()
        self.assertEqual(db.test.find({}).count(), 3)
        self.assertEqual(db.test.find({'id': 1})[0]['state'], 'STARTED')
        self.assertEqual(db.test.find({'id': 2})[0]['state'], 'ENDED')
        self.assertEqual(db.test.find({'id': 3})[0]['state'], 'DELETED')

    def test_drop_db_servers_not_in_provider(self):
        info = {'connector': {}}
        list_servers = [{'id': 1, 'hostname': 1}, {'id': 2, 'hostname': 2}, {'id': 3, 'hostname': 3}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        d = deleteClient.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        new_servers = d.drop_db_servers_not_in_provider(list_servers)

        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 1)
        self.assertEqual(db.test.find({'state': 'DELETED'})[0]['id'], 4)
        self.assertEqual(len(new_servers), 3)

    def test_db_servers_where_provider_has_status_error_stopped(self):
        info = {'connector': {}}
        list_servers = [{'id': 1, 'hostname': 1, 'state': 'STOPPED'},
                        {'id': 2, 'hostname': 2, 'state': 'ERROR'},
                        {'id': 3, 'hostname': 3, 'state': 'ENDED'},
                        {'id': 4, 'hostname': 4, 'state': 'CREATED'}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        d = deleteClient.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        new_servers = d.db_servers_where_provider_has_status_error_stopped(list_servers)

        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 3)
        self.assertEqual(db.test.find({'id': 4})[0]['state'], 'BOOTED')
        self.assertEqual(len(new_servers), 1)
        self.assertEqual(new_servers[0]['id'], 4)

    def test_drop_servers_not_in_db(self):
        info = {'connector': {}}
        list_servers = [{'id': 1, 'hostname': 1, 'state': 'STOPPED'},
                        {'id': 2, 'hostname': 2, 'state': 'ERROR'},
                        {'id': 3, 'hostname': 3, 'state': 'ENDED'},
                        {'id': 4, 'hostname': 4, 'state': 'CREATED'}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        d = deleteClient.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        new_servers = d.drop_servers_not_in_db(list_servers)
        self.assertEqual(db.test.find({}).count(), 2)
        self.assertEqual(len(new_servers), 2)
        self.assertEqual(new_servers[0]['id'], 1)
        self.assertEqual(new_servers[1]['id'], 4)

    def test_drop_error_stopped_vms(self):
        info = {'connector': {}}
        list_servers = [{'id': 1, 'hostname': 1, 'state': 'STOPPED'},
                        {'id': 2, 'hostname': 2, 'state': 'ERROR'},
                        {'id': 3, 'hostname': 3, 'state': 'ENDED'},
                        {'id': 4, 'hostname': 4, 'state': 'CREATED'}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        d = deleteClient.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        new_servers = d.drop_error_stopped_vms(list_servers)
        self.assertEqual(db.test.find({}).count(), 2)
        self.assertEqual(len(new_servers), 1)
        self.assertEqual(new_servers[0]['id'], 4)

    def test_execute_deleteClient(self):
        info = {'connector': {}}
        list_servers = [{'id': 1, 'hostname': 1, 'state': 'STOPPED'},
                        {'id': 2, 'hostname': 2, 'state': 'ERROR'},
                        {'id': 3, 'hostname': 3, 'state': 'ENDED'},
                        {'id': 4, 'hostname': 4, 'state': 'CREATED'}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        d = deleteClient.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        new_servers = d.execute_all(list_servers)
        self.assertEqual(len(new_servers), 1)
        self.assertEqual(new_servers[0]['id'], 4)
        self.assertEqual(db.test.find({'state': 'DELETED'}).count(), 3)

    def test_execute_delete(self):
        info = {'connector': {}, 'boot_time': 400, 'start_time': 500, 'heartbeat': 600, 'walltime': 1700, 'max_machines':2000}
        list_servers = [{'id': 1, 'hostname': 1, 'state': 'STOPPED'},
                        {'id': 2, 'hostname': 2, 'state': 'ERROR'},
                        {'id': 3, 'hostname': 3, 'state': 'ENDED'},
                        {'id': 4, 'hostname': 4, 'state': 'CREATED'}]

        db.test.delete_many({})
        db.test.insert({'id': 1, 'hostname': 1, 'state': 'STARTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 2, 'hostname': 2, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 3, 'hostname': 3, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})
        db.test.insert({'id': 4, 'hostname': 4, 'state': 'BOOTED', 'site': 'test', 'experiment': 'test'})

        d = delete.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        new_servers = d.execute_all(list_servers)
        self.assertEqual(new_servers, None)

    def test_all_vms_are_in_provider_and_db(self):
        info = {'connector': {}, 'boot_time': 400, 'start_time': 500, 'heartbeat': 600, 'walltime': 1700, 'max_machines':2000}
        list_servers = [{'id': i, 'hostname': i, 'state': 'STARTED', 'site':'test', 'experiment':'test'} for i in range(1000)]
        db.test.delete_many({})
        db.test.insert_many(list_servers)

        d = deleteClient.Delete(collection=db.test, site='test', experiment='test', client=Foo(), info=info)
        new_servers = d.execute_all(list_servers)
        self.assertEqual(db.test.find({'state':'STARTED'}).count(), 1000)
        self.assertEqual(len(new_servers), 1000)


#if __name__ == '__main__':
#    unittest.main()