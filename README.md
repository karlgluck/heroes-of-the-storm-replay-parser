# Heroes of the Storm Replay Parser

Web service that returns a JSON description of a *.StormReplay file from Blizzard's new game Heroes of the Storm

This code is built to be deployed to a Heroku instance, but can be run locally with foreman. See the [Heroku Getting Started](https://devcenter.heroku.com/articles/getting-started-with-python#introduction) for more information.

This project is based on code from:
 * [S2Protocol](https://github.com/Blizzard/s2protocol)
 * [SC2Reader](http://sc2reader.readthedocs.org/en/latest/)
 * [mpyq](https://github.com/eagleflo/mpyq)

Special thanks to Ben of [HOTS Logs](http://www.hotslogs.com) for helping me figure out the new GameEvents format!


## Setup

This server is intended to run on Linux and was developed on Ubuntu 14.04.1 LTS. I have gotten it to run on Windows just fine but it requires some tinkering and a lot of installed apps. It's *much* easier to just develop in a virtual machine with [Ubuntu](http://www.ubuntu.com) and [VMware Player](http://www.vmware.com/products/player).

To get started, grab a copy of this repository:

```
git clone https://github.com/karlgluck/heroes-of-the-storm-replay-parser.git
```

If you haven't already, install the [Heroku Toolbelt](https://toolbelt.heroku.com/).

Follow [these instructions on Heroku](https://devcenter.heroku.com/articles/getting-started-with-python#declare-app-dependencies) to set up your environment for a local copy of a Python server.

**Note:** When running `pip install` on Ubuntu for the first time, you may run into an [error with psycops](http://stackoverflow.com/questions/5420789/how-to-install-psycopg2-with-pip-on-python). Run `sudo apt-get install libpq-dev python-dev` to fix it.

Once installation is complete, start up the server and test it using Foreman (the next step from the Heroku tutorial):

```
foreman start web
```

If you visit `http://localhost:5000` with your browser, the app will now be running. If you're running inside a virtual machine like I suggested, only the browser inside the VM will resolve localhost. It is possible to access the server from your host computer by using `ifconfig` to find the VM's ip address and typing `[ip]:5000` into the host's browser's address bar.
