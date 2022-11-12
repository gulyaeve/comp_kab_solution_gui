import logging
import subprocess

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal
from paramiko.ssh_exception import AuthenticationException

from config import config_path
from desktop_entrys import network_share, network_share_for_teacher
from system import run_command_by_root, user, this_host, run_command_in_xterm


class NetworkFolderSetup(QThread):
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts = None

    def run(self):
        self.network_folders()

    def network_folders(self):
        """
        Создание сетевой папки и копирование ярлыка по ssh на хосты
        """
        logging.info("Создание сетевой папки")
        ssh_hosts = self.test_ssh()
        if ssh_hosts:
            self.progress_signal.emit(
                'Создаю сетевую папку share (/home/share) и отправляю ссылку на компьютеры учеников')
            run_command_by_root(f'mkdir -p /home/share && chmod 755 /home/share && chown {user} /home/share')
            with open(f'{config_path}/share.desktop', 'w') as file_link:
                file_link.write(network_share.format(teacher_host=this_host))
            for host in self.hosts.items_to_list():
                run_command_in_xterm(
                    f"scp {config_path}/share.desktop root@{host.hostname}:'/home/student/Рабочий\ стол'"
                )
            with open(f'/home/{user}/Рабочий стол/share.desktop', 'w') as file_link_2:
                file_link_2.write(network_share_for_teacher)
            logging.info('Сетевая папка создана')
        else:
            self.progress_signal.emit(
                "\nНастройка сетевой папки не выполнена"
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

