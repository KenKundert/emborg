# Hooks

# License {{{1
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.


# Imports {{{1
from inform import Error, full_stop, log
from .preferences import EMBORG_SETTINGS
import requests

# Hooks base class {{{1
class Hooks:
    @classmethod
    def provision_hooks(cls):
        for subclass in cls.__subclasses__():
            for k, v in subclass.EMBORG_SETTINGS.items():
                assert k not in EMBORG_SETTINGS
                EMBORG_SETTINGS[k] = v

    def __init__(self, settings):
        self.active_hooks = []
        for subclass in self.__class__.__subclasses__():
            c = subclass(settings)
            if c.is_active():
                self.active_hooks.append(c)

    def backups_begin(self):
        for hook in self.active_hooks:
            hook.signal_start()

    def backups_finish(self, borg):
        for hook in self.active_hooks:
            hook.signal_end(borg)

    def is_active(self):
        return bool(self.uuid)

    def signal_start(self):
        url = self.START_URL.format(url=self.url, uuid=self.uuid)
        log(f'signaling start of backups to {self.NAME}: {url}.')
        try:
            requests.get(url)
        except requests.exceptions.RequestException as e:
            raise Error(f'{self.NAME} connection error.', codicil=full_stop(e))

    def signal_end(self, borg):
        status = borg.status
        if status:
            url = self.FAIL_URL.format(url=self.url, uuid=self.uuid)
            result = 'failure'
        else:
            url = self.SUCCESS_URL.format(url=self.url, uuid=self.uuid)
            result = 'success'
        log(f'signaling {result} of backups to {self.NAME}: {url}.')
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            raise Error('{self.NAME} connection error.', codicil=full_stop(e))


# HealthChecks class {{{1
class HealthChecks(Hooks):
    NAME = 'healthchecks.io'
    EMBORG_SETTINGS = dict(
        healthchecks_url = 'the healthchecks.io URL for back-ups monitor',
        healthchecks_uuid = 'the healthchecks.io UUID for back-ups monitor',
    )
    URL = 'https://hc-ping.com'

    def __init__(self, settings):
        self.uuid = settings.healthchecks_uuid
        self.url = settings.healthchecks_url
        if not self.url:
            self.url = self.URL

    def signal_start(self):
        url = f'{self.url}/{self.uuid}/start'
        log(f'signaling start of backups to {self.NAME}: {url}.')
        try:
            requests.post(url)
        except requests.exceptions.RequestException as e:
            raise Error('{self.NAME} connection error.', codicil=full_stop(e))

    def signal_end(self, borg):
        status = borg.status
        result = 'failure' if status else 'success'
        payload = borg.stderr
        url = f'{self.url}/{self.uuid}/{status}'
        log(f'signaling {result} of backups to {self.NAME}: {url}.')
        try:
            if payload is None:
                log('log unavailable to upload to healthchecks.io.')
                response = requests.post(url)
            else:
                response = requests.post(url, data=payload.encode('utf-8'))
        except requests.exceptions.RequestException as e:
            raise Error('{self.NAME} connection error.', codicil=full_stop(e))


# CronHub class {{{1
class CronHub(Hooks):
    NAME = 'cronhub.io'
    EMBORG_SETTINGS = dict(
        cronhub_uuid = 'the cronhub.io UUID for back-ups monitor',
        cronhub_url = 'the cronhub.io URL for back-ups monitor',
    )
    START_URL = '{url}/start/{uuid}'
    SUCCESS_URL = '{url}/finish/{uuid}'
    FAIL_URL = '{url}/fail/{uuid}'
    URL = 'https://cronhub.io'

    def __init__(self, settings):
        self.uuid = settings.cronhub_uuid
        self.url = settings.cronhub_url
        if not self.url:
            self.url = self.URL
