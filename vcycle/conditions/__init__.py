__author__ = 'luis'

from vcycle.connectors import CloudException


class DeleteBase(object):

    def __init__(self,
                 collection=None,
                 site="",
                 experiment="",
                 client=None,
                 info="",
                 logger=None):
        self.collection = collection
        self.site = site
        self.experiment = experiment
        self.client = client
        self.info = info
        self.logger = logger

    def execute_all(self, list_servers):
        import types
        servers = None

        for method in dir(self):
            if isinstance(getattr(self, method), types.MethodType) and not method.startswith('__') and method != 'execute_all':
                if self.logger is not None:
                    self.logger.debug("Executing %s" % method)
                if servers is None:
                    servers = getattr(self, method)(list_servers)
                else:
                    servers = getattr(self, method)(servers)
        return servers

    @staticmethod
    def process_list(vm_list, vm_deleted):
        return_list = []
        for vm in vm_list:
            delete = False
            for vm2 in vm_deleted:
                if vm['id'] == vm2['id']:
                    delete = True
                    break
            if not delete:
                return_list.append(vm)
        return return_list

    @staticmethod
    def execute(list_servers, collection=None, site="", experiment="", client=None, info="", logger=None):
        import os
        import glob
        servers = None
        modules = glob.glob(os.path.dirname(__file__)+"/*.py")
        for cls in [os.path.basename(f)[:-3] for f in modules if f.find("__") < 0 and f.find('test') < 0]:
            print cls
            module = __import__("conditions.%s" % cls)
            submodule = getattr(module, cls)

            delete = getattr(submodule, "Delete")
            obj = delete(collection=collection, site=site, experiment=experiment, client=client, info=info, logger=logger)
            try:
                if servers is None:
                    servers = obj.execute_all(list_servers)
                else:
                    servers = obj.execute_all(servers)
            except CloudException as ex:
                if logger is not None:
                    logger.warn(str(ex))
        return servers
