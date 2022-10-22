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

from config import config_path, hostname_expression
from desktop_entrys import ssh_add_link, veyon_link, network_share, network_share_for_teacher
from hosts import Hosts, Host
from system import exit_app, run_command, this_host, user


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
        self.setWindowTitle('Настройки компьютерного класса')
        self.setFixedWidth(700)
        # self.setFixedHeight(400)

        # TODO: Сделать нередактируемым
        self.textfield = QPlainTextEdit()
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

    def change_data(self, item):
        """
        Реагирует на изменение данных в таблице
        :param item: элемент таблицы
        """
        host = str(item.text())
        self.hosts_table.blockSignals(True)
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
        self.hosts_table.setRowCount(self.hosts_table.rowCount()+1)

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
            del self.hosts[item_text.split('.')[0]]
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
        hosts = self.hosts.to_list()
        if hosts:
            print("\nСписок устройств найден, выполняю ping всех устройств:")
            self.textfield.appendPlainText("\nСписок устройств найден, выполняю ping всех устройств:")
            errors = 0
            list_of_hosts = []
            for host in hosts:
                # host = host.split('\n')[0]
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
                list_of_hosts.append(host)
            if errors > 0:
                print("Некоторые компьютеры найти не удалось, "
                      "проверьте правильность имён или адресов и повторите попытку.")
                self.textfield.appendPlainText("Некоторые компьютеры найти не удалось, "
                                               "проверьте правильность имён или адресов и повторите попытку.")
            return list_of_hosts
        else:
            self.textfield.appendPlainText(
                'Заполните список устройств: '
                'перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
                '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local\n'
                'Если по имени компьютеры не находятся, '
                'то используйте ip-адреса, но так делать не рекомендуется из-за смены адресов по DHCP.')

    def test_ssh(self):
        """
        Проверка подключения к хостам пользователем root
        """
        print("\nПроверяю доступ по ssh к компьютерам")
        self.textfield.appendPlainText("\nПроверяю доступ по ssh к компьютерам")
        list_of_hosts = self.ping()
        if list_of_hosts:
            errors = 0
            ssh_hosts = []
            for host in list_of_hosts:
                host = host.split('\n')[0]
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    ssh.connect(hostname=host, port=22, timeout=5, username='root')
                    logging.info(f"Подключено по ssh@root без пароля к {host}")
                    self.textfield.appendPlainText(f"Подключено по ssh@root без пароля к {host}")
                    ssh_hosts.append(host)
                except AuthenticationException:
                    print(f'Не удалось подключиться ssh root@{host}')
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
            root_pass, okPressed = QInputDialog.getText(
                self, "Введите пароль",
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
        self.textfield.setPlainText('Installing Veyon...')
        ssh_hosts = self.test_ssh()
        if ssh_hosts:
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
        else:
            self.textfield.appendPlainText(
                '\nДля настройки veyon необходимо сначала настроить ssh')

    def network_folders(self):
        """
        Создание сетевой папки и копирование ярлыка по ssh на хосты
        """
        logging.info("Создание сетевой папки")
        self.textfield.setPlainText('Creating share...')
        ssh_hosts = self.test_ssh()
        if ssh_hosts:
            self.textfield.appendPlainText(
                'Создаю сетевую папку share (/home/share) и отправляю ссылку на компы учеников, '
                'введите пароль суперпользователя на '
                'этом компьютере: ')
            # TODO: Не очень правильно создавать папку в хоум, нужно подумать куда перенести
            # TODO: настроить shh root localhost
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
        else:
            self.textfield.appendPlainText(
                "\nДля настройки сетевой папка необходимо сначала настроить ssh"
            )

    def save_hosts(self):
        # TODO: Добавить получение имён из таблицы
        self.hosts.update(self.hostsfield.toPlainText())
        # with open(f'{config_path}/hosts.txt', 'w') as out:
        #     print(self.hostsfield.toPlainText(), file=out)

    def get_mac_address(self, hostname): # TODO нужно тестировать
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

    # TODO: Добавить валидацию имён
    def open_file_dialog(self):
        fileName = QFileDialog.getOpenFileName(self, f"/home/{user}", '', '.txt')
        # fileName = QFileDialog.getOpenFileName(self)
        try:
            with open(fileName[0], 'r') as inp:
                lines = inp.readlines()
                if len(lines) > 1000:
                    QMessageBox('Слишком большой файл!').show()
                else:
                    self.hosts_table.setRowCount(len(lines))
                    for index, host in enumerate(lines):
                        self.hosts_table.setItem(index, 0, QTableWidgetItem(host.strip()))
        except FileNotFoundError:
            pass
