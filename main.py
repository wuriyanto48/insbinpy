import sys
import os
from insbin import Insbin

# example
# install yowes from its github release page
if __name__ == '__main__':
    home = os.path.dirname(os.path.abspath(__file__))

    os_platform = ''
    try:
        os_platform = Insbin.get_platform()
    except Exception as e :
        sys.exit(e)
 
    installation_dir = os.path.join(home, '.yowes')
    url = f'https://github.com/wuriyanto48/yowes/releases/download/v1.0.0/yowes-v1.0.0.{os_platform}.tar.gz'
    ins = Insbin.install_to_home(app_name='yowes', url=url, installation_dir=installation_dir)
    # ins.install()
    try:
        ins.run()
    except Exception as e:
        print(e)