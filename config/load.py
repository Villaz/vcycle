__author__ = 'Luis Villazon Esteban'

import legacy
import yaml
import os.path

def load_configuration(logger=None):
    if os.path.isfile('../conf/infinity.conf'):
    #if os.path.isfile('/etc/vcycle/vcycle.conf'):
        try:
            return yaml.load(open('../conf/infinity.conf'))
        except Exception as ex:
            if logger is not None:
                logger.error(str(ex))
    else:
        return legacy.process_legacy_configuration_file('../conf/legacy.conf')