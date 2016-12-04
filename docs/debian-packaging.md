# Debian Packaging

The main goal of our continuous integration platform is to automate the
of Debian packages for the Ideascube project.

We want to be able to build the packages properly, in an unattended and
reproducible way.

The Debian developers use [sbuild](https://wiki.debian.org/sbuild) to do that,
so it seems like a good idea to do the same.

**Note:** When following this documentation, you will find a few variables
here and there. You must replace them by their actual values. For example, the
`$arch` variable appears several times, and must be replaced by something like
`amd64` or `armhf`, depending on the actual architecture of the worker.

## On each worker machine

### Pre-requisites

A few things need to be installed before we start:

```
# apt install sbuild debootstrap debhelper dh-virtualenv dput python3-setuptools
```

The [buildbot](buildbot.md) user needs to be a sudoer for certain commands, so
add the following lines with the `visudo` command:

```
# Allow buildbot to update the sbuild chroots without a password
buildbot  ALL=(root) NOPASSWD: /usr/bin/sbuild-update
```

Finally, there are a couple of directories to create:

```
# mkdir /srv/chroot{,-tarballs}
# chown root:sbuild /srv/chroot{,-tarballs}
# chmod g+w /srv/chroot{,-tarballs}
```

### Configuring sbuild

A few things are needed in order to get a working sbuild deployment:

```
# sbuild-update --keygen
# sbuild-adduser buildbot
# sbuild-createchroot \
    --make-sbuild-tarball=/srv/chroot-tarballs/jessie-$arch.tar.gz \
    --arch=$arch \
    jessie \
    /srv/chroot/jessie-$arch \
    http://ftp.fr.debian.org/debian
```

At this point, you should have a functional `sbuild`. You could test it by
running the following commands as the `buildbot` user:

```
$ sudo sbuild-update -udcar jessie-$arch-sbuild
$ git clone https://github.com/ideascube/ideascube
$ cd ideascube
$ sbuild -s -d jessie --arch $arch
```

If the `sbuild` command finished successfully, you'll find an
`ideascube-VERSION.deb` package in the parent directory of your Ideascube git
tree. You can remove the git tree as well as the build artefacts, they are not
necessary any more.

One last thing to do is add some local `sbuild` configuration.

To do so, install the `debian/dot_sbuildrc` file provided in this repository,
as `~/.sbuildrc` in the `buildbot` user's home.

### Configuring dput

Once packages are built on the worker, we need to upload them to the master
and update the repository.

Debian provides the `dput` and `mini-dinstall` commands which work together to
fulfil that purpose.

On the workers, we want to use `dput` to upload the built packages to the
master, and request that `mini-dinstall` be ran there to update the
repository.

To that end, install the `debian/dot_dput.cf` file provided in this
repository, as `~/.dput.cf` in the `buildbot` user's home.

If the worker is not the same host as the master, then the `buildbot` user on
the worker needs to be able to connect through SSH as the `buildbot` user on
the master, without a password.

## On the master machine

### Pre-requisites

A few things need to be installed before we start:

```
# apt install mini-dinstall
```

Finally, there are a couple of directories to create:

```
# mkdir -p /srv/repos/debian/mini-dinstall/incoming
# chown -R buildbot:www-data /srv/repos
# chmod -R g+s /srv/repos

### Configuring mini-dinstall

Once packages are built on the worker, we need to upload them to the master
and update the repository.

Debian provides the `dput` and `mini-dinstall` commands which work together to
fulfil that purpose.

On the master, we want to use `mini-dinstall` to update the repository after
the worker has uploaded the built packages with `dput`.

To that end, install the `debian/dot_mini-dinstall.conf` file provided in this
repository, as `~/.mini-dinstall.conf` in the `buildbot` user's home.

### Configuring the Buildbot master

You must configure the master to run package building tasks. The
`master/master.cfg` included in this repository does just that.

### Serving the repository with nginx

To make the Debian repository publicly accessible, we use nginx to serve the
static content.

You can install the `nginx/repos` file provided in this repository, in the
`/etc/nginx/sites-available/` directory, then enable it:

```
# ln -s /etc/nginx/sites-{available,enabled}/repos
```

Restart or reload nginx so it takes into account the new configuration.

At this point, the package repository is available at
[http://repos.ideascube.org/debian](http://repos.ideascube.org/debian).
