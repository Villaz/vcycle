__author__ = 'Luis Villazon Esteban'

from cloudconnector import CloudConnector, CloudException
import subprocess
import json
import uuid
from os import kill
from signal import alarm, signal, SIGALRM, SIGKILL


class Alarm(Exception):
    pass


def alarm_handler(signum, frame):
    raise Alarm


class Azure(CloudConnector):

    def __init__(self, **kwargs):
        """

        :param kwargs: Dictionary with information about azure connection
        :param subscription: Subscription id used to connect with azure
        :param pfx: Certificate use to grant access to VMs
        """
        CloudConnector.__init__(self)
        self.params = kwargs

    def list(self, prefix):
        """ Reads information from provider and returns a list of all deployed vms

        :param prefix: Only returns vms with the prefix in their hostname
        :type prefix: string
        :return List of VMs
        """
        vms = []
        process = subprocess.Popen(['/usr/local/bin/azure', 'vm','list',
                                           '-s', self.params['subscription'],
                                           '--json'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        signal(SIGALRM, alarm_handler)
        alarm(30)
        try:
            output, error = process.communicate()
            alarm(0)
        except Alarm:
            kill(process.pid, SIGKILL)
            raise CloudException("Error retrieving list")

        if len(error) > 0:
            raise CloudException(error)
        else:
            output = json.loads(output)
        for value in output:
            if prefix not in value['VMName']:
                continue
            vm = {'id': value['VMName'],
                  'hostname': value['VMName']}
            if value['InstanceStatus'] in ['Unknown', 'CreatingVM', 'StartingVM', 'CreatingRole', 'StartingRole',
                                           'ReadyRole', 'BusyRole', 'Preparing']:
                vm['state'] = 'CREATING'
            elif value['InstanceStatus'] in ['StoppingRole', 'StoppingVM', 'DeletingVM', 'StoppedVM', 'RestartingRole']:
                vm['state'] = 'STOPPED'
            else:
                vm['state'] = 'ERROR'
            vms.append(vm)
        return vms

    def delete(self, identifier):
        """Deletes a VM in the provider

        :param identifier: vm identifier
        """
        process = subprocess.Popen(['/usr/local/bin/azure', 'vm', 'delete', identifier,
                                        '-s', self.params['subscription'],
                                        '--json', '-q'],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        signal(SIGALRM, alarm_handler)
        alarm(60)
        try:
            output, error = process.communicate()
            alarm(0)
        except Alarm:
            kill(process.pid, SIGKILL)
            raise CloudException("Error deleting VM %s" % identifier)

        if len(error) > 0:
            raise CloudException(error)
        return

    def create(self, **kwargs):
        """Creates a new VM

        :param kwargs: Paramters to create the vm
        :param hostname: Name's machine
        :param location: Location where VM will be created.
        :param image: Image to use to create the VM
        :param flavor: Flavor to use to create the VM
        :param pfx: location on local disk of the certificate to upload, must be in pfx format.
        :param username: Username in the VM
        :param password: Password in the VM
        :param user_data: User data to contextualize the VM
        :type user_data: string
        :return: Id , hostname and state of the created VM
        """
        def _create(command, aux_file):
            import os
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            signal(SIGALRM, alarm_handler)
            alarm(600)
            try:
                output, error = process.communicate()
                alarm(0)
            except Alarm:
                kill(process.pid, SIGKILL)
                raise CloudException("Error creating VM %s" % kwargs['hostname'])

            if 'logger' in kwargs:
                kwargs['logger'].info(output)
                if len(error) > 0:
                    kwargs['logger'].error(error)
            os.remove(aux_file)

        if 'user_data' in kwargs:
            aux_file = "/tmp/%s" % str(uuid.uuid4())
            open(aux_file, 'w').write(kwargs['user_data'])
            custom_data = aux_file
        else:
            custom_data = None

        if 'logger' in kwargs:
            kwargs['logger'].debug("Creating service %s" % kwargs['hostname'])

        #Creates a service. If the creation of the service fails, a exception is raised
        self.__create_service(kwargs['hostname'], kwargs['location'])

        try:
            if 'pfx' in kwargs:
                if 'logger' in kwargs:
                    kwargs['logger'].debug("Adding certificate to service")
                thumbprint = self.__add_certificate(kwargs['hostname'], kwargs['pfx'])
        except CloudException,e:
            if 'logger' in kwargs:
                kwargs['logger'].error("Error storing certificate, the VM %s will be created witout cert", kwargs['hostname'])

        if 'logger' in kwargs:
            kwargs['logger'].debug("Creating the VM %s" % kwargs['hostname'])
            kwargs['logger'].debug(" WARNING: Azure creates the VM async!")

        command = ['/usr/local/bin/azure', 'vm', 'create',
                   '-e', '22',
                   '--json',
                   '--location', kwargs['location'],
                   '-s', self.params['subscription'],
                   '-z', kwargs['flavor'],
                   '-t', thumbprint]

        if custom_data is not None:
            command.append('-d')
            command.append(custom_data)
        command.append(kwargs['hostname'])
        command.append(kwargs['image'])
        command.append(kwargs['username'])
        command.append(kwargs['password'])

        import multiprocessing
        multiprocessing.Process(target=_create, args=(command, aux_file,)).start()
        return {'id': kwargs['hostname'], 'hostname': kwargs['hostname'], 'state': 'CREATING'}

    def __create_service(self, name, location):
        """Creates a new service

        :param name: Name of the service
        :param location: Location where the service will be created
        :raise CloudException

        """
        command = ['/usr/local/bin/azure', 'service', 'create',
                   '--location', location,
                   '-s', self.params['subscription'],
                   name]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        signal(SIGALRM, alarm_handler)
        alarm(60)
        try:
            output, error = process.communicate()
            alarm(0)
        except Alarm:
            kill(process.pid, SIGKILL)
            raise CloudException("Error creating service %s" % name)
        if len(error) > 0:
            raise CloudException(error)

    def __add_certificate(self, name, certificate):
        """Adds a certificate to the service

        :param name: Name of the service to links the certificate
        :param certificate: location on local disk of the certificate to upload, must be in pfx format.
        :return: The thumbprint of the uploaded certificate
        """
        command = ['/usr/local/bin/azure', 'service', 'cert', 'create',
                   '-s', self.params['subscription'],
                   name,
                   certificate]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        signal(SIGALRM, alarm_handler)
        alarm(60)
        try:
            output, error = process.communicate()
            alarm(0)
        except Alarm:
            kill(process.pid, SIGKILL)
            raise CloudException("Error creating certificate to service %s" % name)
        if len(error) > 0:
            raise CloudException(error)

        command = ['/usr/local/bin/azure', 'service', 'cert', 'list',
                   '--serviceName', name,
                   '-s', self.params['subscription'], '--json']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        signal(SIGALRM, alarm_handler)
        alarm(60)
        try:
            output, error = process.communicate()
            alarm(0)
        except Alarm:
            kill(process.pid, SIGKILL)
            raise CloudException("Error retrieving certificate from service %s" % name)
        if len(error) > 0:
            raise CloudException(error)
        return json.loads(output)[0]['thumbprint']


def create(**kwargs):
    return Azure(**kwargs)