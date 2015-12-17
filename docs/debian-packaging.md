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
# apt install sbuild dh-virtualenv
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
    http://httpredir.debian.org/debian
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

## On the master machine

### Configuring the Buildbot master

You must configure the master to run package building tasks. The
`master/master.cfg` included in this repository already does that, but let's
explain the config a bit:

```
$arch_pkg_factory = util.BuildFactory()
$arch_pkg_factory.addStep(steps.Git(
    repourl='https://github.com/ideascube/ideascube.git',
    mode='incremental', branch='master'))
$arch_pkg_factory.addStep(steps.ShellCommand(
    command=['sudo', 'sbuild-update', '-udcar', 'jessie-$arch-sbuild']))
$arch_pkg_factory.addStep(steps.ShellCommand(
    command=['sbuild', '-s', '-d', 'jessie', '--arch', '$arch']))

c['builders'] = [
    util.BuilderConfig(
        name='build-$arch-pkg',
        slavenames=['slave-$arch'],
        factory=$arch_pkg_factory),
    ]
```

In the snippet above, `$arch` represents the architecture of the worker
machine. There must be one `$arch_pkg_factory` and `BuilderConfig` for each
worker architecture.