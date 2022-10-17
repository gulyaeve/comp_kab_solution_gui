#!/usr/bin/env python3

from getpass import getpass
import os
import sys
import subprocess
import logging
import time
from socket import *
import paramiko
from paramiko.channel import Channel
from paramiko.ssh_exception import AuthenticationException, SSHException
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QPlainTextEdit

logging.basicConfig(filename='log.txt',
                    format=u'%(asctime)s %(filename)s [LINE:%(lineno)d] [%(funcName)s()] #%(levelname)-15s %(message)s',
                    level=logging.INFO,
                    )

this_host = subprocess.run(['hostname'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0]
user = subprocess.run(['whoami'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0]

network_share = """[Desktop Entry]
Icon=folder-remote
Name=Задания
Type=Application
Exec=dolphin sftp://student@{teacher_host}.local/home/share
"""

network_share_for_teacher = """[Desktop Entry]
Icon=folder-remote
Name=Задания
Type=Link
URL[$e]=/home/share
"""

veyon_link = """[Desktop Entry]
Version=1.0
Type=Application
Exec=/usr/bin/veyon-master
Icon=/usr/share/icons/hicolor/scalable/apps/veyon-master.svg
Terminal=false
Name=Управление компьютерным классом
Comment=Monitor and control remote computers
Comment[de]=Entfernte Computer beobachten und steuern
Comment[ru]=Наблюдение за удалёнными компьютерами и управление ими (veyon)
Categories=Qt;Education;Network;RemoteAccess;
Keywords=classroom,control,computer,room,lab,monitoring,teacher,student
"""

teacher_sh_link = f"""[Desktop Entry]
Icon=/usr/share/icons/breeze-dark/apps/48/rocs.svg
Name=Собрать работы
Type=Application
Exec=sh /home/teacher/teacher_control/teacher_control.sh
"""

ssh_add_link = """[Desktop Entry]
Exec=ssh-add
Icon=
Name=ssh-add
Path=
Terminal=False
Type=Application
"""


class SSHTimeoutError(Exception):
    pass


class WrongRootPass(Exception):
    pass


class SettingsWindow(QWidget):
    def exit_app(self):
        logging.info("Выход из программы")
        print('Выход из программы...')
        sys.exit(0)

    def ssh_copy_to_root(self, host, root_pass):
        logging.info("Начало копирования ключей ssh to root")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(hostname=host, port=22, timeout=5, username='teacher')
            logging.info(f"Подключено по ssh@teacher без пароля к {host}")
        except AuthenticationException:
            print(f"Введите пароль учётной записи teacher на {host}: ")
            teacher_pass = str(input())
            ssh.connect(hostname=host, port=22, timeout=5, username='teacher', password=teacher_pass)
            logging.info(f"Подключено по ssh@teacher С ПАРОЛЕМ к {host}")
        except timeout:
            logging.info(f"timeout Не удалось подключиться к ssh@teacher к {host}")
            raise SSHTimeoutError
        except SSHException:
            print('Ошибка ssh')
            self.textfield.appendPlainText('Ошибка ssh')
            logging.info(f"SSHException Не удалось подключиться к ssh@teacher к {host}")
            self.exit_app()
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

    def ping(self):
        try:
            with open("/home/teacher/teacher_control/hosts.txt", "r") as hosts:
                list_of_hosts = hosts.readlines()
        except IOError:
            print(
                '\nСоздайте файл /home/teacher/teacher_control/hosts.txt, перечислите в нём имена компьютеров построчно и запустите скрипт повторно')
            self.textfield.appendPlainText(
                '\nСоздайте файл /home/teacher/teacher_control/hosts.txt, перечислите в нём имена компьютеров построчно и запустите скрипт повторно')
            self.exit_app()
        if len(list_of_hosts) == 0 or list_of_hosts[0] == '':
            print(
                'Заполните файл hosts.txt: перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
                '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local. Если по имени компьютеры не находятся, '
                'то используйте ip-адреса, но так делать не рекомендуется из-за смены адресов по DHCP.')
            self.textfield.appendPlainText(
                'Заполните файл hosts.txt: перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
                '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local. Если по имени компьютеры не находятся, '
                'то используйте ip-адреса, но так делать не рекомендуется из-за смены адресов по DHCP.')
            self.exit_app()
        print("\nФайл hosts.txt найден, выполняю ping всех устройств:")
        self.textfield.appendPlainText('\nФайл hosts.txt найден, выполняю ping всех устройств:')
        errors = 0
        for host in list_of_hosts:
            host = host.split('\n')[0]
            result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
            if result.returncode == 0:
                print(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                self.textfield.appendPlainText(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
            elif result.returncode == 2:
                logging.info(f"ping: {host}: {result=} {result.returncode=}")
                errors += 1
            else:
                print(host + " неизвестная ошибка")
                self.textfield.appendPlainText(host + " неизвестная ошибка")
                logging.info(host + f" неизвестная ошибка {result=} {result.returncode=}")
                errors += 1
        if errors > 0:
            print("Некоторые компьютеры найти не удалось, "
                  "проверьте правильность имён или адресов в hosts.txt и повторите попытку.")
            self.textfield.appendPlainText("Некоторые компьютеры найти не удалось, "
                                           "проверьте правильность имён или адресов в hosts.txt и повторите попытку.")
        return list_of_hosts

    def test_ssh(self):
        print("\nПроверяю доступ по ssh к компьютерам из hosts.txt:")
        self.textfield.appendPlainText("\nПроверяю доступ по ssh к компьютерам из hosts.txt:")
        list_of_hosts = self.ping()
        for host in list_of_hosts:
            host = host.split('\n')[0]
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(hostname=host, port=22, timeout=5, username='root')
                logging.info(f"Подключено по ssh@root без пароля к {host}")
            except AuthenticationException:
                print('Не удалось подключиться по ssh к', host)
                self.textfield.appendPlainText(f'Не удалось подключиться по ssh к {host}')
                logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
                self.exit_app()
            ssh.close()

    def setupssh(self):
        print('Setup ssh...')
        self.textfield.setPlainText('Setup ssh...')
        list_of_hosts = self.ping()
        logging.info(f"Начало создания ключа")
        print("\nСоздаю ключ ssh:")
        self.textfield.appendPlainText("\nСоздаю ключ ssh:")
        os.system("ssh-keygen -t ed25519 -q -P '' -f /home/teacher/.ssh/id_ed25519")
        logging.info(f"Ключ создан")
        time.sleep(1)
        os.system('mkdir -p /home/teacher/.config/autostart')
        with open('/home/teacher/.config/autostart/ssh-add.desktop', 'w') as file_link:
            file_link.write(ssh_add_link)
        logging.info(f"Ярлык в автозапуск ss-add создан")
        logging.info(f"Начало копирования ключей")
        print('\nКопирую ключ на все компьютеры из списка hosts.txt:')
        self.textfield.appendPlainText('\nКопирую ключ на все компьютеры из списка hosts.txt:')
        os.system(
            "ssh-add; for i in $(cat /home/teacher/teacher_control/hosts.txt); do ssh-copy-id -f -i /home/teacher/.ssh/id_ed25519.pub teacher@$i -o IdentitiesOnly=yes; done")
        logging.info(f"Ключи скопированы")
        print("Теперь я настрою ssh для суперпользователя на всех устройствах")
        print("Введите пароль учётной записи суперпользователя root (для устройств учеников): ")
        self.textfield.appendPlainText("Теперь я настрою ssh для суперпользователя на всех устройствах")
        self.textfield.appendPlainText(
            "Введите пароль учётной записи суперпользователя root (для устройств учеников): ")
        root_pass = str(getpass("root password:"))
        for host in list_of_hosts:
            host = host.split('\n')[0]
            print(f"Пробую подключиться к {host}")
            self.textfield.appendPlainText(f"Пробую подключиться к {host}")
            logging.info(f"Пробую подключиться к {host}")
            try:
                result = self.ssh_copy_to_root(host, root_pass)
                if "[root@" not in result:
                    print(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                    self.textfield.appendPlainText(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                    logging.info(f'Пароль root на {host} не подошёл 1 попытка')
                    root_pass2 = str(str(getpass(f"root@{host} password:")))
                    result2 = self.ssh_copy_to_root(host, root_pass2)
                    if "[root@" not in result2:
                        logging.info(f'Пароль root на {host} не подошёл 2 попытка')
                        raise WrongRootPass
            except (SSHTimeoutError, WrongRootPass):
                print(f"Не удалось подключиться к {host}")
                self.textfield.appendPlainText(f"Не удалось подключиться к {host}")
                logging.info(f"Не удалось подключиться к {host}")
                break
            print(f"На {host} ssh для root настроен успешно")
            self.textfield.appendPlainText(f"На {host} ssh для root настроен успешно")
            logging.info(f"На {host} ssh для root настроен успешно")

    def createShare(self):
        print('Creating share...')
        self.textfield.setPlainText('Creating share...')

    def installVeyon(self):
        print('Installing Veyon...')
        self.textfield.appendPlainText('Installing Veyon...')

    def installTeacherControl(self):
        print('Installing Teacher Control...')
        self.textfield.appendPlainText('Installing Teacher Control...')

    def __init__(self):
        super().__init__()
        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle('Настройки компьютерного класса')
        self.setFixedWidth(500)
        self.setFixedHeight(400)

        button = QPushButton('Настроить доступ по ssh')
        button.clicked.connect(self.setupssh)
        grid.addWidget(button, 0, 0)

        button = QPushButton('Создать сетевую папку share')
        button.clicked.connect(self.createShare)
        grid.addWidget(button, 1, 0)

        button = QPushButton('Установить Veyon на всех компьютерах')
        button.clicked.connect(self.installVeyon)
        grid.addWidget(button, 2, 0)

        button = QPushButton('Установить Teacher Control и создать архивы домашних папок')
        button.clicked.connect(self.installTeacherControl)
        grid.addWidget(button, 3, 0)

        self.textfield = QPlainTextEdit()
        self.textfield.setPlainText('lalala')
        grid.addWidget(self.textfield)
