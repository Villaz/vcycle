Welcome to Vcycle's documentation!
===================================

Few words: Vcycle is a VM lifecycle manager.

Ok...more words:

Vcycle is a VM lifecycle manager, it controls the creation and the destruction of the VMs in a hybrid cloud enviroment.
The management of the lifecycle is Job oriented. If there are jobs available to execute vcycle will create new VMs,
if not, no more VMs will be created.

Vcycle support the deploy of VMs in different clouds, including Openstack, Azure, DBCE , and OCCI.

Installation
-------------

Clone the repository from git:

.. code-block:: bash

   git clone -b new https://github.com/Villaz/vcycle.git

Create a configuration file and put it in /etc/vcycle/vcycle.conf

`See configuration
<configuration.html />`_.

Create your contextualization files and put them in /etc/vcycle/contextualization

`See how to create contextualization file
<user_data.html />`_.

Start vcycle!!

.. code-block:: bash

   python vcycle/main.py

or

.. code-block:: bash

   service vcycle start


Important Paths
----------------

**/etc/vcycle** : All configuration files will be here.

**/etc/vcycle/vcycle.conf** : The configuration file to use vcycle.

**/etc/vcycle/hostkeys/** : Good place to store the hostkeys.

**/etc/vcycle/auth_keys/** : Good place to store the public keys.

**/etc/vcycle/proxies/** : Folder to store authorization proxies (Uses with Occi).

**/etc/vcycle.conf**: If you're using the Legacy mode, this will be the configuration file.

**/etc/vcycle/contextualization/** : Folder were you must store your contextualization files.

**/var/lib/vcycle/user_data/**: If you're using the Legacy mode, this will will be the folder to store the contextualization files.

**/var/log/vcycle/** : All logs will be here.

Contents:

.. toctree::
   :maxdepth: 3

   configuration
   user_data
   docker
   api



Indices and tables
==================

* :ref:`genindex`
* :ref:`search`