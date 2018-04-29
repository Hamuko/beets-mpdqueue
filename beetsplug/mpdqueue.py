"""Beets plugin to add imported files to Music Player Daemon queue.

This plugin listens for Beets import events and adds all imported items at the
end of the server queue at the end of Beets program execution.

This plugin uses the same configuration as the MPDUpdate plugin included with
Beets to connect to a server.

    mpd:
        host: localhost
        port: 6600
        password: seekrit

Compatibility with Python 2.7 or lower not tested or guaranteed.
"""

# pylint: disable=unused-argument

from time import sleep
import os
import socket

from beets import config
from beets.plugins import BeetsPlugin


class MusicPlayerDaemonClient():
    """Simple socket client to provide connectivity to a Music Player Daemon
    server for updates and queue management.
    """

    def __init__(self, host='localhost', port=6600, password=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(0.25)
        acknowledgement = self._read()[0]
        if not acknowledgement.startswith('OK MPD'):
            self.close()
        if password:
            self._send('password "{}"'.format(password))
            response = self._read()[0]
            if not response.startswith('OK'):
                self.close()

    def _read(self):
        """Reads data from the server. Returns the sent lines as an array of strings.

        This operation may return an empty list if the server does not send
        anything during the socket timeout period.
        """
        data = b''
        while True:
            try:
                data_buffer = self.sock.recv(1024)
            except socket.timeout:
                break
            if not data_buffer:
                break
            data += data_buffer
        return data.decode().strip().split('\n')

    def _send(self, data):
        """Sends a string to the server."""
        if data[-1] != '\n':
            data = ''.join([data, '\n'])
        self.sock.send(data.encode())

    def add(self, path):
        """Adds given path to MPD queue."""
        self._send('add "{}"'.format(path))
        return self._read()[0] == 'OK'

    def close(self):
        """Closes the connection to the server."""
        self._send('close')
        self.sock.close()

    def status(self):
        """Fetches status from Music Player Daemon. Returns a tuple of strings.
        """
        self._send('status')
        return self._read()

    def update(self, directory):
        """Updates the MPD database with items from the given directory.

        Blocks until the update is finished.
        """
        self._send('update "{}"'.format(directory))
        response = self._read()
        if response[-1] != 'OK':
            return
        while True:
            updating = False
            for line in self.status():
                if line.startswith('updating_db'):
                    updating = True
            if not updating:
                break
            sleep(0.5)


class MPDQueuePlugin(BeetsPlugin):
    """Beets plugin that generates a list of imported files after each import
    task (import_task_files) and imports them to MPD at the end of program
    execution (cli_exit).
    """

    def __init__(self):
        super(MPDQueuePlugin, self).__init__()
        config['mpd'].add({
            'host': os.environ.get('MPD_HOST', 'localhost'),
            'port': 6600,
            'password': '',
        })
        config['mpd']['password'].redact = True

        self.files = []

        self.register_listener('import_task_files', self.import_task_files)
        self.register_listener('cli_exit', self.update_queue)

    def import_task_files(self, task, session):
        """Track all the files added during an import operation so they can be
        later added to the queue when beets exits.

        This operation skips all import tasks that do not have a `toppath`
        property as it indicates a reimport of existing library files.
        """
        if not task.toppath:
            self._log.debug(u'Skipping library re-import')
            return

        tracks = []
        items = sorted(task.imported_items(), key=lambda x: x.track)
        for item in items:
            destination = item.destination(fragment=True)
            self._log.debug(u'{0} will be added to queue', destination)
            tracks.append(destination)
        self.files += tracks

    def update_queue(self, lib):
        """Updates the MPD queue with the files added to `self.files` array.

        In order for the files to be added successfully to MPD, the database
        must be first populated with them. Thus a set of all the directories
        for the imported files is first created and then imported into MPD
        one-by-one. The update operation is blocking to guarantee that the
        files are in the database when they are added.
        """
        if not self.files:
            self._log.debug(u'No files to add to queue')
            return

        host = config['mpd']['host'].as_str()
        port = config['mpd']['port'].get(int)
        password = config['mpd']['password'].as_str()
        client = MusicPlayerDaemonClient(host, port, password)

        directories = set()
        for file_ in self.files:
            directories.add(os.path.dirname(file_))
        for directory in directories:
            self._log.debug(u'Updating directory {0}', directory)
            client.update(directory)
            self._log.debug(u'Finished updating {0}', directory)

        for file_ in self.files:
            self._log.debug(u'Adding {0} to queue', file_)
            success = client.add(file_)
            if success:
                self._log.debug(u'Added {0} to queue', file_)
            else:
                self._log.warning(u'Failed to add {0} to queue', file_)
        client.close()
