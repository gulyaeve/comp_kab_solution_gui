import logging
import subprocess
import time
from _socket import timeout

import paramiko
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QInputDialog, QLineEdit
from paramiko.channel import Channel
from paramiko.ssh_exception import AuthenticationException, SSHException

from desktop_entrys import ssh_add_link
from system import run_command_in_xterm, user


class SSHRootSetup(QThread):
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.hosts = None

    def run(self):
        self.setup_ssh()

    def ping(self):
        """
        Подключение к хостам и проверка ping
        :return: список хостов в случае успеха
        """
        hosts = self.hosts.to_list()
        if hosts:
            self.progress_signal.emit("\nСписок устройств найден, выполняю ping всех устройств:")
            # self.textfield.appendPlainText("\nСписок устройств найден, выполняю ping всех устройств:")
            errors = 0
            list_of_hosts = []
            for host in hosts:
                # host = host.split('\n')[0]
                result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
                if result.returncode == 0:
                    self.progress_signal.emit(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                    # self.textfield.appendPlainText(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                    logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
                elif result.returncode == 2:
                    logging.info(f"ping: {host}: {result=} {result.returncode=}")
                    self.progress_signal.emit(f"ping: {host}: УСТРОЙСТВО НЕ НАЙДЕНО")
                    # self.textfield.appendPlainText(f"ping: {host}: УСТРОЙСТВО НЕ НАЙДЕНО")
                    errors += 1
                else:
                    self.progress_signal.emit(f"ping: {host}: неизвестная ошибка")
                    # self.textfield.appendPlainText(host + " неизвестная ошибка")
                    logging.info(host + f" неизвестная ошибка {result=} {result.returncode=}")
                    errors += 1
                list_of_hosts.append(host)
            if errors > 0:
                self.progress_signal.emit("Некоторые компьютеры найти не удалось, "
                                          "проверьте правильность имён и повторите попытку.")
                # self.textfield.appendPlainText("Некоторые компьютеры найти не удалось, "
                #                                "проверьте правильность имён и повторите попытку.")
                return []
            return list_of_hosts
        else:
            # self.textfield.appendPlainText(
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
        # self.textfield.setPlainText('Setup ssh...')
        list_of_hosts = self.ping()
        if list_of_hosts:
            logging.info(f"Начало создания ключа")
            # self.textfield.appendPlainText(f"\nСоздаю ключ ssh:")
            self.progress_signal.emit(f"\nСоздаю ключ ssh:")
            # print("\nСоздаю ключ ssh:")
            run_command_in_xterm(f"ssh-keygen -t ed25519 -q -P '' -f /home/{user}/.ssh/id_ed25519")
            logging.info(f"Ключ создан")
            time.sleep(1)
            run_command_in_xterm(f'mkdir -p /home/{user}/.config/autostart')
            with open(f'/home/{user}/.config/autostart/ssh-add.desktop', 'w') as file_link:
                file_link.write(ssh_add_link)
            logging.info(f"Ярлык в автозапуск ssh-add создан")
            logging.info(f"Начало копирования ключей")
            # self.textfield.appendPlainText('\nКопирую ключ на все компьютеры:')
            self.progress_signal.emit('\nКопирую ключ на все компьютеры:')
            run_command_in_xterm(f"ssh-add")
            for host in self.hosts.items_to_list():
                run_command_in_xterm(
                    f"ssh-copy-id -f -i /home/{user}/.ssh/id_ed25519.pub teacher@{host.hostname} -o IdentitiesOnly=yes"
                )
            logging.info(f"Ключи скопированы")
            self.progress_signal.emit("Теперь я настрою ssh для суперпользователя на всех устройствах")
            # self.textfield.appendPlainText("Теперь я настрою ssh для суперпользователя на всех устройствах")
            root_pass, okPressed = QInputDialog.getText(
                self.window, "Введите пароль",
                f"Введите пароль учётной записи суперпользователя root (для устройств учеников): ",
                QLineEdit.Password, "")
            if okPressed:
                for host in list_of_hosts:
                    host = host.strip()
                    self.progress_signal.emit(f"Пробую подключиться к {host}")
                    # self.textfield.appendPlainText(f"Пробую подключиться к {host}")
                    logging.info(f"Пробую подключиться к {host}")
                    try:
                        result = self.ssh_copy_to_root(host, root_pass)
                        if "[root@" not in result:
                            # self.textfield.appendPlainText(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                            self.progress_signal.emit(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                            logging.info(f'Пароль root на {host} не подошёл 1 попытка')
                            root_pass2, okPressed = QInputDialog.getText(self.window, "Введите пароль",
                                                                         f"root@{host} password:",
                                                                         QLineEdit.Password, "")
                            if okPressed:
                                result2 = self.ssh_copy_to_root(host, root_pass2)
                                if "[root@" not in result2:
                                    logging.info(f'Пароль root на {host} не подошёл 2 попытка')
                                    # raise WrongRootPass
                    # except (SSHTimeoutError, WrongRootPass):
                    except Exception as e:
                        logging.info(f"{e}  ---  Не удалось подключиться к {host}")
                        self.progress_signal.emit(f"Не удалось подключиться к {host}")
                    #     self.textfield.appendPlainText(f"Не удалось подключиться к {host}")
                    #     logging.info(f"Не удалось подключиться к {host}")
                    #     break
                    # self.textfield.appendPlainText(f"На {host} ssh для root настроен успешно")
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
        try:
            ssh.connect(hostname=host, port=22, timeout=5, username='teacher')
            logging.info(f"Подключено по ssh@teacher без пароля к {host}")
        except AuthenticationException:
            teacher_pass, okPressed = QInputDialog.getText(self.window, "Введите пароль",
                                                           f"Введите пароль учётной записи teacher на {host}: ",
                                                           QLineEdit.Password, "")
            if okPressed:
                ssh.connect(hostname=host, port=22, timeout=5, username='teacher', password=teacher_pass)
                logging.info(f"Подключено по ssh@teacher С ПАРОЛЕМ к {host}")
        except timeout:
            logging.info(f"timeout Не удалось подключиться к ssh@teacher к {host}")
            # raise SSHTimeoutError
        except SSHException:
            # self.textfield.appendPlainText(f'Не удалось подключиться к ssh teacher@{host}')
            self.progress_signal.emit(f'Не удалось подключиться к ssh teacher@{host}')
            logging.info(f"SSHException Не удалось подключиться к ssh teacher@{host}")
            # exit_app()
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
        logging.info(f"Результат работы paramiko: {channel_data}")
        return channel_data
