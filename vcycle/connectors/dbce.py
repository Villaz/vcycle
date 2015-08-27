__author__ = 'Luis Villazon Esteban'

try:
    from connectors import CloudConnector, CloudException
except:
    from vcycle.connectors import CloudConnector, CloudException

import requests
import json
import base64
import urllib3

urllib3.disable_warnings()


class Dbce(CloudConnector):

    def __init__(self, **kwargs):
        """

        :param logger:
        :param kwargs:
        :param endpoint: URL to connect
        :param version: API version to use
        :param key: API Key
        """
        CloudConnector.__init__(self)
        self.params = kwargs
        if 'logger' in kwargs:
            self.logger = kwargs['logger']

    def list(self, prefix=None):
        """ Reads information from provider and returns a list of all deployed vms

        :param prefix: Only returns vms with the prefix in their hostname
        :type prefix: string
        :return List of VMs
        """
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'DBCE-ApiKey': self.params['key']}
        response = requests.get("%s/%s/machines" % (self.params['endpoint'], self.params['version']),
                                headers=headers,
                                verify=False)
        if response.status_code == 200:
            def process_vm(value):
                vm = {'id': value['id'], 'hostname': value['name'], 'state': value['state'].upper()}
                return vm

            content = response.json()
            return [process_vm(value) for value in response.json()['data'] if prefix is None or prefix in value['name']]
        else:
            raise CloudException(response.json)

    def delete(self, identifier):
        """Deletes a VM in the provider

        :param identifier: vm identifier
        """
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'DBCE-ApiKey': self.params['key']}

        response = requests.delete("%s/%s/machines/%s" % (self.params['endpoint'],
                                                          self.params['version'],
                                                          identifier),
                                   headers=headers,
                                   verify=False)
        return identifier

    def create(self, **kwargs):
        """Creates a new VM

        :param kwargs: Paramters to create the vm
        :param hostname: Name's machine
        :param image: Image to use to create the VM
        :param flavor: Flavor to use to create the VM
        :param network: Network to use to create the VM
        :param public_key: key to use to connect to VM
        :param user_data: User data to contextualize the VM
        :type user_data: string
        :return: Id , hostname and state of the created VM
        """
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'DBCE-ApiKey': self.params['key']}

        json_request = {
            'name': kwargs['hostname'],
            'platform': {
                'id': kwargs['platform']
            },
            'image': {
                'id': kwargs['image']
            },
            'configuration': {
                'id': kwargs['flavor']
            },
            'network': {
                'id': kwargs['network']
            }
        }

        if 'public_key' in kwargs:
            json_request['publicKey'] = base64.b64encode(kwargs['public_key'])
        if 'user_data' in kwargs:
            json_request['cloudConfig'] = base64.b64encode(kwargs['user_data'])

        response = requests.post("%s/%s/machines" % (self.params['endpoint'], self.params['version']),
                                 headers=headers,
                                 data=json.dumps(json_request),
                                 verify=False)
        if response.status_code == 201:
            info = response.json()['data']
            return {'id': info['id'], 'hostname': info['name'], 'state': info['state'].upper()}
        else:
            raise CloudException(response.json())

    def describe(self, identifier):
        """Returns a decription of the VM

        :param identifier: VM identifier
        :return: VM information in json format
        """
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'DBCE-ApiKey': self.params['key']}

        response = requests.get("%s/%s/machines/%s" % (self.params['endpoint'],
                                                       self.params['version'],
                                                       identifier),
                                headers=headers,
                                verify=False)

        if response.status_code == 200:
            return  response.json()
        else:
            raise CloudException(response.json()['message'])

    def add_network_address(self, identifier):
        """Adds a public network to a given VM

        :param identifier: Identifier of the VM
        :return: A description of the VM with the new network
        """
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'DBCE-ApiKey': self.params['key']}

        requests.post("%s/%s/machines/%s/actions/assign-public-ip" %(self.params['endpoint'],
                                                                     self.params['version'],
                                                                     identifier),
                      headers=headers,
                      verify=False)
        return self.describe(identifier)

def create(**kwargs):
    return Dbce(**kwargs)