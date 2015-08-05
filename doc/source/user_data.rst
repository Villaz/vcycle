Create your Contextualization script
=====================================

Vcycle uses **jinja2** to create the contextualization files. ¿What does mean?, The contextualization files are templates!

The contextualization file in vcycle has three different parts:

- pre-Job. Here you must write all the dependencies and information that your job will need.
- job. The execution of your job.
- post-Job. The tasks to do ones the job has finished.


To create the contextualization file you only need to copy this template and complete it with your code:

.. code-block:: python

    {% extends "base_centos" %}

    {% block pre_job %}

        PUT YOUR CODE!!

    {% endblock %}

    {% block job %}

        HERE IS YOUR JOB!

    {% endblock %}

    {% block post_job %}
        PUT YOUR CODE!!
    {% endblock %}


Base template
---------------

Base template is the basic template to contextualize a VM. It has the code that allows the VM to comunicate with
vcycle, so you don't need to worry about this, you only need to worry about write your job code :-).

If you want to create a new base template, for example to support other OS, you need to copy the base_centos template
and adapt it to the new scenario.

.. code-block:: bash

    #!/bin/sh

    hostname {{id}}

    cat <<X5_EOF >/usr/share/sources
    export HOME=/root/
    export MONGO_DB={{db}}
    export SITE={{site}}
    export EXPERIMENT={{experiment}}
    X5_EOF

    chmod 777 /usr/share/sources

    function installClient {
		wget https://bootstrap.pypa.io/get-pip.py
		python get-pip.py

		#create python enviroment
		pip install virtualenv
		mkdir -p /usr/python-env
		virtualenv /usr/python-env/
		source /usr/python-env/bin/activate
		pip install wheel
		pip install pymongo==3.0.3
		pip install requests
		pip install python-geoip
		pip install python-geoip-geolite2
		pip install ipgetter
		pip install stomp.py
		pip install boto3
		deactivate

		cd /root
		git clone https://bitbucket.org/Villaz/infinity-client.git
		cd /root/infinity-client

		source /usr/python-env/bin/activate
		python /root/infinity-client/index_test.py -i {{id}} -t boot
	    python /root/infinity-client/index_test.py -i {{id}} -t heartbeat &
	    deactivate
    }

    echo 0 >/selinux/enforce
    yum -y install wget
    yum -y install git
    yum -y install python
    yum -y install apr
    yum -y install libconfuse

    #Don't remove
    source /usr/share/sources
    installClient

    {% block pre_job %}{% endblock %}

    #Don't remove
    source /usr/python-env/bin/activate
    python /root/infinity-client/index_test.py -i {{id}} -t start
    deactivate

    {% block job %}{% endblock %}

    {% block post_job %}{% endblock %}

    #Don't remove
    source /usr/python-env/bin/activate
    python /root/infinity-client/index_test.py -i {{id}} -t end
    deactivate

    sleep 30
    shutdown -h now