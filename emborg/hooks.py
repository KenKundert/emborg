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
            hook.backups_begin()

    def backups_finish(self, borg):
        for hook in self.active_hooks:
            hook.backups_finish(borg)

# HealthChecks class {{{1
class HealthChecks(Hooks):
    EMBORG_SETTINGS = dict(
        healthchecks_uuid = 'the UUID associated with your health check.'
    )

    def __init__(self, settings):
        self.url = settings.healthchecks_uuid
        if self.url:
            if not self.url.startswith('http'):
                self.url = f'https://hc-ping.com/{self.url}'

    def is_active(self):
        return bool(self.url)

    def backups_begin(self):
        url = f'{self.url}/start'
        log(f'signaling start of backups to {self.url}.')
        try:
            requests.post(url)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException
        ) as e:
            raise Error('healthcheck connection error.', codicil=full_stop(e))

    def backups_finish(self, borg):
        status = borg.status
        payload = borg.stderr
        url = f'{self.url}/{status}'
        log(f'signaling end of backups to {self.url} with status {status}.')
        try:
            response = requests.post(url, data=payload.encode('utf-8'))
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException
        ) as e:
            raise Error('healthcheck connection error.', codicil=full_stop(e))
