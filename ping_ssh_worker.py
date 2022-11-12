import time

from PyQt5.QtCore import QThread, pyqtSignal

from hosts import Hosts
from system import test_ssh


class PingSSH(QThread):
    progress_signal = pyqtSignal(list)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def run(self):
        while True:
            hosts = Hosts()
            result = []
            for host in hosts.to_list():
                if test_ssh(host):
                    result.append(f"{host} SSH")
                else:
                    result.append(f"{host} NO_SSH")
            self.progress_signal.emit(result)
            time.sleep(1)
            # print(test_ssh(host))
