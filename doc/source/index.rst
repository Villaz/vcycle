Welcome to Vcycle's documentation!
===============================

Few words: Vcycle is a VM lifecycle manager.

Ok...more words:

Vcycle is a VM lifecycle manager, it controls the creation and the destruction of the VMs in a hybrid cloud enviroment.
The management of the lifecycle is Job oriented. If there are jobs abai

managing them under the demand for jobs in a hybrid cloud environment.
Vcycle is a VM lifecycle manager that creates VMs on job demand in hybrid cloud. Vcycle support the deploy
of VMs in different clouds, including Openstack, Azure, DBCE , and OCCI.

Installation
-------------

Clone the respository from git:

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


Contents:

.. toctree::
   :maxdepth: 3

   intro
   api
   configuration
   user_data
   arch
   ec3
   templates
   faq
   about



Indices and tables
==================

* :ref:`genindex`
* :ref:`search`