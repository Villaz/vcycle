__author__ = 'Luis Villazon Esteban'

import yaml
import os.path
import ConfigParser


def load(path=u"/etc/vcycle/vcycle.conf", logger=None):
    if os.path.isfile(path):
        configuration = yaml.load(open(path))
    else:
        configuration = process_legacy_configuration_file('/etc/vcycle.conf')

    for experiment in configuration['vcycle']['experiments']:
        for site in configuration['vcycle']['experiments'][experiment]['sites']:
            parse_params(configuration, site, experiment, logger)
    return configuration


def parse_params(configuration, site, experiment, logger=None):
    for option in configuration['vcycle']['experiments'][experiment]:
        if option == 'sites':
            continue
        configuration['vcycle']['experiments'][experiment]['sites'][site][option] = configuration['vcycle']['experiments'][experiment][option]

    configuration['vcycle']['experiments'][experiment]['sites'][site]['db'] = configuration['vcycle']['db']['mongo']['url']
    connector = configuration['vcycle']['experiments'][experiment]['sites'][site]['connector']

    #load files
    for option in configuration['vcycle']['experiments'][experiment]['sites'][site]:
        aux = configuration['vcycle']['experiments'][experiment]['sites'][site]
        if isinstance(aux[option], basestring) and aux[option].startswith('file://'):
            file = aux[option].replace('file://', '')
            if os.path.isfile(file):
                configuration['vcycle']['experiments'][experiment]['sites'][site][option] = open(file).read()
            else:
                if logger is not None:
                    logger.warn("File %s for option %s in %s:%s not exists.", file, option, experiment, site)



def process_legacy_configuration_file(path):
    parser = ConfigParser.RawConfigParser()
    parser.read(path)

    experiments = {}
    connectors = {}
    mongo = {}

    for spaceSectionName in parser.sections():
        parts = [part.rstrip() for part in spaceSectionName.split(" ")]
        if 'db' in parts[0]:
            mongo['mongo'] = {'url': parser.get(spaceSectionName,'url').replace("'", "").replace("\"", "")}
        if 'tenancy' in parts[0]:
            connectors[parts[1]] = {}
            experiments[parts[2]] = {}
            name = parts[2]
            for item in parser.items(spaceSectionName):
                if item[0] == 'max_machines':
                    experiments[name]['max_machines'] = item[1]
                else:
                    if item[0] == 'url':
                        connectors[parts[1]]['endpoint'] = item[1].replace("'", "").replace("\"", "")
                    else:
                        connectors[parts[1]][item[0]] = item[1].replace("'", "").replace("\"", "")
        elif 'vmtype' in parts[0]:
            experiment = parts[2]
            site = parts[1]
            if parts[2] in experiments:
                experiments[parts[2]]['sites'] = {parts[1]: {'connector': parts[1], 'prefix': "vcycle-%s" % site}}
                experiments[parts[2]]['queue'] = parts[-1]
                experiments[parts[2]]['user_data'] = "file:///var/lib/vcycle/user_data/%s:%s:%s" % (parts[1], parts[2], parts[-1])
                for item in parser.items(spaceSectionName):
                    if 'max_wallclock_seconds' in item[0]:
                        experiments[experiment]['sites'][site]['wall_time'] = int(item[1].replace("'", "").replace("\"", ""))
                    elif 'heartbeat_seconds' in item[0]:
                        experiments[experiment]['sites'][site]['heartbeat'] = int(item[1].replace("'", "").replace("\"", ""))
                    elif 'fizzle_seconds' in item[0]:
                        experiments[experiment]['sites'][site]['boot_time'] = int(item[1].replace("'", "").replace("\"", ""))
                    elif 'backoff_seconds' in item[0]:
                        experiments[experiment]['sites'][site]['start_time'] = int(item[1].replace("'", "").replace("\"", ""))
                    elif 'image_name' in item[0]:
                        experiments[experiment]['sites'][site]['image'] = item[1].replace("'", "").replace("\"", "")
                    elif 'flavor_name' in item[0]:
                        experiments[experiment]['sites'][site]['flavor'] = item[1].replace("'", "").replace("\"", "")
                    elif 'root_key_name' in item[0]:
                        experiments[experiment]['key_name'] = item[1].replace("'", "").replace("\"", "")
                    else:
                        experiments[experiment]['sites'][site][item[0]] = item[1].replace("'", "").replace("\"", "")

    return {'vcycle': {'db': mongo, 'connectors': connectors, 'experiments': experiments}}
