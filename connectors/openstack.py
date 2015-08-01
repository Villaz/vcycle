__author__ = 'Luis Villazon Esteban'

from connectors import CloudConnector, CloudException
from novaclient.client import Client
import os
import uuid


class Openstack(CloudConnector):

    def __init__(self, **kwargs):
        """
        :param kwargs: Dictionary with information about azure connection
        :param username: Openstack username
        :param password: Openstack password
        :param tenant: Tenant to connect
        :param endpoint: Url to connect
        """
        CloudConnector.__init__(self)
        self.params = kwargs
        if 'logger' in kwargs:
            self.logger = kwargs['logger']
        self.client = Client('2',
                             username=self.params['username'],
                             api_key=self.params['password'],
                             project_id=self.params['tenant'],
                             auth_url=self.params['endpoint'])

    def list(self, prefix):
        """ Reads information from provider and returns a list of all deployed vms
        :param prefix: Only returns vms with the prefix in their hostname
        :type prefix: string
        :return List of VMs
        """
        try:
            serversList = self.client.servers.list(detailed=True)
        except Exception,e:
            raise CloudException(e.message)

        servers = []
        for server in serversList:
            if prefix in server.name:
                serv = {'id': server.id, 'hostname': server.name, 'state':None}
                if server.status in [u'BUILDING', u'BUILD', u'ACTIVE']:
                    serv['state'] = 'CREATING'
                elif server.status in [u'PAUSED', u'STOPPED', u'SUSPENDED', u'SHUTOFF']:
                    serv['state'] = 'STOPPED'
                else:
                    serv['state'] = 'ENDED'
                servers.append(serv)
        return servers

    def delete(self, identifier):
        """Deletes a VM in the provider
        :param identifier: vm identifier
        """
        try:
            self.client.servers.delete(identifier)
        except Exception, e:
            if 'Instance could not be found' in e.message:
                return
            else:
                raise CloudException(e.message)

    def create(self, **kwargs):
        """
        Creates a new VM
        :param kwargs: Paramters to create the vm
        :param hostname: Name's machine
        :param image: Image to use to create the VM
        :param flavor: Flavor to use to create the VM
        :param key_name: Name of the key to use to connect to VM
        :param user_data: User data to contextualize the VM
        :type user_data: string
        :return: Id , hostname and state of the created VM
        """
        server = self.client.servers.create(kwargs['hostname'],
                                            kwargs['image'],
                                            kwargs['flavor'],
                                            key_name=kwargs['key_name'],
                                            userdata=kwargs['user_data'])

        info = {'id': server.id, 'hostname': server.name, 'state': server.status}
        if info['state'] in ['BUILDING', 'BUILD', 'ACTIVE']:
            info['state'] = 'CREATING'
        elif info['state'] in ['PAUSED','STOPPED','SUSPENDED','SHUTOFF']:
            info['state'] = 'STOPPED'
        else:
            info['state'] = 'ENDED'
        return info


def create(**kwargs):
    return Openstack(**kwargs)
