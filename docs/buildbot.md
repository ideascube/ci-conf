# Buildbot Deployment

We use [Buildbot](https://buildbot.net) to pilot our continuous integration
system.

We have two types of machines deployed:

* A single **master**, piloting the work to be done
* Multiple **workers**, actually doing the work

The rest of this documentation is structured in a way that reflects this.

**Note:** When following this documentation, you will find a few variables
here and there. You must replace them by their actual values. For example, the
`$arch` variable appears several times, and must be replaced by something like
`amd64` or `armhf`, depending on the actual architecture of the worker.

## Deploying a worker machine

We currently have only one worker machine:

* an `amd64` machine (which also runs the master)

### Pre-requisites

A few things need to be installed before we start:

```
# apt install virtualenv git
```

It is also necessary to create a new user which will run Buildbot:

```
# useradd -c "Buildbot user" -d /srv/buildbot -m -s /bin/bash buildbot
```

### Deploying the Buildbot worker

Unfortunately, the Debian packages for buildbot are too old, so we will use
the latest version (as of this writing, it is version 0.8.12) in a virtual
environment.

As the `buildbot` user, run the following commands to install the Buildbot
worker code:

```
$ virtualenv venv
$ . ./venv/bin/activate
$ pip install "buildbot-slave==0.8.12"
```

Next, create the worker:

```
$ buildslave create-slave -r slave-$arch $master_host:master_port slave-$arch $password
```

In the above command, some variables are important to explain:

* `$master_host` is the host name or IP address of the machine where the
    Buildbot master runs (or will run). It could be `localhost` if the worker
    being created runs on the same machine as the master.
* `master_port` is the private protocol port of the Buildbot master. By
    default this is `9989`, but it can be changed when configuring the master
    (see below)
* `password` is the password for this worker to authenticate with the master.
    Remember it, you will need to specify it in the master's configuration.

Next, edit the `slave-$arch/info/admin` and `slave-$arch/info/host` files.

Finally, install the `buildbot-worker@.service` file provided in this
repository, in the `/etc/systemd/system/` folder.

Then, start and enable the new worker service:

```
# systemctl daemon-reload
# systemctl start buildbot-worker@$arch.service
# systemctl enable buildbot-worker@$arch.service
# systemctl status buildbot-worker@$arch.service
```

At this point, your worker is ready to accept tasks.

## Deploying the master machine

At the moment, our master runs on the same machine as our amd64 worker.

### Pre-requisites

**Note:** If your master runs on the same machine as an already configured
worker, you can skip some of this as you have already done it when deploying
the worker.

A few things need to be installed before we start:

```
# apt install virtualenv
```

It is also necessary to create a new user which will run Buildbot:

```
# useradd -c "Buildbot user" -d /srv/buildbot -m -s /bin/bash buildbot
# passwd buildbot
```

### Deploying the Buildbot master

Unfortunately, the Debian packages for buildbot are too old, so we will use
the latest version (as of this writing, it is version 0.8.12) in a virtual
environment.

**Note:** If your master runs on the same machine as an already configured
worker, you should already have a virtual environment ready. It is
perfectly fine to reuse it.

As the `buildbot` user, run the following commands to install the Buildbot
master code:

```
$ virtualenv venv
$ . ./venv/bin/activate
$ pip install "buildbot==0.8.12"
```

Next, create the master:

```
$ buildbot create-master -r master
```

You now need to configure the master, with the `master/master.cfg` file.

This repository includes the configuration file we actually use for our CI
deployment (without the passwords and secrets of course).

A few important things from that file.

First, the project identity:

```
c['title'] = 'Ideascube'
c['titleURL'] = 'https://github.com/ideascube'
c['buildbotURL'] = 'http://buildbot.ideascube.org/'
```

Next, let the master know about the workers:

```
c['slaves'] = [
    buildslave.BuildSlave('slave-$arch', '$password'),
    ]
```

You must add one `buildslave.BuildSlave(...)` line for **each** worker you
have already deployed.

In the above configuration snippet, `$password` is the password you supplied
when creating the worker. It will let the master authenticate the worker.

One more thing about the workers, the `master.cfg` file contains this snippet:

```
c['protocols'] = {'pb': {'port': 9989}}
```

This is the private protocol port of the Buildbot master, to which the
Buildbot workers will connect. It **must** correspond to the `master_port`
value you used (or will use) when creating workers. (see the worker
deployment documentation) Feel free to leave this line to its default value.
Make sure the workers can access the master on this port, though. (open the
firewall if necessary)

Our master configuration file does not contain any "change source", since we
don't want to poll a Git repository or anything like that (we rely on web
hooks from github). Therefore:

```
c['change_source'] = []
```

We do need some task scheduling though, either to force builds manually, or
to react automatically to new tags being created in the Ideascube repository
over at Github:

```
c['schedulers'] = [
    schedulers.ForceScheduler(
        name='force',
        builderNames=[
            'build-$arch-pkg',
            ]),
    schedulers.AnyBranchScheduler(
        name='tags',
        categories=['new-tag'],
        builderNames=[
            'build-$arch-pkg',
            ]),
    ]
```

In the snippet above, there must be one line for each deployed worker in the
`builderNames` lists.

Finally, configure the Buildbot web application. It allows a few things:

* it reports the status of tasks
* it allows forcing a task manually
* it provides a web hook that Github can call to report events

```
authz_cfg = web.authz.Authz(
    auth=web.auth.BasicAuth([('$admin_login', '$admin_password')]), forceBuild='auth',
    forceAllBuilds='auth', gracefulShutdown=False, pingBuilder=False,
    stopBuild=False, stopAllBuilds=False, cancelPendingBuild=False)

c['status'] = [
    html.WebStatus(
        http_port=8010, authz=authz_cfg,
        change_hook_dialects={
            'github': {
                'class': GithubCreateEventHandler,
                'secret': '$secret',
                'strict': True,
                },
            },
        ),
    ]
```

Of course, in the above snippet, replace the `$admin_login` and
`$admin_password` variables by their actual values. They are used to
authenticate on the Buildbot web application, which is required to manually
for tasks.

In the same way, the `$secret` variable should be replaced by the secret value
given to Github when configuring the web hook.

Now, install the `buildbot-master.service` file provided in this repository,
in the `/etc/systemd/system/` folder.

Then, start and enable the new master service:

```
# systemctl daemon-reload
# systemctl start buildbot-master.service
# systemctl enable buildbot-master.service
# systemctl status buildbot-master.service
```

At this point, your master is fully operational, ready to dispatch tasks to
the worker(s).

### Web proxy with nginx

To make the web application publicly accessible on the normal HTTP port(s),
we use nginx as a reverse proxy.

You can install the `nginx/buildbot` file provided in this repository, in the
`/etc/nginx/sites-available/` directory, then enable it:

```
# ln -s /etc/nginx/sites-{available,enabled}/buildbot
```

Restart or reload nginx so it takes into account the new configuration.

At this point, the Buildbot web application is responding on
[http://buildbot.ideascube.org](http://buildbot.ideascube.org).
