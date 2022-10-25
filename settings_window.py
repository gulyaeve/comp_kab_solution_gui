import logging
import re
import subprocess
import time
from _socket import timeout
import paramiko
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QPlainTextEdit, QLabel, QLineEdit, QInputDialog, \
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem
from paramiko.channel import Channel
from paramiko.ssh_exception import AuthenticationException, SSHException
from PyQt5.QtCore import Qt

from config import config_path, hostname_expression, version
from desktop_entrys import ssh_add_link, veyon_link, network_share, network_share_for_teacher
from hosts import Hosts
from system import exit_app, run_command, this_host, user, run_command_in_xterm, run_command_by_root


class SSHTimeoutError(Exception):
    pass


class WrongRootPass(Exception):
    pass


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.hosts = Hosts()

        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle(f'Настройка компьютерного кабинета, версия {version}')
        self.setFixedWidth(700)
        # self.setFixedHeight(400)

        self.textfield = QPlainTextEdit()
        self.textfield.setReadOnly(True)
        grid.addWidget(self.textfield, 4, 0, 4, 1)

        hostslabel = QLabel('Список хостов:')
        hostslabel.setAlignment(Qt.AlignCenter)
        grid.addWidget(hostslabel, 0, 1, 1, 2)

        open_filebtn = QPushButton('Открыть файл...')
        open_filebtn.clicked.connect(self.open_file_dialog)
        grid.addWidget(open_filebtn, 0, 3)

        self.hosts_table = QTableWidget()
        self.hosts_table.setColumnCount(1)
        self.hosts_table.setColumnWidth(0, 238)
        if not self.hosts:
            self.hosts_table.setRowCount(1)
            self.hosts_table.setItem(0, 0, QTableWidgetItem('Введите сюда имена хостов'))
        else:
            self.hosts_table.clear()
            self.hosts_table.setRowCount(len(self.hosts.to_list()))
            for index, host in enumerate(self.hosts.to_list()):
                item = QTableWidgetItem(host)
                if re.match(hostname_expression, host):
                    item.setBackground(QColor("green"))
                else:
                    item.setBackground(QColor("red"))
                self.hosts_table.setItem(index, 0, item)
        grid.addWidget(self.hosts_table, 1, 1, 6, 3)
        self.hosts_table.itemChanged.connect(self.change_data)

        button = QPushButton('+')
        button.clicked.connect(self.add_row)
        grid.addWidget(button, 7, 1)

        button = QPushButton('-')
        button.clicked.connect(self.delete_row)
        grid.addWidget(button, 7, 2)

        button = QPushButton('Очистить...')
        button.clicked.connect(self.delete_all)
        grid.addWidget(button, 7, 3)

        if user == 'root':
            logging.info("Попытка запустить от рута")
            messageBox = QMessageBox.warning(
                self,
                "Неверный пользователь!",
                f"Данное приложение не следует запускать от имени суперпользователя",
                QMessageBox.Ok,
            )
            if messageBox == QMessageBox.Ok:
                exit_app()
        elif user == 'student':
            logging.info("Попытка запустить от студента")
            messageBox = QMessageBox.warning(
                self,
                "Неверный пользователь!",
                f"Данное приложение не следует запускать от имени ученика",
                QMessageBox.Ok,
            )
            if messageBox == QMessageBox.Ok:
                exit_app()
        else:
            button_ssh = QPushButton('Настроить доступ по ssh')
            button_ssh.clicked.connect(self.setup_ssh)
            grid.addWidget(button_ssh, 0, 0)

            button_share = QPushButton('Создать сетевую папку share')
            button_share.clicked.connect(self.network_folders)
            grid.addWidget(button_share, 1, 0)

            button_veyon = QPushButton('Установить Veyon на всех компьютерах')
            button_veyon.clicked.connect(self.install_veyon)
            grid.addWidget(button_veyon, 2, 0)

    def change_data(self, item: QTableWidgetItem):
        """
        Реагирует на изменение данных в таблице
        :param item: элемент таблицы
        """
        self.hosts_table.blockSignals(True)
        item_index = item.row()
        host = str(item.text())
        if len(self.hosts.to_list()) > item_index:
            del self.hosts[self.hosts.to_list()[item_index]]
        self.hosts[host] = host
        self.hosts_table.clear()
        self.hosts_table.setRowCount(len(self.hosts.to_list()))
        for index, host in enumerate(self.hosts.to_list()):
            item = QTableWidgetItem(host)
            if re.match(hostname_expression, host):
                item.setBackground(QColor("green"))
            else:
                item.setBackground(QColor("red"))
            self.hosts_table.setItem(index, 0, item)
        self.hosts_table.blockSignals(False)

    def add_row(self):
        """
        Добавление пустой строки
        """
        self.hosts_table.setRowCount(self.hosts_table.rowCount() + 1)

    def delete_row(self):
        """
        Удаление строки и удаление из файла
        """
        row = self.hosts_table.currentRow()
        if row < 0:
            return
        item_text = str(self.hosts_table.currentItem().text())
        messageBox = QMessageBox.warning(
            self,
            "Подтверждение удаления!",
            f"Вы действительно хотите удалить компьютер {item_text}?",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if messageBox == QMessageBox.Ok:
            del self.hosts[item_text]
            self.hosts_table.clear()
            self.hosts_table.setRowCount(len(self.hosts.to_list()))
            for index, host in enumerate(self.hosts.to_list()):
                item = QTableWidgetItem(host)
                if re.match(hostname_expression, host):
                    item.setBackground(QColor("green"))
                else:
                    item.setBackground(QColor("red"))
                self.hosts_table.setItem(index, 0, item)

    def delete_all(self):
        """
        Очистка таблицы и удаление из файла
        """
        messageBox = QMessageBox.warning(
            self,
            "Подтверждение удаления!",
            f"Вы действительно хотите очистить список устройств?",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if messageBox == QMessageBox.Ok:
            self.hosts.clean()
            self.hosts_table.clear()
            self.hosts_table.setRowCount(len(self.hosts.to_list()))
            for index, host in enumerate(self.hosts.to_list()):
                item = QTableWidgetItem(host)
                if re.match(hostname_expression, host):
                    item.setBackground(QColor("green"))
                else:
                    item.setBackground(QColor("red"))
                self.hosts_table.setItem(index, 0, item)

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
            if okPressed:
                ssh.connect(hostname=host, port=22, timeout=5, username='teacher', password=teacher_pass)
                logging.info(f"Подключено по ssh@teacher С ПАРОЛЕМ к {host}")
        except timeout:
            logging.info(f"timeout Не удалось подключиться к ssh@teacher к {host}")
            raise SSHTimeoutError
        except SSHException:
            self.textfield.appendPlainText(f'Не удалось подключиться к ssh teacher@{host}')
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

    def ping(self):
        """
        Подключение к хостам и проверка ping
        :return: список хостов в случае успеха
        """
        hosts = self.hosts.to_list()
        if hosts:
            self.textfield.appendPlainText("\nСписок устройств найден, выполняю ping всех устройств:")
            errors = 0
            list_of_hosts = []
            for host in hosts:
                # host = host.split('\n')[0]
                result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
                if result.returncode == 0:
                    self.textfield.appendPlainText(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                    logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
                elif result.returncode == 2:
                    logging.info(f"ping: {host}: {result=} {result.returncode=}")
                    self.textfield.appendPlainText(f"ping: {host}: УСТРОЙСТВО НЕ НАЙДЕНО")
                    errors += 1
                else:
                    self.textfield.appendPlainText(host + " неизвестная ошибка")
                    logging.info(host + f" неизвестная ошибка {result=} {result.returncode=}")
                    errors += 1
                list_of_hosts.append(host)
            if errors > 0:
                self.textfield.appendPlainText("Некоторые компьютеры найти не удалось, "
                                               "проверьте правильность имён и повторите попытку.")
                return []
            return list_of_hosts
        else:
            self.textfield.appendPlainText(
                'Заполните список устройств: '
                'перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
                '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local\n'
                'Если по имени компьютеры не находятся, '
                'то используйте ip-адреса, но так делать не рекомендуется из-за смены адресов по DHCP.')
            return []

    def test_ssh(self):
        """
        Проверка подключения к хостам пользователем root
        """
        self.textfield.appendPlainText("\nПроверяю доступ по ssh к компьютерам")
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
                    self.textfield.appendPlainText(f"Подключено по ssh@root без пароля к {host}")
                    ssh_hosts.append(host)
                except AuthenticationException:
                    self.textfield.appendPlainText(f'Не удалось подключиться ssh root@{host}')
                    logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
                    errors += 1
                    return []
                return ssh_hosts
            if errors > 1:
                self.textfield.appendPlainText(
                    '\nssh не удалось настроить'
                )
        else:
            self.textfield.appendPlainText(
                '\nssh не настроен'
            )

    def setup_ssh(self):
        """
        Создание ключей ssh
        Копирование ключей на хосты для пользователя teacher
        Подключение к хостам под пользователем teacher и копирование ключей пользователю root
        """
        self.textfield.setPlainText('Setup ssh...')
        list_of_hosts = self.ping()
        if list_of_hosts:
            logging.info(f"Начало создания ключа")
            self.textfield.appendPlainText(f"\nСоздаю ключ ssh:")
            # print("\nСоздаю ключ ssh:")
            run_command_in_xterm(f"ssh-keygen -t ed25519 -q -P '' -f /home/{user}/.ssh/id_ed25519")
            logging.info(f"Ключ создан")
            time.sleep(1)
            run_command_in_xterm(f'mkdir -p /home/{user}/.config/autostart')
            with open(f'/home/{user}/.config/autostart/ssh-add.desktop', 'w') as file_link:
                file_link.write(ssh_add_link)
            logging.info(f"Ярлык в автозапуск ssh-add создан")
            logging.info(f"Начало копирования ключей")
            self.textfield.appendPlainText('\nКопирую ключ на все компьютеры:')
            run_command_in_xterm(f"ssh-add")
            for host in self.hosts.items_to_list():
                run_command_in_xterm(
                    f"ssh-copy-id -f -i /home/{user}/.ssh/id_ed25519.pub teacher@{host.hostname} -o IdentitiesOnly=yes"
                )
            logging.info(f"Ключи скопированы")
            self.textfield.appendPlainText("Теперь я настрою ssh для суперпользователя на всех устройствах")
            root_pass, okPressed = QInputDialog.getText(
                self, "Введите пароль",
                f"Введите пароль учётной записи суперпользователя root (для устройств учеников): ",
                QLineEdit.Password, "")
            if okPressed:
                for host in list_of_hosts:
                    host = host.strip()
                    self.textfield.appendPlainText(f"Пробую подключиться к {host}")
                    logging.info(f"Пробую подключиться к {host}")
                    try:
                        result = self.ssh_copy_to_root(host, root_pass)
                        if "[root@" not in result:
                            self.textfield.appendPlainText(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                            logging.info(f'Пароль root на {host} не подошёл 1 попытка')
                            root_pass2, okPressed = QInputDialog.getText(self, "Введите пароль",
                                                                         f"root@{host} password:",
                                                                         QLineEdit.Password, "")
                            if okPressed:
                                result2 = self.ssh_copy_to_root(host, root_pass2)
                                if "[root@" not in result2:
                                    logging.info(f'Пароль root на {host} не подошёл 2 попытка')
                                    raise WrongRootPass
                    except (SSHTimeoutError, WrongRootPass):
                        self.textfield.appendPlainText(f"Не удалось подключиться к {host}")
                        logging.info(f"Не удалось подключиться к {host}")
                        break
                    self.textfield.appendPlainText(f"На {host} ssh для root настроен успешно")
                    logging.info(f"На {host} ssh для root настроен успешно")

    def install_veyon(self):
        """
        Установка и настройка veyon: скачивание пакета, создание ключей, копирование списка хостов и настройка по ssh на
        хостах
        """
        self.textfield.setPlainText('Installing Veyon...')
        ssh_hosts = self.test_ssh()
        if ssh_hosts:
            kab, okPressed = QInputDialog.getText(self, "Номер кабинета",
                                                  f"Введите номер этого кабинета:",
                                                  QLineEdit.Normal, "")
            if okPressed:
                logging.info(f'Установка вейон на компьютере учителя')
                network_objects = ''
                for host in self.hosts.items_to_list():
                    mac_address = "aa:bb:cc:dd:ee:ff" if not host.mac_address else host.mac_address
                    network_objects += f"veyon-cli networkobjects add " \
                                       f"computer \"{host.name()}\" \"{host.hostname}\" \"{mac_address}\" \"{kab}\"; "
                run_command_by_root(
                    f"apt-get update -y; "
                    f"apt-get install veyon -y; "
                    f"rm {config_path}/teacher_public_key.pem; "
                    f"rm {config_path}/myconfig.json; "
                    f"veyon-cli config clear; "
                    f"veyon-cli config set Authentication/Method 1; "
                    "veyon-cli config set VncServer/Plugin {39d7a07f-94db-4912-aa1a-c4df8aee3879}; "
                    f"veyon-cli authkeys delete {user}/private; "
                    f"veyon-cli authkeys delete {user}/public; "
                    f"veyon-cli authkeys create {user}; "
                    f"veyon-cli authkeys setaccessgroup {user}/private {user}; "
                    f"veyon-cli authkeys export {user}/public {config_path}/teacher_public_key.pem; "
                    f"veyon-cli networkobjects clear; "
                    f"veyon-cli networkobjects add location {kab}; "
                    f"{network_objects}"
                    f"veyon-cli config export {config_path}/myconfig.json; "
                    f"veyon-cli service start"
                )
                logging.info(f'Установка вейон на комьютере учителя УСПЕШНО')
                self.textfield.appendPlainText(
                    "Настраиваю veyon на компьютерах учеников (должен быть доступ к root по ssh):"
                )
                logging.info(f'Установка вейон на комьютере учеников')
                copy_to_hosts = []
                for host in self.hosts.items_to_list():
                    copy_to_hosts.append(
                        f"scp {config_path}/teacher_public_key.pem root@{host.hostname}:/tmp/ && "
                        f"scp {config_path}/myconfig.json root@{host.hostname}:/tmp/ && "
                        f"ssh root@{host.hostname} 'apt-get update && "
                        f"apt-get -y install veyon && "
                        f"veyon-cli authkeys delete {user}/public; "
                        f"veyon-cli authkeys import {user}/public /tmp/teacher_public_key.pem && "
                        f"veyon-cli config import /tmp/myconfig.json && "
                        f"veyon-cli service start && "
                        f"reboot'"
                    )
                run_command_in_xterm(
                    f"ssh-add"
                )
                for command in copy_to_hosts:
                    run_command_in_xterm(command)
                logging.info(f'Установка вейон на компьютере учеников УСПЕШНО')

                self.textfield.appendPlainText("Создаю ярлык:")
                with open(f'/home/{user}/Рабочий стол/veyon.desktop', 'w') as file_link:
                    file_link.write(veyon_link)
                self.textfield.appendPlainText('Veyon установлен')
                logging.info('Veyon установлен')
        else:
            self.textfield.appendPlainText(
                '\nДля настройки veyon необходимо сначала настроить ssh'
            )

    def network_folders(self):
        """
        Создание сетевой папки и копирование ярлыка по ssh на хосты
        """
        logging.info("Создание сетевой папки")
        self.textfield.setPlainText('Создание сетевой папки...')
        ssh_hosts = self.test_ssh()
        if ssh_hosts:
            self.textfield.appendPlainText(
                'Создаю сетевую папку share (/home/share) и отправляю ссылку на компьютеры учеников')
            run_command_by_root(f'mkdir /home/share && chmod 755 /home/share && chown {user} /home/share')
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
            self.textfield.appendPlainText(
                "\nДля настройки сетевой папка необходимо сначала настроить ssh"
            )

    def get_mac_address(self, hostname):  # TODO нужно тестировать
        ip_address = subprocess.check_output(['ping', hostname, '-c', '1']).decode('utf-8').split('(')[1].split(')')[0]
        ifconfig_output = run_command(f'ssh root@{hostname} "ifconfig"')
        macAddress = ''
        for s in ifconfig_output:
            if s.startswith('e'):
                macAddress = s.split('HWaddr ')[1].rstrip()
            if s.strip() == '':
                logging.info(f'Компьютер {hostname} не подключён к проводной сети')
                return ''
            if ip_address in s:
                return macAddress
        return macAddress

    def open_file_dialog(self):
        file_name = QFileDialog.getOpenFileName(self, f"/home/{user}", '', '.txt')
        # file_name = QFileDialog.getOpenFileName(self)
        try:
            with open(file_name[0], 'r') as inp:
                lines = inp.readlines()
                if len(lines) > 1000:
                    QMessageBox('Слишком большой файл!').show()
                else:
                    self.hosts_table.setRowCount(len(lines))
                    for index, host in enumerate(lines):
                        self.hosts_table.setItem(index, 0, QTableWidgetItem(host.strip()))
        except FileNotFoundError:
            pass
