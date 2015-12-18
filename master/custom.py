# Author: Mathieu Bridon <bochecha@daitauha.fr>
# License: GPLv2+
# TODO: Get something like that merged in upstream Buildbot


from datetime import datetime
from glob import glob

from buildbot.status.web.hooks.github import GitHubEventHandler


class GithubCreateEventHandler(GitHubEventHandler):
    def handle_create(self, payload):
        ref_name = payload['ref']
        ref_type = payload['ref_type']

        if ref_type != 'tag':
            # Ignore, we are only interested in new tags
            return [], 'git'

        change = {
            'revision': ref_name,
            'when_timestamp': datetime.now(),
            'branch': ref_name,
            'repository': payload['repository']['clone_url'],
            'category': 'new-tag',
            'author': payload['sender']['login'],
            'comments': 'Tag %s created' % ref_name,
            'project': payload['repository']['full_name']
        }

        return [change], 'git'


def get_changes_file(arch):
    def getter(rc, stdout, stderr):
        if rc != 0:
            return

        for line in stdout.split('\n'):
            if not line.startswith('dpkg-source: info: '):
                continue

            if not line.endswith('.dsc'):
                continue

            dsc_file = line.rsplit(' ', 1)[-1]
            changes_file = '%s_%s.changes' % (dsc_file[:-4], arch)

            return {'changes_file': changes_file}

    return getter
