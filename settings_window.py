import logging
import os
import subprocess
import time
from _socket import timeout
# from getpass import getpass

import paramiko
import shutil

from PIL.ImageFont import truetype
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QPlainTextEdit, QLabel, QLineEdit, QInputDialog, \
    QFileDialog, QMessageBox, QTableView, QHeaderView
from paramiko.channel import Channel
from paramiko.ssh_exception import AuthenticationException, SSHException
from PyQt5.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

from classes import TableModel
from config import config_path
from desktop_entrys import ssh_add_link, veyon_link, network_share, network_share_for_teacher
from hosts import Hosts
from system import exit_app, run_command, this_host, user


class SSHTimeoutError(Exception):
    pass


class WrongRootPass(Exception):
    pass


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()

        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle('Настройки компьютерного класса')
        self.setFixedWidth(700)
        # self.setFixedHeight(400)

        button = QPushButton('Настроить доступ по ssh')
        button.clicked.connect(self.setupssh)
        grid.addWidget(button, 0, 0)

        button = QPushButton('Создать сетевую папку share')
        button.clicked.connect(self.createShare)
        grid.addWidget(button, 1, 0)

        button = QPushButton('Установить Veyon на всех компьютерах')
        button.clicked.connect(self.installVeyon)
        grid.addWidget(button, 2, 0)

        # TODO: Предполагаем что это заменим на rsync и "типовую" папку студента
        button = QPushButton('Создать архивы домашних папок')
        button.clicked.connect(self.installTeacherControl)
        grid.addWidget(button, 3, 0)

        self.textfield = QPlainTextEdit()
        self.textfield.setPlainText('lalala')
        grid.addWidget(self.textfield, 4, 0, 4, 1)

        hostslabel = QLabel('Список хостов:')
        hostslabel.setAlignment(Qt.AlignCenter)
        grid.addWidget(hostslabel, 0, 1)

        openFilebtn = QPushButton('Открыть файл...')
        openFilebtn.clicked.connect(self.openFileDialog)
        grid.addWidget(openFilebtn, 0, 2)

        self.hostsfield = QTableView()
        self.hostsfieldvalues = TableModel(['1654651', '23651', '35213'])
        self.hostsfield.setModel(self.hostsfieldvalues)
        self.hostsfield.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hosts = Hosts()
        if not self.hosts:
            self.hostsfield.setModel(TableModel([['Введите сюда имена хостов']]))
        else:
            self.hostsfield.setModel(TableModel(self.hosts))
        grid.addWidget(self.hostsfield, 1, 1, 6, 2)

        button = QPushButton('Сохранить список хостов')
        button.clicked.connect(self.saveHosts)
        grid.addWidget(button, 7, 1, 1, 2)

        if user == 'root':
            logging.info("Попытка запустить от рута")
            print("Данный скрипт не следует запускать от имени суперпользователя")
            self.textfield.appendPlainText("Данный скрипт не следует запускать от имени суперпользователя")
            exit_app()
        if user == 'student':
            logging.info("Попытка запустить от студента")
            print("Данный скрипт не следует запускать от имени ученика")
            self.textfield.appendPlainText("Данный скрипт не следует запускать от имени ученика")
            exit_app()

    def setupssh(self):
        print('Setup ssh...')  # это выводится
        self.textfield.setPlainText('Setup ssh...')
        self.setup_ssh()

    def createShare(self):
        print('Creating share...')
        self.textfield.setPlainText('Creating share...')

    def installVeyon(self):
        print('Installing Veyon...')
        self.textfield.appendPlainText('Installing Veyon...')

    def installTeacherControl(self):
        print('Installing Teacher Control...')
        self.textfield.appendPlainText('Installing Teacher Control...')

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
            teacher_pass, okPressed = QInputDialog.getText(self, "Введите пароль",
                                                           f"Введите пароль учётной записи teacher на {host}: ",
                                                           QLineEdit.Password, "")
            ssh.connect(hostname=host, port=22, timeout=5, username='teacher', password=teacher_pass)
            logging.info(f"Подключено по ssh@teacher С ПАРОЛЕМ к {host}")
        except timeout:
            logging.info(f"timeout Не удалось подключиться к ssh@teacher к {host}")
            raise SSHTimeoutError
        except SSHException:
            print(f'Не удалось подключиться к ssh teacher@{host}')
            self.textfield.appendPlainText(f'Не удалось подключиться к ssh teacher@{host}')
            logging.info(f"SSHException Не удалось подключиться к ssh teacher@{host}")
            exit_app()
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
        """
        Подключение к хостам и проверка ping
        :return: список хостов в случае успеха
        """
        list_of_hosts = self.hosts.to_list()
        if len(list_of_hosts) == 0 or list_of_hosts[0] == '':
            self.textfield.appendPlainText(
                'Заполните список устройств: перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
                '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local. '
                'Если по имени компьютеры не находятся, '
                'то используйте ip-адреса, но так делать не рекомендуется из-за смены адресов по DHCP.')
        else:
            print("\nСписок устройств найден, выполняю ping всех устройств:")
            self.textfield.appendPlainText("\nСписок устройств найден, выполняю ping всех устройств:")
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
                      "проверьте правильность имён или адресов и повторите попытку.")
                self.textfield.appendPlainText("Некоторые компьютеры найти не удалось, "
                                               "проверьте правильность имён или адресов и повторите попытку.")
                exit_app()
            return list_of_hosts

    def test_ssh(self):
        """
        Проверка подключения к хостам пользователем root
        """
        print("\nПроверяю доступ по ssh к компьютерам")
        self.textfield.appendPlainText("\nПроверяю доступ по ssh к компьютерам")
        list_of_hosts = self.ping()
        for host in list_of_hosts:
            host = host.split('\n')[0]
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(hostname=host, port=22, timeout=5, username='root')
                logging.info(f"Подключено по ssh@root без пароля к {host}")
            except AuthenticationException:
                print(f'Не удалось подключиться ssh root@{host}')
                self.textfield.appendPlainText(f'Не удалось подключиться ssh root@{host}')
                logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
                exit_app()
            ssh.close()

    def setup_ssh(self):
        """
        Создание ключей ssh
        Копирование ключей на хосты для пользователя teacher
        Подключение к хостам под пользователем teacher и копирование ключей пользователю root
        """
        list_of_hosts = self.ping()
        logging.info(f"Начало создания ключа")
        self.textfield.appendPlainText(f"\nСоздаю ключ ssh:")
        print("\nСоздаю ключ ssh:")
        run_command(f"ssh-keygen -t ed25519 -q -P '' -f /home/{user}/.ssh/id_ed25519")
        logging.info(f"Ключ создан")
        time.sleep(1)
        run_command(f'mkdir -p /home/{user}/.config/autostart')
        with open(f'/home/{user}/.config/autostart/ssh-add.desktop', 'w') as file_link:
            file_link.write(ssh_add_link)
        logging.info(f"Ярлык в автозапуск ssh-add создан")
        logging.info(f"Начало копирования ключей")
        print('\nКопирую ключ на все компьютеры')
        self.textfield.appendPlainText('\nКопирую ключ на все компьютеры:')
        run_command(f"ssh-add; for i in $({str(self.hosts)}); do ssh-copy-id -f -i "
                    f"/home/{user}/.ssh/id_ed25519.pub teacher@$i -o IdentitiesOnly=yes; done")
        logging.info(f"Ключи скопированы")
        print("Теперь я настрою ssh для суперпользователя на всех устройствах")
        self.textfield.appendPlainText("Теперь я настрою ssh для суперпользователя на всех устройствах")
        root_pass, okPressed = QInputDialog.getText(self, "Введите пароль",
                                                    f"Введите пароль учётной записи суперпользователя root (для устройств учеников): ",
                                                    QLineEdit.Password, "")

        for host in list_of_hosts:
            host = host.split('\n')[0]
            print(f"Пробую подключиться к {host}")
            self.textfield.appendPlainText(f"Пробую подключиться к {host}")
            logging.info(f"Пробую подключиться к {host}")
            try:
                result = self.ssh_copy_to_root(host, root_pass)
                if "[root@" not in result:
                    print(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                    # TODO: нужно окно ввода пароля (где??)
                    self.textfield.appendPlainText(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                    logging.info(f'Пароль root на {host} не подошёл 1 попытка')
                    # TODO: нужно окно ввода пароля v
                    # root_pass2 = str(str(getpass(f"root@{host} password:")))
                    root_pass2, okPressed = QInputDialog.getText(self, "Введите пароль",
                                                                 f"root@{host} password:",
                                                                 QLineEdit.Password, "")
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

    def install_veyon(self):
        """
        Установка и настройка veyon: скачивание пакета, создание ключей, копирование списка хостов и настройка по ssh на
        хостах
        """
        print("Введите номер этого кабинета:")
        kab, okPressed = QInputDialog.getText(self, "Номер кабинета",
                                              f"Введите номер этого кабинета:",
                                              QLineEdit.Normal, "")
        print('Сначала установим на этом компьютере, введите пароль от root и ждите окончания установки: ')
        # TODO: нужно понять как вводить пароль root (может тоже появляться окно, но тут может не сработать)
        logging.info(f'Установка вейон на комьютере учителя')
        run_command(
            "su - root -c '"
            "apt-get update -y;"
            "apt-get install veyon -y;"
            "veyon-cli authkeys delete teacher/private; "
            "veyon-cli authkeys delete teacher/public; "
            "veyon-cli authkeys create teacher; "
            "veyon-cli authkeys setaccessgroup teacher/private teacher; "
            "veyon-cli authkeys export teacher/public {config_path}/teacher_public_key.pem; "
            "veyon-cli networkobjects add location {kab}; "
            "for i in $({hosts}); "
            "do veyon-cli networkobjects add computer $i $i \"\" {kab}; done; "
            "veyon-cli config export {config_path}/myconfig.json; "
            "veyon-cli service start'".format(config_path=config_path, kab=kab, hosts=str(self.hosts))
        )
        logging.info(f'Установка вейон на комьютере учителя УСПЕШНО')

        print("Настраиваю veyon на компьютерах учеников (должен быть доступ к root по ssh):")
        logging.info(f'Установка вейон на комьютере учеников')
        run_command(
            f'ssh-add; '
            f'for i in $({str(self.hosts)}); do '
            f'scp {config_path}/teacher_public_key.pem root@$i:/tmp/ && '
            f'scp {config_path}/myconfig.json root@$i:/tmp/ && '
            f'ssh root@$i "apt-get update && '
            f'apt-get -y install veyon && '
            f'veyon-cli authkeys delete teacher/public; '
            f'veyon-cli authkeys import teacher/public /tmp/teacher_public_key.pem && '
            f'veyon-cli config import /tmp/myconfig.json && '
            f'veyon-cli service start && '
            'reboot"; done '
        )
        logging.info(f'Установка вейон на компьютере учеников УСПЕШНО')

        print("Создаю ярлык:")
        with open(f'/home/{user}/Рабочий стол/veyon.desktop', 'w') as file_link:
            file_link.write(veyon_link)
        print('Veyon установлен')
        logging.info('Veyon установлен')

    def student_archive(self):
        """
        Подключение по ssh к хостам и создание архива /home/student
        """
        print("Начинаю сохранение папки student на всех устройствах в архив:")
        logging.info("Начинаю сохранение папки student на всех устройствах в архив")
        run_command(
            f"ssh-add; "
            f"for i in $({str(self.hosts)}); "
            "do ssh root@$i 'mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && "
            "chmod 777 /home/student/Рабочий\ стол/Сдать\ работы && "
            "cd /home && "
            "pkill -u student ; "
            "echo \"sleep 5 && tar cfz student.tar.gz student && reboot\" | at now'; done")
        print('Архивы созданы\nВведите пароль root на этом компьютере: ')
        logging.info('Архивы созданы')
        # self.teacher_control_store()

    def network_folders(self):
        """
        Создание сетевой папки и копирование ярлыка по ssh на хосты
        """
        logging.info("Создание сетевой папки")
        print(
            'Создаю сетевую папку share в /home/ и отправлю ссылку на компы учеников, введите пароль суперпользователя на '
            'этом компьютере: ')
        # TODO: Не очень правильно создавать папку в хоум, нужно подумать куда перенести
        run_command("su - root -c 'mkdir /home/share && chmod 755 /home/share && chown teacher /home/share'")
        with open(f'{config_path}/share.desktop', 'w') as file_link:
            file_link.write(network_share.format(teacher_host=this_host))
            file_link.close()

        run_command(
            'ssh-add; '
            f'for i in $({str(self.hosts)}); '
            f'do scp {config_path}/share.desktop root@$i:"/home/student/Рабочий\\ стол"; '
            f'done')
        with open(f'/home/{user}/Рабочий стол/share.desktop', 'w') as file_link_2:
            file_link_2.write(network_share_for_teacher)

        print('Сетевая папка создана')
        logging.info('Сетевая папка создана')

    def saveHosts(self):
        self.hosts.update(self.hostsfield.toPlainText())
        # with open(f'{config_path}/hosts.txt', 'w') as out:
        #     print(self.hostsfield.toPlainText(), file=out)

    def getMacAddress(self, hostname): # TODO нужно тестировать
        ip_address = subprocess.check_output(['ping', hostname, '-c', '1']).decode('utf-8').split('(')[1].split(')')[0]
        ifconfig_output = run_command(f'ssh root@{hostname} "ifconfig"')
        macAddress = f'Компьютер {hostname} не подключён к проводной сети'
        for s in ifconfig_output:
            if s.startswith('e'):
                macAddress = s.split('HWaddr ')[1].rstrip()
            if s.strip() == '':
                macAddress = f'Компьютер {hostname} не подключён к проводной сети'
            if ip_address in s:
                return macAddress
        return macAddress

    def openFileDialog(self):
        fileName = QFileDialog.getOpenFileName(self, f"/home/{user}", '', '.txt')
        try:
            with open(fileName[0], 'r') as inp:
                lines = inp.readlines()
                if len(lines) > 1000:
                    QMessageBox('Слишком большой файл!').show()
                else:
                    self.hostsfield.setModel(TableModel([[i] for i in lines]))
        except FileNotFoundError:
            pass

