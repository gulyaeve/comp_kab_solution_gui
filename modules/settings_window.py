import logging
import re

from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QPlainTextEdit, QLabel, QLineEdit, QInputDialog, \
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QThreadPool

from modules.config import hostname_expression, version, ip_expression
from modules.hosts import Hosts
from modules.system import exit_app, user
from modules.settings_workers import SSHRootSetup, NetworkFolderSetup, VeyonSetup, \
    SSHCommandInThreads


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
        self.textfield.cursor = QTextCursor()
        self.textfield.setReadOnly(True)
        # self.textfield.setStyleSheet("QPlainTextEdit {background-color: black; color: white;}")
        # font = QFont('Courier New')
        # font.setBold(True)
        # font.setPixelSize(13)
        # self.textfield.setFont(font)
        grid.addWidget(self.textfield, 4, 0, 4, 1)

        hostslabel = QLabel('Список устройств:')
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
            self.hosts_table.setItem(0, 0, QTableWidgetItem('Введите сетевые имена устройств'))
        else:
            self.update_data()
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
            self.button_ssh = QPushButton('Настроить доступ по ssh')
            self.button_ssh.clicked.connect(self.setup_ssh)
            grid.addWidget(self.button_ssh, 0, 0)

            self.button_share = QPushButton('Создать сетевую папку')
            self.button_share.clicked.connect(self.network_folders)
            grid.addWidget(self.button_share, 1, 0)

            self.button_veyon = QPushButton('Установить Veyon')
            self.button_veyon.clicked.connect(self.install_veyon)
            grid.addWidget(self.button_veyon, 2, 0)

            self.command_exec = QPushButton('Выполнить команду')
            self.command_exec.clicked.connect(self.run_command_on_ssh)
            grid.addWidget(self.command_exec, 3, 0)

    def set_buttons_enabled(self, status: bool):
        self.button_ssh.setEnabled(status)
        self.button_share.setEnabled(status)
        self.button_veyon.setEnabled(status)
        self.command_exec.setEnabled(status)

    def update_data(self):
        self.hosts_table.blockSignals(True)
        font = QFont()
        font.setUnderline(True)
        font_ip = QFont()
        font_ip.setItalic(True)
        self.hosts_table.clear()
        self.hosts_table.setRowCount(len(self.hosts.to_list()))
        for index, host in enumerate(self.hosts.to_list()):
            item = QTableWidgetItem(host)
            if re.match(hostname_expression, host):
                item.setFont(font)
            if re.match(ip_expression, host):
                item.setFont(font_ip)
                # item.setForeground(QColor("green"))
                # item.setBackground(QColor("green"))
            # else:
            #     item.setBackground(QColor("red"))
            self.hosts_table.setItem(index, 0, item)
        self.hosts_table.blockSignals(False)

    def change_data(self, item: QTableWidgetItem):
        """
        Реагирует на изменение данных в таблице
        :param item: элемент таблицы
        """
        item_index = item.row()
        host = str(item.text())
        if len(self.hosts.to_list()) > item_index:
            del self.hosts[self.hosts.to_list()[item_index]]
        self.hosts[host] = host
        self.update_data()

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
            # print(f"{self.hosts.hosts=} {item_text=}")
            if item_text.split('.local')[0] in self.hosts.hosts:
                del self.hosts[item_text]
            self.update_data()

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
            self.update_data()

    def open_file_dialog(self):
        file_name = QFileDialog.getOpenFileName(
            self,
            directory=f"/home/{user}",
            caption='Импорт из текстового файла',
            filter='.txt'
        )
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

    def update_textfield(self, message):
        self.textfield.appendPlainText(message)

    def setup_ssh(self):
        messageBox = QMessageBox.information(
            self,
            "Важная информация!",
            f"Вы запустили настройку ssh для пользователей teacher и root на компьютерах, указанных в таблице.\n\n"
            f"Во время первичной настройки будет осуществляться подключение к компьютерам "
            f"и сохранение ключей аутентификации для пользователя teacher.\n"
            f"Для копирования ключей пользователю root потребуется ввести пароль (предполагается что он единый "
            f"на всех устройствах)\n\n"
            f"При сохренении ключей будет необходимо подтвердить действие "
            f"вводом слова Yes и вводом пароля от teacher на каждом устройстве.",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if messageBox == QMessageBox.Ok:
            root_pass, okPressed = QInputDialog.getText(
                self, "Введите пароль root",
                f"Введите пароль учётной записи суперпользователя root (для устройств учеников): ",
                QLineEdit.Password, "")
            if okPressed:
                self.thread = SSHRootSetup()
                self.thread.hosts = self.hosts
                self.thread.root_pass = root_pass

                self.thread.progress_signal.connect(self.update_textfield)
                self.thread.finished.connect(self.thread.deleteLater)
                self.thread.start()

                self.set_buttons_enabled(False)
                self.thread.finished.connect(
                    lambda: self.set_buttons_enabled(True)
                )
                self.thread.finished.connect(
                    lambda: self.textfield.appendPlainText("\nЗАВЕРШЕНИЕ НАСТРОЙКИ SSH")
                )

    def network_folders(self):
        messageBox = QMessageBox.information(
            self,
            "Важная информация!",
            f"Вы запустили настройку сетевой папки.\n\n"
            f"На компьютере учителя будет создана папка /home/share "
            f"к которой будет настроен доступ по протоколу sftp.\nДля доступа к этой папке с компьютеров учеников, "
            f"убедитесь что на данном компьютере есть учётная запись student.",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if messageBox == QMessageBox.Ok:
            self.thread = NetworkFolderSetup()
            self.thread.hosts = self.hosts

            self.thread.progress_signal.connect(self.update_textfield)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

            self.set_buttons_enabled(False)
            self.thread.finished.connect(
                lambda: self.set_buttons_enabled(True)
            )
            self.thread.finished.connect(
                lambda: self.textfield.appendPlainText("\nЗАВЕРШЕНИЕ НАСТРОЙКИ СЕТЕВЫХ ПАПОК")
            )

    def install_veyon(self):
        kab, okPressed = QInputDialog.getText(self, "Номер кабинета",
                                              f"Введите номер этого кабинета:",
                                              QLineEdit.Normal, "")
        if okPressed:
            self.thread = VeyonSetup()
            self.thread.hosts = self.hosts
            self.thread.kab = kab

            self.thread.progress_signal.connect(self.update_textfield)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

            self.set_buttons_enabled(False)
            self.thread.finished.connect(
                lambda: self.set_buttons_enabled(True)
            )
            self.thread.finished.connect(
                lambda: self.textfield.appendPlainText(
                    "\nКОМАНДЫ ДЛЯ НАСТРОЙКИ VEYON ОТПРАВЛЕНЫ НА КОМПЬЮТЕРЫ УЧЕНИКОВ\n"
                    "ДОЖДИТЕСЬ ПЕРЕЗАГРУЗКИ УСТРОЙСТВ И НЕ ЗАКРЫВАЙТЕ ЭТО ОКНО!")
            )

    def run_command_on_ssh(self):
        command, pressed = QInputDialog.getText(self, 'Команда',
                                                'Введите команду для выполнения на компьютерах учеников',
                                                QLineEdit.Normal)
        if pressed:
            self.update_textfield(f"НАЧАЛО ВЫПОЛНЕНИЯ КОМАНДЫ:\n{command}")
            pool = QThreadPool.globalInstance()
            for host in self.hosts.items_to_list():
                runnable = SSHCommandInThreads(host, command)
                runnable.progress_signal.signal.connect(self.update_textfield)
                pool.start(runnable)
            # self.thread = SSHCommandExec()
            # self.thread.hosts_list = self.hosts.to_list()
            # self.thread.command = command
            #
            # self.thread.progress_signal.connect(self.update_textfield)
            # self.set_buttons_enabled(False)
            # self.thread.start()
            # self.thread.finished.connect(
            #     lambda: self.textfield.appendPlainText(f"\nЗАВЕРШЕНИЕ ВЫПОЛНЕНИЯ КОМАНДЫ:\n{command}")
            # )
            # self.thread.finished.connect(
            #     lambda: self.set_buttons_enabled(True)
            # )
            # self.thread.finished.connect(self.thread.deleteLater)
