import logging
import socket
import subprocess
import time
from _socket import timeout

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal, QRunnable, QObject, QThreadPool
from paramiko.channel import Channel
from paramiko.client import SSHClient
from paramiko.ssh_exception import AuthenticationException, SSHException

from modules.config import config_path
from modules.desktop_entrys import ssh_add_link, network_share_for_teacher, network_share, veyon_link
from modules.hosts import Host, Hosts
from modules.system import run_command_in_xterm, run_command_in_konsole, user, run_command_by_root, this_host, \
    run_command, get_mac_address, test_ssh, test_ping, check_student_on_host


works_folder = 'install -d -m 0755 -o student -g student \\"/home/student/Рабочий стол/Сдать работы\\"'


class PingTest(QThread):
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts = None

    def run(self):
        self.progress_signal.emit("НАЧАЛО ПРОВЕРКИ PING\n")
        for host in self.hosts.items_to_list():
            if test_ping(host.hostname):
                logging.info(f"{host.hostname}: проверка ping успешно")
                self.progress_signal.emit(
                    f"{host.name}: проверка ping успешно"
                )
            else:
                logging.info(f"{host.hostname}: недоступен")
                self.progress_signal.emit(
                    f"{host.name}: недоступен"
                )


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
        hosts = self.hosts.items_to_list()
        if hosts:
            self.progress_signal.emit("\nСписок устройств найден, выполняю ping всех устройств:")
            errors = 0
            list_of_hosts = []
            for host in hosts:
                result = subprocess.run(['ping', '-c1', host.hostname], stdout=subprocess.PIPE)
                if result.returncode == 0:
                    self.progress_signal.emit(f"ping: {host.hostname}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                    logging.info(f"ping: {host.hostname}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
                elif result.returncode == 2:
                    logging.info(f"ping: {host.hostname}: {result=} {result.returncode=}")
                    self.progress_signal.emit(f"ping: {host.hostname}: УСТРОЙСТВО НЕ НАЙДЕНО")
                    errors += 1
                else:
                    self.progress_signal.emit(f"ping: {host.hostname}: неизвестная ошибка")
                    logging.info(host.hostname + f" неизвестная ошибка {result=} {result.returncode=}")
                    errors += 1
                list_of_hosts.append(host.hostname)
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
            run_command(f'mkdir -p /home/{user}/.config/autostart')
            with open(f'/home/{user}/.config/autostart/ssh-add.desktop', 'w') as file_link:
                file_link.write(ssh_add_link)
            logging.info(f"Ярлык в автозапуск ssh-add создан")
            self.progress_signal.emit(f"Ярлык в автозапуск ssh-add создан")
            logging.info(f"Начало копирования ключей")
            self.progress_signal.emit('\nКопирую ключ на все компьютеры:')
            run_command(f"ssh-add")
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
                    else:
                        self.progress_signal.emit(f"На {host} ssh для root настроен успешно")
                        logging.info(f"На {host} ssh для root настроен успешно")
                except Exception as e:
                    logging.info(f"{e}  ---  Не удалось подключиться к {host}")
                    self.progress_signal.emit(f"Не удалось подключиться к {host}")
                    break

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
        hosts_count = len(self.hosts.items_to_list())
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
                if check_student_on_host(host.hostname):
                    run_command(
                        f"scp {config_path}/share.desktop root@{host.hostname}:'/home/student/Рабочий\ стол'"
                    )
                    self.progress_signal.emit(
                        f"{host.hostname}: ярлык на сетевую папку скопирован"
                    )
                    success_count += 1
                    logging.info(f'{host.hostname} ярлык на сетевую папку скопирован')
                else:
                    self.progress_signal.emit(f'{host.hostname}: отсутствует student')
                    logging.info(f'{host.hostname} отсутствует student')
            else:
                self.progress_signal.emit(f'{host.hostname}: не в сети или не настроен ssh')
                logging.info(f'{host.hostname} не в сети или не настроен ssh')
        if success_count == 0:
            self.progress_signal.emit(f"\nКопирование ярлыка на сетевую папку не выполнено.")
        else:
            self.progress_signal.emit(
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
        for host in self.hosts.items_to_list():
            self.hosts.set_item(
                key=host.name,
                hostname=host.hostname,
                mac_address=get_mac_address(host.hostname))
        self.progress_signal.emit("Мак-адреса проверены")

        self.progress_signal.emit("Установка veyon на компьютере учителя")
        logging.info(f'Установка вейон на компьютере учителя')
        network_objects = ''
        for host in self.hosts.items_to_list():
            mac_address = "aa:bb:cc:dd:ee:ff" if not host.mac_address else host.mac_address
            name = host.name.replace(' ', '_')
            network_objects += f'veyon-cli networkobjects add ' \
                               f'computer "{name}" "{host.hostname}" "{mac_address}" "{self.kab}"; '
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
            f"{setup_wol}",
            f"apt-get update",
            f"apt-get -y install veyon",
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

        run_command(
            f"ssh-add"
        )

        self.progress_signal.emit("Копирование публичного ключа")
        for host in self.hosts.items_to_list():
            run_command(f"scp {config_path}/veyon_{user}_public_key.pem root@{host.hostname}:/tmp/")
            self.progress_signal.emit(f"{host.hostname}: ключ скопирован")
        self.progress_signal.emit("Отправка команд на установку")

        command_to_hosts = f"echo \"{'; '.join(install_on_hosts)}\" | at now"

        pool = QThreadPool.globalInstance()
        for host in self.hosts.items_to_list():
            runnable = SSHCommandInThreads(host, command_to_hosts)
            pool.start(runnable)
            logging.info(f"Отправка на {host.hostname}\nкоманды:\n{command_to_hosts}")
            self.progress_signal.emit(f"Команда установки veyon отправлена на {host.hostname}")
        logging.info('Завершение установки Veyon')


class WorkerSignals(QObject):
    signal = pyqtSignal(str)


class SSHCommandInThreads(QRunnable):
    def __init__(self, host: Host, command):
        super().__init__()
        self.progress_signal = WorkerSignals()
        self.host = host
        self.command = command

    def run(self) -> None:
        if type(self.command) is str:
            self.run_command_on_ssh_from_str()
        elif type(self.command) is list:
            self.run_command_on_ssh_from_list(self.command)

    def run_command_on_ssh_from_str(self):
        logging.info(f"Выполнение команды {self.command} на {self.host}")
        client = SSHClient()
        client.load_system_host_keys()
        try:
            client.connect(hostname=self.host.hostname, username="root", timeout=2)
            stdin, stdout, stderr = client.exec_command(self.command)
            result = stdout.read().decode().strip()
            self.progress_signal.signal.emit(f"\nРезультат выполнения на {self.host.hostname}:\n{result}")
            logging.info(f"\nРезультат выполнения на {self.host.hostname}:\n\n{result}")
        except (AuthenticationException, SSHException, socket.gaierror):
            self.progress_signal.signal.emit(f'Не удалось подключиться ssh root@{self.host.hostname}')
            logging.info(f"\nНе удалось подключиться по ssh@root без пароля к {self.host.hostname}")
        except Exception as e:
            self.progress_signal.signal.emit(f'{self.host.hostname} неизвестная ошибка.')
            logging.info(f"неизвестная ошибка {self.host.hostname}: {e}")
        finally:
            client.close()

    def run_command_on_ssh_from_list(self, commands_list: list):
        logging.info(f"Выполнение команды {commands_list} на {self.host.hostname}")
        client = SSHClient()
        client.load_system_host_keys()
        try:
            client.connect(hostname=self.host.hostname, username="root", timeout=2)
            for command in commands_list:
                stdin, stdout, stderr = client.exec_command(command)
                result = stdout.read().decode().strip()
                self.progress_signal.signal.emit(
                    f"\nРезультат выполнения {command} на {self.host.hostname}:\n\n{result}"
                )
                logging.info(
                    f"\nРезультат выполнения {command} на {self.host.hostname}:\n\n{result}"
                )
        except (AuthenticationException, SSHException, socket.gaierror):
            self.progress_signal.signal.emit(f'\nНе удалось подключиться ssh root@{self.host.hostname}')
            logging.info(f"Не удалось подключиться по ssh@root без пароля к {self.host.hostname}")
        except Exception as e:
            self.progress_signal.signal.emit(f'\n{self.host.hostname} неизвестная ошибка.')
            logging.info(f"неизвестная ошибка {self.host.hostname}: {e}")
        finally:
            client.close()


class UpdateList(QThread):
    progress_signal = pyqtSignal(list)
    hosts = None

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.continue_run = True

    def run(self):
        while self.continue_run:
            hosts = Hosts()
            if self.hosts.to_list() != hosts.to_list():
                self.progress_signal.emit(hosts.to_list())
                self.hosts = Hosts()
            time.sleep(1)

    def isFinished(self):
        self.continue_run = False


class GetWorks(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.date = None
        self.text = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nСбор работ начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    run_command(
                        f'mkdir -p "/home/{user}/Рабочий стол/Работы/"' + self.date + '/' + self.text + '/' + host
                    )

                    run_command(
                        f'ssh root@{host} \'{works_folder}\' && '
                        f'scp -r root@{host}:\'/home/student/Рабочий\ стол/Сдать\ работы/*\' '
                        f'\"/home/{user}/Рабочий стол/Работы/\"{self.date}/{self.text}/{host}'
                    )

                    self.progress_signal.emit(f'{host}: работы сохранены успешно')
                    logging.info(f'{host} работы сохранены успешно')
                    success_count += 1
                else:
                    self.progress_signal.emit(f'{host}: отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nСбор работ не выполнен.")
        else:
            self.finish_signal.emit(
                f"\nСбор работ завершился.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class CleanWorks(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nОчистка директорий для сбора работ начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    run_command(f'ssh root@{host} \'rm -rf /home/student/Рабочий\ стол/Сдать\ работы/*\'')
                    self.progress_signal.emit(f'{host}: очистка завершена')
                    logging.info(f'{host} очистка завершена')
                    success_count += 1
                else:
                    self.progress_signal.emit(f'{host}: отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nОчистка директорий для сбора работ не выполнена.")
        else:
            self.finish_signal.emit(
                f"\nОчистка директорий для сбора работ завершилась.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class RecreateStudent(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.student_pass = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nПересоздание student начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                command = f'echo \'' \
                          f'pkill -u student; ' \
                          f'sleep 2; ' \
                          f'userdel -rf student; ' \
                          f'useradd student && ' \
                          f'chpasswd <<<\'student:{self.student_pass}\' && ' \
                          f'{works_folder}\'| at now'
                if check_student_on_host(host):
                    run_command(f'ssh root@{host} \"{command}\"')
                    self.progress_signal.emit(f'{host}: student удален и создан заново')
                    logging.info(f'{host} student удален и создан заново')
                    success_count += 1
                else:
                    run_command(f'ssh root@{host} \"{command}\"')
                    self.progress_signal.emit(f'{host}: student создан')
                    logging.info(f'{host} student создан')
                    success_count += 1
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nПересоздание student не выполнено.")
        else:
            self.finish_signal.emit(
                f"\nПересоздание student завершилось.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class DeleteStudent(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.student_pass = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nУдаление student начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    command = f'echo \'pkill -u student; sleep 2; userdel -rf student\' | at now'
                    run_command(f'ssh root@{host} \"{command}\"')
                    self.progress_signal.emit(f'{host}: student удален')
                    logging.info(f'{host} student удален')
                    success_count += 1
                else:
                    self.progress_signal.emit(f'{host}: отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nУдаление student не выполнено.")
        else:
            self.finish_signal.emit(
                f"\nУдаление student завершилось.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class OpenSFTP(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nДиректории открываются\n"
        )
        # sftp_adresses = ["xdg-open"]
        for host in self.hosts_list:
            if test_ssh(host):
                # sftp_adresses.append(f'"sftp://root@{host}:/home/"')
                # sftp_adresses.append(f'sftp://root@{host}:/home/')
                self.progress_signal.emit(f'{host}: открыт проводник')
                logging.info(f'{host} открыт sftp')
                success_count += 1
                run_command_in_konsole(f'mc $HOME/Рабочий\ стол sh://root@{host}:/home')
                # run_command_in_xterm(f'dolphin --new-window sftp://root@{host}:/home')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        # command = " ".join(sftp_adresses)
        if success_count == 0:
            self.finish_signal.emit(f"\nОткрытие директорий не выполнено.")
        else:
            self.finish_signal.emit(
                f"\nОткрытие директорий завершилось.\n"
            )
