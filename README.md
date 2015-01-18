# Heroes of the Storm Replay Parser 
Web service that returns a JSON description of a *.StormReplay file from Blizzard's game Heroes of the Storm. Developed by Karl Gluck.

This code is built to be deployed to a Heroku instance, but can be run locally with Ubuntu on either a virtual or a dedicated machine.

This project is based on code from:
 * [S2Protocol](https://github.com/Blizzard/s2protocol)
 * [SC2Reader](http://sc2reader.readthedocs.org/en/latest/)
 * [mpyq](https://github.com/eagleflo/mpyq)

It uses the following technologies:
 * [Python programming language](https://www.python.org/)
 * [Django web framework](https://www.djangoproject.com/)
 * [Celery distributed task queue](http://www.celeryproject.org/)
 * [Redis key-value data store](http://redis.io/)
 * [Heroku cloud application platform](https://www.heroku.com/)
 * [Amazon S3](http://aws.amazon.com/s3/) for production API replay file & result storage
 * [Boto](https://github.com/boto/boto)

Special thanks to Ben, the admin of [HOTS Logs](http://www.hotslogs.com), for helping me figure out the GameEvents binary format!

## SECURITY WARNING

This code is insecure because it is in Django developer mode. I'm still developing this library so I don't have the production configuration set up. If you want to get started right now, fix this yourself before deploying anywhere public.

## Setup for Local Development

This server is intended to run on Linux and was developed on Ubuntu 14.04.1 LTS. I have gotten parts of it to run on Windows but it requires some tinkering and a lot of installed apps. It's *much* easier to just develop in a virtual machine with [Ubuntu](http://www.ubuntu.com) and [VMware Player](http://www.vmware.com/products/player). VMware Player is free, by the way. The 'trial' only applies if you activate pro features, which we don't need.

To get started, grab a copy of this repository:

```
git clone https://github.com/karlgluck/heroes-of-the-storm-replay-parser.git
```

If you haven't already, [install the Heroku Toolbelt](https://toolbelt.heroku.com/) and [get a Redis server running](http://redis.io/topics/quickstart).

Follow [these instructions on Heroku](https://devcenter.heroku.com/articles/getting-started-with-python#declare-app-dependencies) to set up your environment for a local copy of a Python server.

**Note:** When running `pip install` on Ubuntu for the first time, you may run into an [error with psycops](http://stackoverflow.com/questions/5420789/how-to-install-psycopg2-with-pip-on-python). Run `sudo apt-get install libpq-dev python-dev` to fix it.

Wait for installation to complete. Start up the Redis server in another terminal:

```
redis-server
```

**Note:** The first time you start `redis-server`, it may complain about two things that [will affect latency](http://redis.io/topics/latency). Fix them if it does:
* vm.overcommit_memory should be 1
* Transparent huge pages must be disabled

Once Redis is running, launch a Celery instance:

```
foreman start worker
```

Next, launch the replay parser web server using Foreman (the next step from the Heroku tutorial):

```
foreman start web
```

If you visit `http://localhost:5000` with your browser, the app will now be running. If you're running inside a virtual machine like I suggested, only the browser inside the VM will resolve localhost. It is possible to access the server from your host computer by using `ifconfig` to find the VM's ip address and typing `[ip]:5000` into the host's browser's address bar.

## Setup for Production Deployment

### Environment Variables 

You will need to set the following environment variables. In Heroku you can set them as 'config vars' in the panel or with the Toolbelt command `heroku config set VAR=VALUE`. For local deployment, Foreman can read these from the `.env` file in the root of your project. Do not check in the `.env` file!

```
AWS_ACCESS_KEY_ID=<Amazon Web Services user access key>
AWS_SECRET_ACCESS_KEY=<Amazon Web Services user secret signing key>
AWS_BUCKET_NAME=<Your bucket on Amazon S3>
```

### Amazon Setup

The bucket you create for storing replays should have the following CORS configuration:

```
<?xml version="1.0" encoding="UTF-8"?>
<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <CORSRule>
        <AllowedOrigin>*</AllowedOrigin>
        <AllowedMethod>GET</AllowedMethod>
        <AllowedMethod>POST</AllowedMethod>
        <AllowedMethod>PUT</AllowedMethod>
        <AllowedMethod>HEAD</AllowedMethod>
        <AllowedHeader>*</AllowedHeader>
    </CORSRule>
</CORSConfiguration>
```

The access and secret keys from above come from an Amazon user that you create for this project. DO NOT use your Amazon account root credentials and NEVER add these values to any public repository (don't check in your `.env` file, for example). Bad things that cost you a lot of money can happen if someone gets a hold of your secret key. You have been warned!

The user needs to have permissions to access your bucket. To do this:
* Go to your Security Credentials on AWS
* Go into the IAM users panel
* Create a new user
* Download a copy of your user's access credentials to get the access key ID and secret access key
* Hit Attach User Policy
* Select the Policy Generator
* On the Edit Permissions page, pick `Allow`, `AWS Service`=`Amazon S3`, and check the actions:
    * `GetObject`
    * `GetObjectAcl`
    * `PutObject`
    * `PutObjectAcl`
* For `Amazon Resource Name` enter `arn:aws:s3:::<bucket>/*` with `<bucket>` replaced by the name of your bucket
* Save



## Todo List

* Redo API design and make its operation clear / not hard-coded
* Document global environment variables
* API keys for request rate limiting
* Protocol version 29666 (circa April 2014)
* Protocol version 30027 (circa May 2014)
* Protocol version 31566 (circa August 2014)
* Protocol version 31948 (circa September 2014)
* Protocol version 32524 (circa October 2014)

