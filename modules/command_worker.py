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
        self.hosts_list = None
        self.command = ""
        self.commands_list = []

    def run(self):
        if self.command:
            self.run_command_on_ssh()
        elif self.commands_list:
            self.run_command_on_ssh_from_list(self.commands_list)

    def run_command_on_ssh(self):
        logging.info(f"Выполнение команды {self.command} на {self.hosts_list}")
        client = SSHClient()
        client.load_system_host_keys()
        for host in self.hosts_list:
            try:
                client.connect(hostname=host, username="root")
                stdin, stdout, stderr = client.exec_command(self.command)
                # print(f"{stdout.read().decode().strip()=}")
                result = stdout.read().decode().strip()
                self.progress_signal.emit(f"\nРезультат выполнения на {host}:\n\n{result}")
                logging.info(f"\nРезультат выполнения на {host}:\n\n{result}")
            except (AuthenticationException, SSHException, socket.gaierror):
                self.progress_signal.emit(f'Не удалось подключиться ssh root@{host}')
                logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
            except Exception as e:
                self.progress_signal.emit(f'{host} неизвестная ошибка.')
                logging.info(f"неизвестная ошибка {host}: {e}")

    def run_command_on_ssh_from_list(self, commands_list: list):
        logging.info(f"Выполнение команды {commands_list} на {self.hosts_list}")
        client = SSHClient()
        client.load_system_host_keys()
        for host in self.hosts_list:
            try:
                client.connect(hostname=host.hostname, username="root")
                for command in commands_list:
                    stdin, stdout, stderr = client.exec_command(command)
                    # print(f"{stdout.read().decode().strip()=}")
                    result = stdout.read().decode().strip()
                    self.progress_signal.emit(f"\nРезультат выполнения {command} на {host.hostname}:\n\n{result}")
                    logging.info(f"\nРезультат выполнения {command} на {host.hostname}:\n\n{result}")
            except (AuthenticationException, SSHException, socket.gaierror):
                self.progress_signal.emit(f'Не удалось подключиться ssh root@{host}')
                logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
            except Exception as e:
                self.progress_signal.emit(f'{host} неизвестная ошибка.')
                logging.info(f"неизвестная ошибка {host}: {e}")
