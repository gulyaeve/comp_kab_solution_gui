import logging
import re

from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtWidgets import QGridLayout, QPushButton, QPlainTextEdit, QLabel, QLineEdit, QInputDialog, \
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QThreadPool

from modules.config import hostname_expression, version, ip_expression
from modules.hosts import Hosts
from modules.system import user, CompKabSolutionWindow
from modules.workers import SSHRootSetup, NetworkFolderSetup, VeyonSetup, \
    SSHCommandInThreads, PingTest


class SettingsWindow(CompKabSolutionWindow):
    def __init__(self):
        super().__init__()

        self.hosts = Hosts()

        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle(f'Настройка компьютерного кабинета, версия {version}')
        # self.setFixedWidth(700)
        self.setMinimumWidth(600)

        self.textfield = QPlainTextEdit()
        self.textfield.cursor = QTextCursor()
        self.textfield.setReadOnly(True)
        grid.addWidget(self.textfield, 5, 0, 4, 1)

        hostslabel = QLabel('Список устройств:')
        hostslabel.setAlignment(Qt.AlignCenter)
        grid.addWidget(hostslabel, 0, 1, 1, 2)

        open_filebtn = QPushButton('Открыть файл...')
        open_filebtn.clicked.connect(self.open_file_dialog)
        grid.addWidget(open_filebtn, 0, 3)

        self.hosts_table = QTableWidget()
        self.hosts_table.setColumnCount(2)
        self.hosts_table.setHorizontalHeaderLabels(["Название", "Адрес"])
        self.update_data()

        self.hosts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        grid.addWidget(self.hosts_table, 1, 1, 7, 3)
        self.hosts_table.itemChanged.connect(self.change_data)

        button = QPushButton('+')
        button.clicked.connect(self.add_row)
        grid.addWidget(button, 8, 1)

        button = QPushButton('-')
        button.clicked.connect(self.delete_row)
        grid.addWidget(button, 8, 2)

        button = QPushButton('Очистить...')
        button.clicked.connect(self.delete_all)
        grid.addWidget(button, 8, 3)

        if user == 'root':
            logging.info("Попытка запустить от рута")
            messageBox = QMessageBox.warning(
                self,
                "Неверный пользователь!",
                f"Данное приложение не следует запускать от имени суперпользователя",
                QMessageBox.Ok,
            )
            if messageBox == QMessageBox.Ok:
                self.close()
        elif user == 'student':
            logging.info("Попытка запустить от студента")
            messageBox = QMessageBox.warning(
                self,
                "Неверный пользователь!",
                f"Данное приложение не следует запускать от имени ученика",
                QMessageBox.Ok,
            )
            if messageBox == QMessageBox.Ok:
                self.close()
        else:
            self.button_ping = QPushButton('Проверить ping')
            self.button_ping.clicked.connect(self.test_ping)
            grid.addWidget(self.button_ping, 0, 0)

            self.button_ssh = QPushButton('Настроить доступ по ssh')
            self.button_ssh.clicked.connect(self.setup_ssh)
            grid.addWidget(self.button_ssh, 1, 0)

            self.button_share = QPushButton('Создать сетевую папку')
            self.button_share.clicked.connect(self.network_folders)
            grid.addWidget(self.button_share, 2, 0)

            self.button_veyon = QPushButton('Установить Veyon')
            self.button_veyon.clicked.connect(self.install_veyon)
            grid.addWidget(self.button_veyon, 3, 0)

            self.command_exec = QPushButton('Выполнить команду')
            self.command_exec.clicked.connect(self.run_command_on_ssh)
            grid.addWidget(self.command_exec, 4, 0)

    def set_buttons_status(self, status: bool):
        self.button_ping.setEnabled(status)
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
        self.hosts_table.setHorizontalHeaderLabels(["Название", "Адрес"])
        self.hosts_table.setRowCount(len(self.hosts))
        for index, host in enumerate(self.hosts.items_to_list()):
            item_name = QTableWidgetItem(host.name)
            item_hostname = QTableWidgetItem(host.hostname)
            if re.match(hostname_expression, host.hostname):
                item_hostname.setFont(font)
            if re.match(ip_expression, host.hostname):
                item_hostname.setFont(font_ip)
            self.hosts_table.setItem(index, 0, item_name)
            self.hosts_table.setItem(index, 1, item_hostname)
        self.hosts_table.blockSignals(False)

    def change_data(self, item: QTableWidgetItem):
        """
        Реагирует на изменение данных в таблице
        :param item: элемент таблицы
        """
        item_index = item.row()
        key = self.hosts_table.item(item_index, 0).text()
        hostname = self.hosts_table.item(item_index, 1).text() if self.hosts_table.item(item_index, 1) else ""
        if len(self.hosts.to_list()) > item_index:
            del self.hosts[self.hosts.to_list()[item_index]]
        self.hosts.set_item(key, hostname)
        self.update_data()

    def add_row(self):
        """
        Добавление пустой строки
        """
        number = self.hosts_table.rowCount()
        item_name = QTableWidgetItem(f"Компьютер {number + 1}")
        self.hosts_table.setRowCount(number + 1)
        self.hosts_table.setItem(number, 0, item_name)

    def delete_row(self):
        """
        Удаление строки и удаление из файла
        """
        row = self.hosts_table.currentRow()
        if row < 0:
            return
        if not self.hosts_table.currentItem():
            self.hosts_table.removeRow(row)
        else:
            key = self.hosts_table.item(row, 0).text()
            messageBox = QMessageBox.warning(
                self,
                "Подтверждение удаления!",
                f"Вы действительно хотите удалить {key}?",
                QMessageBox.Ok | QMessageBox.Cancel,
            )
            if messageBox == QMessageBox.Ok:
                if key in self.hosts.hosts:
                    del self.hosts[key]
                self.update_data()

    def delete_all(self):
        """
        Очистка таблицы и удаление из файла
        """
        message_box = QMessageBox.warning(
            self,
            "Подтверждение удаления!",
            f"Вы действительно хотите очистить список устройств?",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if message_box == QMessageBox.Ok:
            self.hosts.clean()
            self.update_data()

    def open_file_dialog(self):
        file_name = QFileDialog.getOpenFileName(
            self,
            directory=f"/home/{user}",
            caption='Импорт из текстового файла',
            filter='*.txt'
        )
        # file_name = QFileDialog.getOpenFileName(self)
        try:
            with open(file_name[0], 'r') as inp:
                lines = inp.readlines()
                if len(lines) > 1000:
                    QMessageBox('Слишком большой файл!').show()
                else:
                    for index, host in enumerate(lines):
                        new_index = self.hosts_table.rowCount() + 1
                        self.hosts_table.setRowCount(new_index)
                        self.hosts_table.setItem(new_index - 1, 0, QTableWidgetItem(f"Host {index + 1}"))
                        self.hosts_table.setItem(new_index - 1, 1, QTableWidgetItem(host.strip()))
        except FileNotFoundError:
            pass

    def update_textfield(self, message):
        self.textfield.appendPlainText(message)

    def test_ping(self):
        self.textfield.clear()

        self.thread = PingTest()
        self.thread.hosts = self.hosts

        self.thread.progress_signal.connect(self.update_textfield)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.set_buttons_status(False)
        self.thread.finished.connect(
            lambda: self.set_buttons_status(True)
        )
        self.thread.finished.connect(
            lambda: self.textfield.appendPlainText("\nЗАВЕРШЕНИЕ ПРОВЕРКИ PING")
        )

    def setup_ssh(self):
        self.textfield.clear()
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

                self.set_buttons_status(False)
                self.thread.finished.connect(
                    lambda: self.set_buttons_status(True)
                )
                self.thread.finished.connect(
                    lambda: self.textfield.appendPlainText("\nЗАВЕРШЕНИЕ НАСТРОЙКИ SSH")
                )

    def network_folders(self):
        self.textfield.clear()
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

            self.set_buttons_status(False)
            self.thread.finished.connect(
                lambda: self.set_buttons_status(True)
            )
            self.thread.finished.connect(
                lambda: self.textfield.appendPlainText("\nЗАВЕРШЕНИЕ НАСТРОЙКИ СЕТЕВЫХ ПАПОК")
            )

    def install_veyon(self):
        self.textfield.clear()
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

            self.set_buttons_status(False)
            self.thread.finished.connect(
                lambda: self.set_buttons_status(True)
            )
            self.thread.finished.connect(
                lambda: self.textfield.appendPlainText(
                    "\nКОМАНДЫ ДЛЯ НАСТРОЙКИ VEYON ОТПРАВЛЕНЫ НА КОМПЬЮТЕРЫ УЧЕНИКОВ\n"
                    "ДОЖДИТЕСЬ ПЕРЕЗАГРУЗКИ УСТРОЙСТВ")
            )

    def run_command_on_ssh(self):
        self.textfield.clear()
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
