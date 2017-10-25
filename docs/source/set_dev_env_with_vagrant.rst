Setup development environment with Vagrant
==========================================

``Vagrantfile`` is provided in project root directory. To setup the
development environment, all you need is just to run

::

    vagrant up --provider virtualbox

Note if you're under proxy, then you need to modify Vagrantfile first by adding proxy

::

    config.proxy.http = "http://;proxy>:<port>"
    config.proxy.https = "http://<proxy>:<port>"

After ``vagrant`` succeeds to run the virtual machine, you will get a complete
environment to develop Nitrate,

* a Python virtual environment creatd at ``$HOME/nitrate-env/`` with all
  necessary dependecies installed.
 
* install all required Python dependencies

  ::

    cd /code
    sudo pip install -r requirements/base.txt
    sudo pip install -r requirements/devel.txt

* database is created in MariaDB and name is ``nitrate``. It's empty. Before
  hacking and running development server, remember to synchronize database
  from models. 
  MySQL user is 'nitrate' without a password.  

  ::

    ./manage.py migrate

* port forwarding. ``8000`` is mapped to ``8087`` in host.

* source code is mounted at ``/code``.

* Run development server

  ::

    ./manage.py runserver 0.0.0.0:8000

visit http://127.0.0.1:8087 with your favourite web browser.

* Create a user through web-interface

* In order to make it admin, hack MySQL query:
  ::
    mysql -u nitrate
    USE nitrate
    UPDATE auth_users SET is_staff=1,is_active=1,is_superuser=1 WHERE id=1

Happy hacking.
