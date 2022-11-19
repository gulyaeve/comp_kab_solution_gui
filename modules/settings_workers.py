import logging
import socket
import subprocess
import time
from _socket import timeout

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal
from paramiko.channel import Channel
from paramiko.client import SSHClient
from paramiko.ssh_exception import AuthenticationException, SSHException

from modules.config import config_path
from modules.desktop_entrys import ssh_add_link, network_share_for_teacher, network_share, veyon_link
from modules.system import run_command_in_xterm, user, run_command_by_root, this_host, run_command, get_mac_address, \
    test_ssh


class SSHRootSetup(QThread):
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts = None
        self.root_pass = ""

    def run(self):
        self.progress_signal.emit("НАЧАЛО НАСТРОЙКИ SSH")
        self.setup_ssh()

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

    def setup_ssh(self):
        """
        Создание ключей ssh
        Копирование ключей на хосты для пользователя teacher
        Подключение к хостам под пользователем teacher и копирование ключей пользователю root
        """
        list_of_hosts = self.ping()
        if list_of_hosts:
            logging.info(f"Начало создания ключа")
            self.progress_signal.emit(f"\nСоздание ключа ssh")
            run_command_in_xterm(f"ssh-keygen -t ed25519 -q -P '' -f /home/{user}/.ssh/id_ed25519")
            logging.info(f"Ключ создан")
            self.progress_signal.emit(f"\nКлюч ssh создан")
            time.sleep(1)
            run_command_in_xterm(f'mkdir -p /home/{user}/.config/autostart')
            with open(f'/home/{user}/.config/autostart/ssh-add.desktop', 'w') as file_link:
                file_link.write(ssh_add_link)
            logging.info(f"Ярлык в автозапуск ssh-add создан")
            self.progress_signal.emit(f"Ярлык в автозапуск ssh-add создан")
            logging.info(f"Начало копирования ключей")
            self.progress_signal.emit('\nКопирую ключ на все компьютеры:')
            run_command_in_xterm(f"ssh-add")
            for host in self.hosts.items_to_list():
                run_command_in_xterm(
                    f"ssh-copy-id -f -i /home/{user}/.ssh/id_ed25519.pub teacher@{host.hostname} -o IdentitiesOnly=yes"
                )
            logging.info(f"Ключи скопированы")
            self.progress_signal.emit("Настройка ssh для суперпользователя root на всех устройствах")
            for host in list_of_hosts:
                host = host.strip()
                self.progress_signal.emit(f"Попытка подключения к {host}")
                logging.info(f"Попытка подключения к {host}")
                try:
                    result = self.ssh_copy_to_root(host, self.root_pass)
                    if "[root@" not in result:
                        self.progress_signal.emit(f"Пароль root неверный для {host}")
                        logging.info(f"Пароль root неверный для {host}")
                except Exception as e:
                    logging.info(f"{e}  ---  Не удалось подключиться к {host}")
                    self.progress_signal.emit(f"Не удалось подключиться к {host}")
                    break
                self.progress_signal.emit(f"На {host} ssh для root настроен успешно")
                logging.info(f"На {host} ssh для root настроен успешно")

    def ssh_copy_to_root(self, host, root_pass):
        """
        Копирование ключей ssh от teacher в root
        :param host: имя или адрес хоста
        :param root_pass: пароль root на хосте
        :return: вывод результата от терминала
        """
        logging.info("Начало копирования ключей ssh to root")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        try:
            ssh.connect(hostname=host, port=22, timeout=5, username='teacher')
            logging.info(f"Подключено по ssh@teacher без пароля к {host}")

            channel: Channel = ssh.invoke_shell()
            channel_data = str()
            channel_data += str(channel.recv(999).decode('utf-8'))
            channel.send("su -\n")
            time.sleep(0.5)
            channel.send(f"{root_pass}\n")
            time.sleep(0.5)
            channel.send("cat /home/teacher/.ssh/authorized_keys > /root/.ssh/authorized_keys\n")
            time.sleep(0.5)
            channel.send("exit\n")
            time.sleep(0.5)
            channel.send("exit\n")
            time.sleep(0.5)
            channel_data += f"{str(channel.recv(99999).decode('utf-8'))}\n"
            channel.close()
            ssh.close()
            logging.info(f"Результат работы paramiko на {host}: {channel_data}")
            return channel_data
        except AuthenticationException as e:
            self.progress_signal.emit(f'Не правильно настроены ключи авторизации для teacher@{host}')
            logging.info(f"{e} Не удалось подключиться к ssh@teacher к {host}")
        except (timeout, SSHException) as e:
            self.progress_signal.emit(f'Не удалось подключиться к ssh teacher@{host}')
            logging.info(f"{e} Не удалось подключиться к ssh@teacher к {host}")
        except Exception as e:
            self.progress_signal.emit(f'Не удалось подключиться к ssh teacher@{host}')
            logging.info(f"{e} Не удалось подключиться к ssh teacher@{host}")
        finally:
            ssh.close()


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
        self.progress_signal.emit("НАЧАЛО НАСТРОЙКИ СЕТЕВЫХ ПАПОК")
        hosts_count = len(self.hosts.to_list())
        success_count = 0
        self.progress_signal.emit(
            'Создание сетевой папки share (/home/share) и отправка ссылки на компьютеры учеников'
        )
        run_command_by_root(f'mkdir -p /home/share && chmod 755 /home/share && chown {user} /home/share')
        with open(f'/home/{user}/Рабочий стол/share.desktop', 'w') as file_link_2:
            file_link_2.write(network_share_for_teacher)
        with open(f'{config_path}/share.desktop', 'w') as file_link:
            file_link.write(network_share.format(teacher_host=this_host))
        for host in self.hosts.items_to_list():
            if test_ssh(host):
                check_student = run_command(f"ssh root@{host} file /home/student").strip()
                if check_student.endswith('directory'):
                    run_command_in_xterm(
                        f"scp {config_path}/share.desktop root@{host.hostname}:'/home/student/Рабочий\ стол'"
                    )
                    self.progress_signal.emit(
                        f"{host}: ярлык на сетевую папку скопирован"
                    )
                    success_count += 1
                else:
                    self.progress_signal.emit(f'{host}: отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nКопирование ярлыка на сетевую папку не выполнено.")
        else:
            self.finish_signal.emit(
                f"\nКопирование ярлыка на сетевую папку завершилось.\n"
                f"Всего устройств: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


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
        self.progress_signal.emit("НАЧАЛО НАСТРОЙКИ VEYON")

        self.progress_signal.emit("Проверка мак-адресов проводных сетевых плат")
        for host in self.hosts.hosts:
            self.hosts.save_mac_address(
                host,
                get_mac_address(self.hosts.hosts[host]['hostname'])
            )
        self.progress_signal.emit("Мак-адреса проверены")

        self.progress_signal.emit("Установка veyon на компьютере учителя")
        logging.info(f'Установка вейон на компьютере учителя')
        network_objects = ''
        for host in self.hosts.items_to_list():
            mac_address = "aa:bb:cc:dd:ee:ff" if not host.mac_address else host.mac_address
            network_objects += f"veyon-cli networkobjects add " \
                               f"computer \"{host.name()}\" \"{host.hostname}\" \"{mac_address}\" \"{self.kab}\"; "
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
            f"{network_objects} "
            f"veyon-cli service start"
        )
        self.progress_signal.emit("Установка veyon на компьютере учителя завершена")
        logging.info(f'Установка вейон на комьютере учителя УСПЕШНО')

        logging.info(f'Установка вейон на комьютере учеников')
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
        self.thread.command = install_on_hosts
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.thread.finished.connect(lambda: self.progress_signal.emit("Перезагрузка устройства"))
        logging.info(f'Установка вейон на компьютере учеников УСПЕШНО')
        logging.info('Veyon установлен')


class SSHCommandExec(QThread):
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.command = None

    def run(self):
        if type(self.command) is str:
            self.run_command_on_ssh_from_str()
        elif type(self.command) is list:
            self.run_command_on_ssh_from_list(self.command)

    def run_command_on_ssh_from_str(self):
        self.progress_signal.emit(f"НАЧАЛО ВЫПОЛНЕНИЯ КОМАНДЫ:\n{self.command}")
        logging.info(f"Выполнение команды {self.command} на {self.hosts_list}")
        client = SSHClient()
        client.load_system_host_keys()
        for host in self.hosts_list:
            try:
                client.connect(hostname=host, username="root")
                stdin, stdout, stderr = client.exec_command(self.command)
                # print(f"{stdout.read().decode().strip()=}")
                result = stdout.read().decode().strip()
                self.progress_signal.emit(f"\nРезультат выполнения на {host}:\n{result}")
                # self.progress_signal.emit(f"{result}")
                logging.info(f"\nРезультат выполнения на {host}:\n\n{result}")
            except (AuthenticationException, SSHException, socket.gaierror):
                self.progress_signal.emit(f'Не удалось подключиться ssh root@{host}')
                logging.info(f"\nНе удалось подключиться по ssh@root без пароля к {host}")
            except Exception as e:
                self.progress_signal.emit(f'\n{host} неизвестная ошибка.')
                logging.info(f"неизвестная ошибка {host}: {e}")
        client.close()


    def run_command_on_ssh_from_list(self, commands_list: list):
        # self.progress_signal.emit(f"НАЧАЛО ВЫПОЛНЕНИЯ КОМАНД:\n{self.command}")
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
                self.progress_signal.emit(f'\nНе удалось подключиться ssh root@{host}')
                logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
            except Exception as e:
                self.progress_signal.emit(f'\n{host} неизвестная ошибка.')
                logging.info(f"неизвестная ошибка {host}: {e}")
        client.close()
