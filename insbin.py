import os
import platform
import requests
import sys
import subprocess
import tarfile
from io import BytesIO

WINDOWS_PLATFORM = 'Windows'
OSX_PLATFORM = 'Darwin'
LINUX_PLATFORM = 'Linux'

ARCH_64 = '64bit'
ARCH_32 = '32bit'

class Insbin(object):
    def __init__(self, url, data = {}):
        self.url = url
        self.data = data

        if not 'installation_dir' in self.data:
            raise Exception('installation_dir should appear in data dict')

        if not 'app_name' in self.data:
            raise Exception('app_name should appear in data dict')

        self.installation_dir = self.data['installation_dir']
        self.binary_directory = ''
    
    def get_installation_dir(self):
        
        if not os.path.isdir(self.installation_dir):
            # create installation dir
            try:
                os.makedirs(self.installation_dir)
            except OSError as err:
                raise Exception(err.strerror)
        return self.installation_dir

    def get_binary_directory(self):
        binary_directory = os.path.join(self.installation_dir, 'bin')
        if not os.path.isdir(binary_directory):
            raise Exception(err.strerror)
        self.binary_directory = binary_directory
        return self.binary_directory

    # install binary from given source URL
    def install(self):
        home = ''
        if sys.version_info >= (3, 5):
            from pathlib import Path
            home = Path.home()
        else:
            from os.path import expanduser
            home = expanduser('~')

        installation_dir = self.get_installation_dir()
        if not os.path.isdir(installation_dir):
            # create dir
            try:
                os.makedirs(installation_dir)
            except OSError as err:
                raise Exception(err.strerror)

        
        self.binary_directory = os.path.join(installation_dir, 'bin')
        
        # create bin dir
        try:
            os.makedirs(self.binary_directory)
        except OSError as err:
            raise Exception(err.strerror)

        url = 'https://github.com/wuriyanto48/yowes/releases/download/v1.0.0/yowes-v1.0.0.darwin-amd64.tar.gz'
        req = requests.get(url, stream=True)

        print(req.status_code)

        file_name = req.headers['Content-Disposition']
        print(file_name)

        tmp_file = BytesIO()
        while True:
            # download piece of file from given url
            s = req.raw.read(16384)

            # tarfile returns b'', if the download process finished
            if not s:
                break

            tmp_file.write(s)
        req.raw.close()

        # Begin by seeking back to the beginning of the
        # temporary file.
        tmp_file.seek(0)


        tar = tarfile.open(fileobj=tmp_file, mode='r:gz')
        print(tar.getnames())

        if len(tar.getnames()) > 0:
            try:
                bin_name = tar.getnames()[0]
                e = tar.extractall(path=self.binary_directory, members=None)
            except KeyError:
                print('extract error')
        
        tar.close()
        tmp_file.close()

    # run binary
    def run(self):
        argv = sys.argv[1:]
        command = ['./yowes', *argv]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)
        while True:
            out = p.stdout.read(1)
            return_code = p.poll()
            if out == '' and return_code is not None:
                print('RETURN_CODE ', return_code)
                break
            if out != '':
                sys.stdout.write(out)
                sys.stdout.flush()
    
# show operating system and platform
def show_platform():

    os_type = platform.system()
    os_arch = platform.architecture()[0]

    if os_type == WINDOWS_PLATFORM and os_arch == ARCH_64:
        return 'windows-amd64'
    
    if os_type == OSX_PLATFORM and os_arch == ARCH_64:
        return 'darwin-amd64'

    if os_type == LINUX_PLATFORM and os_arch == ARCH_64:
        return 'linux-amd64'
    
    raise Exception('cannot identified os type')


if __name__ == '__main__':
    binary = Insbin('url', data = {'installation_dir': '/Users/wuriyanto', 'app_name': 'yowes'})