Vcycle in Docker
==================


If you don't want to install all dependencies and vcycle code in your computer, docker could be a good option.

Vcycle allows you to install everything via Docker :-)

Steps
------

1. `Install docker in your computer`_

2. Download the vcycle container

.. code-block:: bash

    docker pull lvillazo/vcycle

3. Define the paths that you want to use to store:

* Cofiguration files
* Contextualization files
* Log files

4. Execute the docker container:

.. code-block:: bash

    docker run -d -v /etc/vcycle/:/etc/vcycle -v /var/log/vcycle:/var/log/vcycle lvillazo/vcycle

In this commmand we are saying:

 * The path /etc/vcycle in docker is linked to /etc/vcycle in the host.

  * The configuration file is /etc/vcycle/vcycle.conf

  * The contextualization files are in /etc/vcycle/contextualization

 * The path /var/log/vcycle in docker is linked to /var/log/vcycle in the host. (All logs are written there).

If you want to define a different location to the contextualization files, you should add:

.. code-block:: bash

    -v /etc/vcycle/contextualization:<path>


.. _Install docker in your computer: https://docs.docker.com/installation/