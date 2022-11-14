import logging
import socket
import subprocess

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal
from paramiko.client import SSHClient
from paramiko.ssh_exception import AuthenticationException, SSHException

# from system import run_command_in_xterm_hold


class SSHCommandExec(QThread):
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts = None
        self.command = ""

    def run(self):
        self.run_command_on_ssh()

    def run_command_on_ssh(self):
        logging.info("Выполнение команды")
        client = SSHClient()
        client.load_system_host_keys()
        for host in self.hosts.items_to_list():
            try:
                client.connect(hostname=host.hostname, username="root")
                stdin, stdout, stderr = client.exec_command(self.command)
                # print(f"{stdout.read().decode().strip()=}")
                result = stdout.read().decode().strip()
                self.progress_signal.emit(f"\nРезультат выполнения на {host.hostname}:\n\n{result}")
            except (AuthenticationException, SSHException, socket.gaierror):
                self.progress_signal.emit(f'Не удалось подключиться ssh root@{host.hostname}')
                logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
            except Exception as e:
                self.progress_signal.emit(f'{host.hostname} неизвестная ошибка.')
                logging.info(f"неизвестная ошибка {host}: {e}")
