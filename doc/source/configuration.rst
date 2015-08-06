Configure Vcycle
===============================

Vcycle uses a YAML file format to define its settings.


How looks like?
-----------------------------
.. code-block:: yaml

    vcycle:
      db:
        mongo:
          url: ""
          database: ""
          collection: ""
          capped_collection: ""

      ganglia:
        ganglia-xxx:
          host: ""
          conf: ""

      connectors:
        azure-win:
          type: "azure"
          subscription: ""


      experiments:
          COOL-EXPERIMENT:
            experiment: "cool"
            hostkey: ""
            authorized_keys: ""
            ganglia: ""
            user_data: ""
            queue: ""
            username: ""
            password: ""
            pfx: ""

            sites:
              SITE-TO-AZURE:
                connector: "azure"
                prefix: "vcycle-azure"
                max_machines: "2"
                image: ""
                flavor: ""
                location: ""
                boot_time: 100
                start_time: 100
                heartbeat: 700
                wall_time: 20000

Database
---------
At the moment Vcycle only works with MongoDB, but who knows, maybe in the future we'll add support to new one!.
The DB is used by vcycle to retrieve information about the state of the deployed VMs, and also is used by the
VMs to update their own information. **IMPORTANT** the DB port must be open to internet!.

.. code-block:: yaml

    db:
      mongo:
        url: "mongodb://<user>:<password>@<host>"
        database: "database_name"
        collection: "collection_to_store_vm_information"
        capped_collection: "collection_to_store_the_messages_send_by_vms"



Ganglia
---------

This key is only used if you want monitor your VMs.
You can define as many ganglia servers you want, and attach then to the different experiments.

For each ganglia server you need to specify:

- host : Where is ganglia? (without http and www, only the host).
- conf : The URL to the configuration file, the configuration file has a JSON format with the name of the clusters and the port they used to retrieve the information.

.. code-block:: yaml

  ganglia:
    ganglia-1:
      host: "ganglia_serv1.com"
      conf: "http://ganglia_serv1.com/file.conf"
    ganglia-2:
      host: "ganglia_serv2.com"
      conf: "http://ganglia_serv2.com/file.conf"

Connectors
-----------

Vcycle supports: Azure, Openstack, Occi, DBCE.

In connectors, you have to define all the connectors that you are going to use in your experiments.
Each connector has it owns parameters, so let go:

Azure
```````

.. code-block:: yaml

  my-azure:
    type: "azure"
    subscription: "<your_subscription>"

DBCE
``````

.. code-block:: yaml

  dbce:
    type: "dbce"
    endpoint: "https://api.cloud.exchange" #Right now it is the only endpoint
    key: "<your_api_key>"
    version: "v0" #Always v0

Openstack
```````````

.. code-block:: yaml

  local-openstack:
    type: "openstack"
    endpoint: "<keystone_url>"
    username: "<username>"
    password: "<password>"
    tenant: "<tenant>"
    key_name: "<key_name>" #This parameter is optional

Occi
``````

.. code-block:: yaml

  occi-provider:
    type: "occi"
    url: "<url>"
    proxy: "<local_path_to_proxy>"


Experiments
-----------

In this space you will define all the experiments that you will run, and also all the sites inside the experiment.
In the experiment you need to define the contextualization script that you want to use to contextualize your VMs. Also
you can define your own parameters to use in the contextualization.

.. code-block:: yaml

  experiments:
    HALF-LIFE-3:
        user_data: "file://<path>"
        ganglia: "ganglia-dbce" #If you use ganglia, you need to put here the identifier
        custom-param: "Gordooon!"

        sites: #Your providers

**Notice that the experiment name must be in CAPITAL LETTERS!**

Sites
-----------

Sites are the providers that you will use to create VMs and execute your jobs.
In this part you need to define all the needed parameters to create the VMs.
The mandatory parameters are: connector, prefix, image, flavor, max_machines.
Like in experiment section, you are free to add new parameters.

**Notice that the site name must be in CAPITAL LETTERS!**

.. code-block:: yaml

  sites:
    ONE:
      connector: "dbce" # You need to introduce the connector name
      prefix: "vcycle-xyz" #The prefix to use to monitor the machines, all machines will be created with the prefix and the creation timestamp
      max_machines: "1" #The maximum VMs to create in the site
      flavor: "<flavor_vm>"
      image: "<image_vm>"
      boot_time: 800 # Time in seconds between the machine is created and It starts
      start_time: 10000 #Time in seconds between the machine starts and the job starts
      heartbeat: 700 #Time in seconds between heartbearts.
      wall_time: 20000 #Maximum vm lifetime.


Legacy Configuration
======================

Vcycle also supports the old vcycle configuration file.

The file looks like:

.. code-block:: python

  [db mongo]
  url = "mongodb://xxx"


  [tenancy dbce dbceExperiment]
  type = "dbce"
  url = "https://api.cloud.exchange"
  key = "XYZ"
  version = "v0"
  max_machines = 2

  [vmtype dbce dbceExperiment DBCE]
  max_machines = 2
  backoff_seconds = 1000
  fizzle_seconds = 1000
  max_wallclock_seconds = 200000
  heartbeat_seconds = 9500
  platform: "1"
  flavor_name: ""
  image_name: ""
  network: ""
  public_key: ""



In this configuration file you need to see a couple of things:

- The file must be in /etc/vcycle.conf
- The user_data files are stored in /var/lib/vcycle/user_data/ with name TENANT:EXPERIMENT:QUEUE.
- The [db mongo] section is mandatory.
- The tenancy section initializes the name of the tenant and the experiment.
- The vmtype section indicates the name of the tenant, the name of the experiment and the QUEUE to use in the experiment

In this case, for example, we are telling to vcycle that the vmtype with the tenancy dbce and  with experiment dbceExperiment
will execute a job in DBCE queue.

**IMPORTANT: user_data is a text file, the template user_data is not supported in legacy mode.**