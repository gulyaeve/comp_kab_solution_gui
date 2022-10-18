import logging
import os
import subprocess
import time
from _socket import timeout
from getpass import getpass

import paramiko
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QPlainTextEdit, QLabel
from paramiko.channel import Channel
from paramiko.ssh_exception import AuthenticationException, SSHException
from PyQt5.QtCore import Qt
from desktop_entrys import ssh_add_link, veyon_link, teacher_sh_link, network_share, network_share_for_teacher
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

        button = QPushButton('Установить Teacher Control и создать архивы домашних папок')
        button.clicked.connect(self.installTeacherControl)
        grid.addWidget(button, 3, 0)

        self.textfield = QPlainTextEdit()
        self.textfield.setPlainText('lalala')
        grid.addWidget(self.textfield, 4, 0, 4, 1)

        hostslabel = QLabel('Список хостов:')
        hostslabel.setAlignment(Qt.AlignCenter)
        grid.addWidget(hostslabel, 0, 1)

        self.hostsfield = QPlainTextEdit()
        if 'hosts.txt' in os.listdir(f'/home/{user}/.teacher_control'):
            self.hostsfield.setPlainText(''.join(open(f'/home/{user}/.teacher_control/hosts.txt', 'r').readlines()))
        else:
            with open(f'/home/{user}/.teacher_control/hosts.txt', 'w'):
                pass
            self.hostsfield.setPlainText('Введите сюда имена хостов')
        grid.addWidget(self.hostsfield, 1, 1, 6, 1)

        button = QPushButton('Сохранить список хостов')
        button.clicked.connect(self.saveHosts)
        grid.addWidget(button, 7, 1)

        if user == 'root':
            logging.info("Попытка запустить от рута")
            print("Данный скрипт не следует запускать от имени суперпользователя")
            self.textfield.appendPlainText("Данный скрипт не следует запускать от имени суперпользователя")
            # exit_app()
        if user == 'student':
            logging.info("Попытка запустить от студента")
            print("Данный скрипт не следует запускать от имени ученика")
            self.textfield.appendPlainText("Данный скрипт не следует запускать от имени ученика")
            # exit_app()
        if user != 'teacher':
            logging.info("Попытка запустить от другого пользователя")
            print("Данный скрипт возможно запустить только под teacher, ознакомьтесь с инструкцией\n")
            self.textfield.appendPlainText("Данный скрипт возможно запустить только под teacher, ознакомьтесь с инструкцией\n")
            # exit_app()
        logging.info(f"Попытка создать папку ~/.teacher_control")
        # self.textfield.appendPlainText(run_command(f'ls'))
        self.textfield.appendPlainText(run_command(f'mkdir -p ~/.teacher_control'))
        self.textfield.appendPlainText(run_command(f'touch ~/.teacher_control/hosts.txt'))
        logging.info(f"Успешно создана папка ~/.teacher_control")
        # try:
        #     with open(f"~/.teacher_control/hosts.txt", "r") as hosts:
        #         hosts.close()
        #     # self.textfield.appendPlainText(run_command(f'ln -s ~/.teacher_control/hosts.txt hosts.txt'))
        #     logging.info("файл host найден и открыт")
        # except (IOError, FileNotFoundError):
        #     with open(f"~/.teacher_control/hosts.txt", "w") as hosts:
        #         hosts.close()
        #     self.textfield.appendPlainText(run_command(f'ln -s ~/.teacher_control/hosts.txt hosts.txt'))
        #     print(
        #         'Сгенерирован файл hosts.txt, перечислите в нём имена компьютеров построчно и запустите скрипт '
        #         'повторно.\n\n '
        #         '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local, пример: m4444-5-kab1-1.local')
        #     logging.info("файл hosts не был найден, создан")
        #     exit_app()

    def setupssh(self):
        print('Setup ssh...') # это выводится
        self.textfield.setPlainText('Setup ssh...') # а вот это почему-то не работает. А в других функциях работает
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
            print(f"Введите пароль учётной записи teacher на {host}: ")
            teacher_pass = str(input())
            ssh.connect(hostname=host, port=22, timeout=5, username='teacher', password=teacher_pass)
            logging.info(f"Подключено по ssh@teacher С ПАРОЛЕМ к {host}")
        except timeout:
            logging.info(f"timeout Не удалось подключиться к ssh@teacher к {host}")
            raise SSHTimeoutError
        except SSHException:
            print('Ошибка ssh')
            logging.info(f"SSHException Не удалось подключиться к ssh@teacher к {host}")
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
        Подключение к хостам из hosts.txt и проверка ping
        :return: список хостов в случае успеха
        """
        try:
            with open("~/.teacher_control/hosts.txt", "r") as hosts:
                list_of_hosts = hosts.readlines()
        except IOError:
            print(f'\nСоздайте файл /home/{user}/.teacher_control/hosts.txt, '
                  f'перечислите в нём имена компьютеров построчно и запустите скрипт повторно')
            # exit_app()
        if len(list_of_hosts) == 0 or list_of_hosts[0] == '':
            print(
                'Заполните файл hosts.txt: перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
                '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local. '
                'Если по имени компьютеры не находятся, '
                'то используйте ip-адреса, но так делать не рекомендуется из-за смены адресов по DHCP.')
            exit_app()
        print("\nФайл hosts.txt найден, выполняю ping всех устройств:")
        errors = 0
        for host in list_of_hosts:
            host = host.split('\n')[0]
            result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
            if result.returncode == 0:
                print(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
                logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
            elif result.returncode == 2:
                logging.info(f"ping: {host}: {result=} {result.returncode=}")
                errors += 1
            else:
                print(host + " неизвестная ошибка")
                logging.info(host + f" неизвестная ошибка {result=} {result.returncode=}")
                errors += 1
        if errors > 0:
            print("Некоторые компьютеры найти не удалось, "
                  "проверьте правильность имён или адресов в hosts.txt и повторите попытку.")
            exit_app()
        return list_of_hosts

    def test_ssh(self):
        """
        Проверка подключения к хостам пользователем root
        """
        print("\nПроверяю доступ по ssh к компьютерам из hosts.txt:")
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
        self.textfield.appendPlainText(f"Начало создания ключа")
        print("\nСоздаю ключ ssh:")
        run_command("ssh-keygen -t ed25519 -q -P '' -f /home/teacher/.ssh/id_ed25519")
        logging.info(f"Ключ создан")
        time.sleep(1)
        run_command(f'mkdir -p ~/.config/autostart')
        with open(f'~/.config/autostart/ssh-add.desktop', 'w') as file_link:
            file_link.write(ssh_add_link)
        logging.info(f"Ярлык в автозапуск ss-add создан")
        logging.info(f"Начало копирования ключей")
        print('\nКопирую ключ на все компьютеры из списка hosts.txt:')
        run_command(f"ssh-add; for i in $(cat ~/.teacher_control/hosts.txt); do ssh-copy-id -f -i "
                    f"~/.ssh/id_ed25519.pub teacher@$i -o IdentitiesOnly=yes; done")
        logging.info(f"Ключи скопированы")
        print("Теперь я настрою ssh для суперпользователя на всех устройствах")
        print("Введите пароль учётной записи суперпользователя root (для устройств учеников): ")
        root_pass = str(getpass("root password:"))
        for host in list_of_hosts:
            host = host.split('\n')[0]
            print(f"Пробую подключиться к {host}")
            logging.info(f"Пробую подключиться к {host}")
            try:
                result = self.ssh_copy_to_root(host, root_pass)
                if "[root@" not in result:
                    print(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                    logging.info(f'Пароль root на {host} не подошёл 1 попытка')
                    root_pass2 = str(str(getpass(f"root@{host} password:")))
                    result2 = self.ssh_copy_to_root(host, root_pass2)
                    if "[root@" not in result2:
                        logging.info(f'Пароль root на {host} не подошёл 2 попытка')
                        raise WrongRootPass
            except (SSHTimeoutError, WrongRootPass):
                print(f"Не удалось подключиться к {host}")
                logging.info(f"Не удалось подключиться к {host}")
                break
            print(f"На {host} ssh для root настроен успешно")
            logging.info(f"На {host} ssh для root настроен успешно")

    def install_veyon(self):
        """
        Установка и настройка veyon: скачивание пакета, создание ключей, копирование списка хостов и настройка по ssh на
        хостах
        """
        print("Введите номер этого кабинета:")
        kab = input()
        print(
            'Сначала установим на этом компьютере, введите пароль от root и ждите окончания установки: ')
        logging.info(f'Установка вейон на комьютере учителя')
        run_command(
            "su - root -c 'apt-get update -y; apt-get install veyon -y; veyon-cli authkeys delete teacher/private; "
            "veyon-cli authkeys delete teacher/public; veyon-cli authkeys create teacher; veyon-cli authkeys "
            "setaccessgroup teacher/private teacher; veyon-cli authkeys export teacher/public "
            "/home/teacher/teacher_control/teacher_public_key.pem; veyon-cli networkobjects add location {}; for i in $("
            "cat /home/teacher/teacher_control/hosts.txt); do veyon-cli networkobjects add computer $i $i \"\" {}; done; "
            "veyon-cli config export /home/teacher/teacher_control/myconfig.json; veyon-cli service start'".format(kab,
                                                                                                                   kab)
        )
        logging.info(f'Установка вейон на комьютере учителя УСПЕШНО')

        print("Настраиваю veyon на компьютерах учеников (должен быть доступ к root по ssh):")
        logging.info(f'Установка вейон на комьютере учеников')
        run_command(
            'ssh-add; for i in $(cat /home/teacher/teacher_control/hosts.txt); do scp '
            '/home/teacher/teacher_control/teacher_public_key.pem root@$i:/tmp/ && scp '
            '/home/teacher/teacher_control/myconfig.json root@$i:/tmp/ && ssh root@$i "apt-get update && apt-get -y '
            'install veyon && veyon-cli authkeys delete teacher/public ; veyon-cli authkeys import teacher/public '
            '/tmp/teacher_public_key.pem && veyon-cli config import /tmp/myconfig.json && veyon-cli service start && '
            'reboot"; done '
        )
        logging.info(f'Установка вейон на компьютере учеников УСПЕШНО')

        print("Создаю ярлык:")
        with open('/home/teacher/Рабочий стол/veyon.desktop', 'w') as file_link:
            file_link.write(veyon_link)
        print('Veyon установлен')
        logging.info('Veyon установлен')

    def teacher_control_store(self):
        """
        Копирование программы для сбора работ и создание ярлыка
        """
        if 'teacher_control' not in os.listdir('/home/teacher'):
            run_command('mkdir -p /home/teacher/teacher_control')

        if 'teacher_control.sh' in os.listdir('/home/teacher/teacher_control'):
            run_command("rm -f /home/teacher/teacher_control/teacher_control.sh && cp teacher_control.sh "
                        "/home/teacher/teacher_control")
            print('Старая версия teacher_control заменена')
        else:
            run_command("cp teacher_control.sh /home/teacher/teacher_control")
            print('Скрипт teacher_control сохранён')

        with open('/home/teacher/Рабочий стол/Teacher Control.desktop', 'w') as file_link_2:
            file_link_2.write(teacher_sh_link)
            print('Успешно создан ярлык для teacher_control')
        logging.info('Успешно создан ярлык для teacher_control')

    def student_archive(self):
        """
        Подключение по ssh к хостам и создание архива /home/student
        """
        print("Начинаю сохранение папки student на всех устройствах в архив:")
        logging.info("Начинаю сохранение папки student на всех устройствах в архив")
        run_command(
            "ssh-add; for i in $(cat /home/teacher/teacher_control/hosts.txt); "
            "do ssh root@$i 'mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && "
            "chmod 777 /home/student/Рабочий\ стол/Сдать\ работы && "
            "cd /home && "
            "pkill -u student ; "
            "echo \"sleep 5 && tar cfz student.tar.gz student && reboot\" | at now'; done")
        print('Архивы созданы\nВведите пароль root на этом компьютере: ')
        logging.info('Архивы созданы')
        self.teacher_control_store()

    def network_folders(self):
        """
        Создание сетевой папки и копирование ярлыка по ssh на хосты
        """
        logging.info("Создание сетевой папки")
        print(
            'Создаю сетевую папку share в /home/ и отправлю ссылку на компы учеников, введите пароль суперпользователя на '
            'этом компьютере: ')
        run_command("su - root -c 'mkdir /home/share && chmod 755 /home/share && chown teacher /home/share'")
        with open('share.desktop', 'w') as file_link:
            file_link.write(network_share.format(teacher_host=this_host))
            file_link.close()

        run_command(
            'ssh-add; for i in $(cat /home/teacher/teacher_control/hosts.txt); do scp share.desktop '
            'root@$i:"/home/student/Рабочий\\ стол"; done')
        with open('/home/teacher/Рабочий стол/share.desktop', 'w') as file_link_2:
            file_link_2.write(network_share_for_teacher)

        print('Сетевая папка создана')
        logging.info('Сетевая папка создана')

    def saveHosts(self):
        with open(f'/home/{user}/.teacher_control/hosts.txt', 'w') as out:
            print(self.hostsfield.toPlainText(), file=out)

    # def main(self):
    #     """
    #     Главное меню
    #     """
    #     print('\n\n    ВНИМАНИЕ!\n\n'
    #           'Перед началом работы ознакомьтесь с инструкцией\n')
    #     if user == 'root':
    #         logging.info("Попытка запустить от рута")
    #         print("Данный скрипт не следует запускать от имени суперпользователя")
    #         exit_app()
    #     if user == 'student':
    #         logging.info("Попытка запустить от студента")
    #         print("Данный скрипт не следует запускать от имени ученика")
    #         exit_app()
    #     if user != 'teacher':
    #         logging.info("Попытка запустить от другого пользователя")
    #         print("Данный скрипт возможно запустить только под teacher, ознакомьтесь с инструкцией\n")
    #         exit_app()
    #     logging.info("Попытка создать папку /home/teacher/teacher_control")
    #     run_command('mkdir -p /home/teacher/teacher_control')
    #     logging.info("Успешно создана папка /home/teacher/teacher_control")
    #     try:
    #         with open("/home/teacher/teacher_control/hosts.txt", "r") as hosts:
    #             hosts.close()
    #         run_command('ln -s /home/teacher/teacher_control/hosts.txt hosts.txt')
    #         logging.info("файл host найден и открыт")
    #     except IOError:
    #         with open("/home/teacher/teacher_control/hosts.txt", "w") as hosts:
    #             hosts.close()
    #         run_command('ln -s /home/teacher/teacher_control/hosts.txt hosts.txt')
    #         print(
    #             'Сгенерирован файл hosts.txt, перечислите в нём имена компьютеров построчно и запустите скрипт '
    #             'повторно.\n\n '
    #             '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local, пример: m4444-5-kab1-1.local')
    #         logging.info("файл hosts не был найден, создан")
    #         exit_app()
    #
    #     while True:
    #         print('\nВыберите действие:\n\n'
    #               '[1] - настроить доступ по ssh для всех компьютеров из вашего файла hosts.txt\n'
    #               '[2] - создать сетевую папку share и копировать её ярлык на устройства учеников (требуется настроенный '
    #               'ssh)\n '
    #               '[3] - установить veyon на всех компьютерах в кабинете (требуется настроенный ssh)\n'
    #               '[4] - установить teacher_control и создать архив с папкой /home/student каждого устройства из файла '
    #               'hosts.txt (требуется настроенный ssh) '
    #               '\n\n[0] - выход')
    #         print("Введите номер действия и нажмите Enter:")
    #         logging.info("Открыто главное меню")
    #         answer = int(input())
    #         logging.info(f"Введено {answer}")
    #         if answer == 1:
    #             setup_ssh()
    #         if answer == 2:
    #             test_ssh()
    #             network_folders()
    #         if answer == 3:
    #             test_ssh()
    #             install_veyon()
    #         if answer == 4:
    #             test_ssh()
    #             student_archive()
    #         if answer == 0:
    #             exit_app()
