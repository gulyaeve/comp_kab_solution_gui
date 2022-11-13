import time

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QListWidgetItem

from modules.hosts import Hosts
from modules.system import test_ssh


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
                item = QListWidgetItem()
                item.setText(host)
                if test_ssh(host):
                    item.setBackground(QColor("green"))
                else:
                    item.setBackground(QColor("red"))
                result.append(item)
            self.progress_signal.emit(result)

