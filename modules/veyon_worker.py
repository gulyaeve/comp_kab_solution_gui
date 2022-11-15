import logging
import subprocess

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal
from paramiko.ssh_exception import AuthenticationException

from modules.command_worker import SSHCommandExec
from modules.config import config_path
from modules.desktop_entrys import veyon_link
from modules.system import get_mac_address, run_command_by_root, user, run_command_in_xterm


class VeyonSetup(QThread):
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts = None
        self.kab = ""

    def run(self):
        self.install_veyon()
        
    def install_veyon(self):
        """
        Установка и настройка veyon: скачивание пакета, создание ключей, копирование списка хостов и настройка по ssh на
        хостах
        """
        ssh_hosts = self.test_ssh()
        if ssh_hosts:
            self.progress_signal.emit("Проверка мак-адресов проводных сетевых плат")
            for host in self.hosts.hosts:
                self.hosts.save_mac_address(
                    host,
                    get_mac_address(self.hosts.hosts[host]['hostname'])
                )
            self.progress_signal.emit("Мак-адреса проверены")
            logging.info(f'Установка вейон на компьютере учителя')
            network_objects = ''
            for host in self.hosts.items_to_list():
                mac_address = "aa:bb:cc:dd:ee:ff" if not host.mac_address else host.mac_address
                network_objects += f"veyon-cli networkobjects add " \
                                   f"computer \"{host.name()}\" \"{host.hostname}\" \"{mac_address}\" \"{self.kab}\""
            self.progress_signal.emit("Установка veyon на компьютере учителя")
            run_command_by_root(
                f"apt-get update -y; "
                f"apt-get install veyon -y; "
                f"rm {config_path}/veyon_{user}_public_key.pem -f; "
                f"veyon-cli config clear; "
                f"veyon-cli config set Authentication/Method 1; "
                f"veyon-cli config set Service/Autostart true; "
                "veyon-cli config set VncServer/Plugin {39d7a07f-94db-4912-aa1a-c4df8aee3879}; "
                f"veyon-cli authkeys delete {user}/private; "
                f"veyon-cli authkeys delete {user}/public; "
                f"veyon-cli authkeys create {user}; "
                f"veyon-cli authkeys setaccessgroup {user}/private {user}; "
                f"veyon-cli authkeys export {user}/public {config_path}/veyon_{user}_public_key.pem; "
                f"veyon-cli networkobjects clear; "
                f"veyon-cli networkobjects add location {self.kab}; "
                f"{network_objects}; "
                f"veyon-cli service start"
            )
            self.progress_signal.emit("Установка veyon на компьютере учителя завершена")
            logging.info(f'Установка вейон на комьютере учителя УСПЕШНО')

            # self.progress_signal.emit("Установка veyon на компьютерах учеников")
            logging.info(f'Установка вейон на комьютере учеников')
            # copy_to_hosts = []
            setup_wol = 'nmcli c modify \\"Проводное соединение 1\\" ethernet.wake-on-lan magic'
            install_on_hosts = [
                f"apt-get update",
                f"apt-get -y install veyon",
                f"{setup_wol}",
                f"veyon-cli config clear",
                f"veyon-cli authkeys delete {user}/public",
                f"veyon-cli authkeys import {user}/public /tmp/veyon_{user}_public_key.pem",
                f"veyon-cli config set Authentication/Method 1",
                f"veyon-cli config set Service/Autostart true",
                f"veyon-cli config set Service/HideTrayIcon true",
                "veyon-cli config set VncServer/Plugin {39d7a07f-94db-4912-aa1a-c4df8aee3879}",
                f"veyon-cli service start",
                f"reboot"
            ]

            self.progress_signal.emit("Создние ярлыка на рабочем столе")
            with open(f'/home/{user}/Рабочий стол/veyon.desktop', 'w') as file_link:
                file_link.write(veyon_link)
                self.progress_signal.emit("Ярлык создан")

            run_command_in_xterm(
                f"ssh-add"
            )

            self.progress_signal.emit("Копирование ключа")
            for host in self.hosts.items_to_list():
                run_command_in_xterm(f"scp {config_path}/veyon_{user}_public_key.pem root@{host.hostname}:/tmp/")
            self.progress_signal.emit("Ключ скопирован")

            self.progress_signal.emit("Отправка команд на установку")
            self.thread = SSHCommandExec()
            self.thread.hosts_list = self.hosts.items_to_list()
            self.thread.commands_list = install_on_hosts
            # self.thread.progress_signal.connect(lambda: self.progress_signal.emit("Команда"))
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()
            self.thread.finished.connect(lambda: self.progress_signal.emit("Перезагрузка устройства"))
            # self.progress_signal.emit("Команды отправлены на компьютеры учеников, дождитесь перезагрузки устройств.")
            logging.info(f'Установка вейон на компьютере учеников УСПЕШНО')
            logging.info('Veyon установлен')
        else:
            self.progress_signal.emit(
                '\nДля настройки veyon необходимо сначала настроить ssh'
            )

    def test_ssh(self):
        """
        Проверка подключения к хостам пользователем root
        """
        self.progress_signal.emit("\nПроверяю доступ по ssh к компьютерам")
        list_of_hosts = self.ping()
        if list_of_hosts:
            errors = 0
            ssh_hosts = []
            for host in list_of_hosts:
                host = host.strip()
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    ssh.connect(hostname=host, port=22, timeout=5, username='root')
                    logging.info(f"Подключено по ssh@root без пароля к {host}")
                    self.progress_signal.emit(f"Подключено по ssh@root без пароля к {host}")
                    ssh_hosts.append(host)
                except AuthenticationException:
                    self.progress_signal.emit(f'Не удалось подключиться ssh root@{host}')
                    logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
                    errors += 1
                    return []
                return ssh_hosts
            if errors > 1:
                self.progress_signal.emit(
                    '\nssh не удалось настроить'
                )
        else:
            self.progress_signal.emit(
                '\nssh не настроен'
            )

    def ping(self):
        """
        Подключение к хостам и проверка ping
        :return: список хостов в случае успеха
        """
        hosts = self.hosts.to_list()
        if hosts:
            self.progress_signal.emit("\nСписок устройств найден, выполняю ping всех устройств:")
            errors = 0
            list_of_hosts = []
            for host in hosts:
                result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
                if result.returncode == 0:
                    self.progress_signal.emit(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                    logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
                elif result.returncode == 2:
                    logging.info(f"ping: {host}: {result=} {result.returncode=}")
                    self.progress_signal.emit(f"ping: {host}: УСТРОЙСТВО НЕ НАЙДЕНО")
                    errors += 1
                else:
                    self.progress_signal.emit(f"ping: {host}: неизвестная ошибка")
                    logging.info(host + f" неизвестная ошибка {result=} {result.returncode=}")
                    errors += 1
                list_of_hosts.append(host)
            if errors > 0:
                self.progress_signal.emit("Некоторые компьютеры найти не удалось, "
                                          "проверьте правильность имён и повторите попытку.")
                return []
            return list_of_hosts
        else:
            self.progress_signal.emit(
                '\nЗаполните список устройств: '
                'перечислите в нём имена компьютеров и запустите скрипт повторно.\n\n'
                '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local\n'
            )
            return []
