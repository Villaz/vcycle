__author__ = 'Luis Villazon Esteban'

import ssl

ssl._create_default_https_context = ssl._create_unverified_context


class CloudException(Exception):
    pass


class CloudConnector(object):

    def __init__(self, logger=None, **cloud_info):
        self.params = cloud_info

    def list(self, prefix):
        """ Reads information from provider and returns a list of all deployed vms

        :param prefix: Only returns vms with the prefix in their hostname
        :type prefix: string
        :return List of VMs
        """
        pass

    def delete(self, identifier):
        """Deletes a VM in the provider

        :param identifier: vm identifier
        """
        pass

    def create(self, **kwargs):
        """Creates a new VM

        :param kwargs: Parameter to create the VM
        :return: VM description
        """
        pass

