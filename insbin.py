import os
import platform
import requests
import sys
import subprocess
import tarfile
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
from io import BytesIO
from urllib.parse import urlparse

WINDOWS_PLATFORM = 'Windows'
OSX_PLATFORM = 'Darwin'
LINUX_PLATFORM = 'Linux'

ARCH_64 = '64bit'
ARCH_32 = '32bit'

# is_url : function for validate url
def is_url(url) -> bool:
    try:
        res = urlparse(url)
        return all([res.scheme, res.netloc])
    except:
        return False

class Insbin(object):
    def __init__(self, url: str, opts = {}):
        self.url = url
        self.opts = opts

        if not self.url:
            raise Exception('url should appear in first position of arguments')

        if not is_url(self.url):
            raise Exception('invalid url')

        if not 'installation_dir' in self.opts:
            raise Exception('installation_dir should appear in opts dict')

        if not 'app_name' in self.opts:
            raise Exception('app_name should appear in opts dict')

        self.installation_dir = self.opts['installation_dir']
        self.binary_directory = ''
        self.binary_path = ''
    
    def get_installation_dir(self) -> str:
        
        if not os.path.isdir(self.installation_dir):
            # create installation dir
            try:
                os.makedirs(self.installation_dir)
            except OSError as err:
                raise Exception(err.strerror)
        return self.installation_dir

    def get_binary_directory(self) -> str:
        binary_directory = os.path.join(self.installation_dir, 'bin')
        if not os.path.isdir(binary_directory):
            # raise Exception('application {} does not exist'.format(self.opts['app_name']))
            # install instead
            self.install()
        self.binary_directory = binary_directory
        return self.binary_directory
    
    def get_binary_path(self) -> str:
        if self.binary_path == '':
            binary_dir = self.get_binary_directory()
            self.binary_path = os.path.join(binary_dir, self.opts['app_name'])
        return self.binary_path

    # install binary from given source URL
    def install(self)-> None:
        installation_dir = self.get_installation_dir()
        if not os.path.isdir(installation_dir):
            # create dir
            try:
                os.makedirs(installation_dir)
            except OSError as err:
                raise Exception(err.strerror)

        
        self.binary_directory = os.path.join(installation_dir, 'bin')

        # binary folder already exist, so its already installed
        # exit from install method
        if os.path.isdir(self.binary_directory):
            return
        
        # create bin dir
        try:
            os.makedirs(self.binary_directory)
        except OSError as err:
            raise Exception(err.strerror)
        
        # create temporary memory 
        tmp_file = BytesIO()

        def log(receiver: Connection, sender: Connection):
            print('downloading', end='')
            sender.close()
            while True:
                if receiver.poll():
                    done = receiver.recv()
                    if done:
                        print('download done')
                        break
                else:
                    print('.', end='')

        # multiprocess
        def download(sender: Connection):
            url = self.url
            req = requests.get(url, stream=True)

            if req.status_code != 200:
                raise Exception('url returned code {}'.format(req.status_code))

            file_name = req.headers['Content-Disposition']
            print(file_name)

            while True:

                # download piece of file from given url
                s = req.raw.read(1024)

                # tarfile returns b'', if the download process finished
                if not s:
                    break

                tmp_file.write(s)
            req.raw.close()

            # send notification to log() process
            # indicating the download process done
            sender.send(True)

        receiver, sender = Pipe()
        log_process = Process(target = log, args = (receiver, sender))
        log_process.daemon = True
        log_process.start()

        receiver.close()
        download(sender)

        log_process.join()

        # multiprocess done

        # Begin by seeking back to the beginning of the
        # temporary file.
        tmp_file.seek(0)

        tar = tarfile.open(fileobj=tmp_file, mode='r:gz')

        # extract tar file
        if len(tar.getnames()) > 0:
            try:
                tar.extractall(path=self.binary_directory, members=None)
            except KeyError:
                print('extract error')
        
        tar.close()
        tmp_file.close()

    # run binary
    def run(self) -> None:
        argv = sys.argv[1:]
        command = [self.get_binary_path(), *argv]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)
        while True:
            out = p.stdout.read(1)
            return_code = p.poll()
            if out == '' and return_code is not None:
                # print('RETURN_CODE ', return_code)
                break
            if out != '':
                sys.stdout.write(out)
                sys.stdout.flush()
    
# show operating system and platform
def show_platform() -> str:

    os_type = platform.system()
    os_arch = platform.architecture()[0]

    if os_type == WINDOWS_PLATFORM and os_arch == ARCH_64:
        return 'windows-amd64'
    
    if os_type == OSX_PLATFORM and os_arch == ARCH_64:
        return 'darwin-amd64'

    if os_type == LINUX_PLATFORM and os_arch == ARCH_64:
        return 'linux-amd64'
    
    raise Exception('cannot identified os type')

# install to home folder
# eg: /Users/ubuntu
def install_to_home() -> Insbin:
    from os.path import expanduser
    home = expanduser('~')

    if sys.version_info >= (3, 5):
        from pathlib import Path
        home = Path.home()
 
    installation_dir = os.path.join(home, '.yowes')
    url = 'https://github.com/wuriyanto48/yowes/releases/download/v1.0.0/yowes-v1.0.0.darwin-amd64.tar.gz'
    return Insbin(url, opts = {'installation_dir': installation_dir, 'app_name': 'yowes'})


if __name__ == '__main__':
    # get_binary()
    home = os.path.dirname(os.path.abspath(__file__))
 
    installation_dir = os.path.join(home, '.yowes')
    url = 'https://github.com/wuriyanto48/yowes/releases/download/v1.0.0/yowes-v1.0.0.darwin-amd64.tar.gz'
    ins = Insbin(url, opts = {'installation_dir': installation_dir, 'app_name': 'yowes'})
    # ins.install()
    ins.run()