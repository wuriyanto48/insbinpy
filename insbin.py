import os
import platform
import requests
import sys
import shutil
import subprocess
import tarfile
from io import BytesIO
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
from urllib.parse import urlparse
from threading import Timer


WINDOWS_PLATFORM = 'Windows'
OSX_PLATFORM = 'Darwin'
LINUX_PLATFORM = 'Linux'

ARCH_64 = '64bit'
ARCH_32 = '32bit'

# is_url : function for validate url
def is_url(url: str) -> bool:
    try:
        res = urlparse(url)
        return all([res.scheme, res.netloc])
    except:
        return False

class Ticker(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class Insbin(object):
    def __init__(self, url: str, opts = {}):
        self.__url = url
        self.__opts = opts

        if not self.__url:
            raise Exception('url should appear in first position of arguments')

        if not is_url(self.__url):
            raise Exception('invalid url')

        if not 'installation_dir' in self.__opts:
            raise Exception('installation_dir should appear in opts dict')

        if not 'app_name' in self.__opts:
            raise Exception('app_name should appear in opts dict')

        self.__installation_dir = self.__opts['installation_dir']
        self.__binary_directory = ''
        self.__binary_path = ''

        self.ticker = Ticker(1, lambda msg='. ': print(msg, end='', flush=True))
    
    def __get_installation_dir(self) -> str:
        if os.path.isdir(self.__installation_dir):
            # create installation dir
            try:
                # remove folder first(uninstall existing binary) if already exist
                shutil.rmtree(self.__installation_dir)
                print(f'removing current installation: {self.__installation_dir}', flush=True)

                # recreate the folder
                os.makedirs(self.__installation_dir)
                print(f'recreating installation: {self.__installation_dir}', flush=True)
            except OSError as err:
                raise Exception(err.strerror)
        return self.__installation_dir

    def __get_binary_directory(self) -> str:
        binary_directory = os.path.join(self.__installation_dir, 'bin')
        if not os.path.isdir(binary_directory):
            # raise Exception('application {} does not exist'.format(self.__opts['app_name']))
            # install instead
            try:
                self.install()
            except Exception as e:
                raise e
        self.__binary_directory = binary_directory
        return self.__binary_directory
    
    def __get_binary_path(self) -> str:
        if self.__binary_path == '':
            try:
                binary_dir = self.__get_binary_directory()
                self.__binary_path = os.path.join(binary_dir, self.__opts['app_name'])
            except Exception as e:
                raise e
        return self.__binary_path

    # install binary from given source URL
    def install(self)-> None:
        installation_dir = self.__get_installation_dir()
        if not os.path.isdir(installation_dir):
            # create dir
            try:
                os.makedirs(installation_dir)
            except OSError as err:
                raise Exception(err.strerror)

        
        self.__binary_directory = os.path.join(installation_dir, 'bin')

        # binary folder already exist, so its already installed
        # exit from install method
        if os.path.isdir(self.__binary_directory):
            return
        
        # create bin dir
        try:
            os.makedirs(self.__binary_directory)
        except OSError as err:
            raise Exception(err.strerror)
        
        # create temporary memory 
        tmp_file = BytesIO()
        
        def log_timer(receiver: Connection, sender: Connection):
            print('downloading ', end='', flush=True)
            sender.close()

            # start ticker
            self.ticker.start()
            
            while True:
                if receiver.poll():
                    done = receiver.recv()
                    if done:
                        print(flush=True)
                        print('download done', flush=True)

                        # stop ticker when download process done
                        self.ticker.cancel()
                        break

        # multiprocess
        def download(sender: Connection):
            url = self.__url
            req = requests.get(url, stream=True)

            if req.status_code != 200:
                raise Exception('url returned code {}'.format(req.status_code))

            # file_name = req.headers['Content-Disposition']
            # print(file_name)

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
        log_process = Process(target = log_timer, args = (receiver, sender))
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
                tar.extractall(path=self.__binary_directory, members=None)
            except KeyError:
                tar.close()
                tmp_file.close()
                raise Exception('insbin: extracting tar file error')
        
        tar.close()
        tmp_file.close()

    # run binary
    def run(self) -> None:
        argv = sys.argv[1:]
        command = [self.__get_binary_path(), *argv]
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
    @staticmethod
    def get_platform() -> str:

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
    @staticmethod
    def install_to_home(app_name: str, url: str, installation_dir: str):
        from os.path import expanduser
        home = expanduser('~')

        if sys.version_info >= (3, 5):
            from pathlib import Path
            home = Path.home()

        # if installation_dir is empty, give the installation_dir default to home
        if installation_dir == '':
            installation_dir = os.path.join(home, f'.{app_name}')

        return Insbin(url, opts = {'installation_dir': installation_dir, 'app_name': app_name})