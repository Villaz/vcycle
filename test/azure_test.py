__author__ = 'Luis Villazon Esteban'

import unittest
import azure

class AzureTest(unittest.TestCase):

    def test_list(self):
        params = {
            'connector':{'subscription': "baaf1202-15a5-4350-8c87-d13839de2d85"},
            'prefix': 'vcycle-test'
        }

        result = azure.list(params)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertGreaterEqual(len(result['message']), 0)

        if len(result['message']) > 0:
            self.assertTrue('state' in result['message'][0])
            self.assertTrue('hostname' in result['message'][0])
            self.assertTrue('id' in result['message'][0])

    def test_list_incorrect_params(self):
        params = {
            'subscription': "baaf1202-15a5-4350-8c87-d13839de2d8",
            'prefix': 'vcycle-test'
        }
        result = azure.list(params)
        self.assertEqual(result['status'], 'ERROR')

    def test_create(self):
        params = {
            'connector':{'subscription': 'baaf1202-15a5-4350-8c87-d13839de2d85', 'pfx': "/Users/luis/Documents/azure/cert.pfx"},
            'name': 'vcycle-test-123',
            'flavor': 'Basic_A1',
            'image': 'vcycle-azure',
            #'image': 'b39f27a8b8c64d52b05eac6a62ebad85__Ubuntu-14_10-amd64-server-20150708-en-us-30GB',
            'location': 'West Europe',
            'username':'azureuser',
            'password':'Espronceda1985$',
            'user_data': 'IyEvYmluL2Jhc2gNCg0KZWNobyAiSG9sYSI='
        }
        result = azure.create(params)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['message']['hostname'], params['name'])

    def test_delete(self):
        params = {
            'connector':{'subscription': 'baaf1202-15a5-4350-8c87-d13839de2d85'},
            'name': 'vcycle-test-123'
        }
        result = azure.delete(params)
        self.assertEqual(result['status'], 'SUCCESS')

    def test_delete_not_exists(self):
        params = {
            'connector':{'subscription': 'baaf1202-15a5-4350-8c87-d13839de2d85'},
            'name': 'vcycle-test-123'
        }
        result = azure.delete(params)
        self.assertEqual(result['status'], 'ERROR')

if __name__ == '__main__':
    unittest.main()
