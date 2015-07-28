__author__ = 'luis'

import unittest
import openstack

class OpenstackTest(unittest.TestCase):

    def test_list(self):
        params = {'username': 'lvillazo',
                  'password': 'Crua1985$',
                  'url': 'https://keystone.cern.ch/main/v2.0',
                  'tenant': 'IT Image Builder Tests',
                  'prefix': 'vcycle'}
        result = openstack.list(params)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertGreaterEqual(len(result['message']), 0)

        if len(result['message']) > 0:
            self.assertTrue('state' in result['message'][0])
            self.assertTrue('hostname' in result['message'][0])
            self.assertTrue('id' in result['message'][0])

    def test_list_incorrect_params(self):
        params = {'username': 'lvillaz',
                  'password': 'Crua1985$',
                  'url': 'https://keystone.cern.ch/main/v2.0',
                  'tenant': 'IT Image Builder Tests',
                  'prefix': 'vcycle'}
        result = openstack.list(params)
        self.assertEqual(result['status'], 'ERROR')

    def test_create(self):
        params = {'username': 'lvillazo',
                  'password': 'Crua1985$',
                  'url': 'https://keystone.cern.ch/main/v2.0',
                  'tenant': 'IT Image Builder Tests',
                  'image': '560499f4-0d40-439d-b720-e48fb61964a1',
                  'flavor': '20',
                  'user_data': 'IyEgL2Jpbi9iYXNoDQoNCmVjaG8gIkhvbGEi',
                  'key_name': 'lvillazo',
                  'hostname': 'testlvvcycle3'
                  }
        result = openstack.create(params)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['message']['hostname'], params['hostname'])

    def test_delete(self):
        params = {'username': 'lvillazo',
                  'password': 'Crua1985$',
                  'url': 'https://keystone.cern.ch/main/v2.0',
                  'tenant': 'IT Image Builder Tests',
                  'id': '9b340129-1217-476d-8cda-f86bb5117d3b'
                  }
        result = openstack.delete(params)
        self.assertEqual(result['status'], 'SUCCESS')

    def test_delete_not_exists(self):
        params = {'username': 'lvillazo',
                  'password': 'Crua1985$',
                  'url': 'https://keystone.cern.ch/main/v2.0',
                  'tenant': 'IT Image Builder Tests',
                  'id': '9b340129-1217-476d-8cda-f86bb5117d3'
                  }
        result = openstack.delete(params)
        self.assertEqual(result['status'], 'ERROR')

if __name__ == '__main__':
    unittest.main()
