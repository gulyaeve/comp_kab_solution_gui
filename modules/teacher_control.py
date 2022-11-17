# -*- coding: utf-8 -*-

import datetime
import logging

from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (QPushButton, QLineEdit,
                             QListWidget, QAbstractItemView, QMenuBar,
                             QInputDialog, QMessageBox, QWidget, QGridLayout, QListWidgetItem,
                             QPlainTextEdit)

from modules.config import version
from modules.help import HelpWindow
from modules.hosts import Hosts
from modules.update_list_worker import UpdateList
from modules.settings_window import SettingsWindow
from modules.teacher_workers import GetWorks, CleanWorks, RecreateStudent, DeleteStudent, OpenSFTP

works_folder = 'install -d -m 0755 -o student -g student \"/home/student/Рабочий стол/Сдать работы\"'


class TeacherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.windows = []
        self.hosts = Hosts()

        menu_bar = QMenuBar()
        menu_file = menu_bar.addMenu('Меню')
        action_help = menu_file.addAction('Справка')
        action_set = menu_file.addAction('Настройка')
        action_exit = menu_file.addAction('Выход')

        action_help.triggered.connect(self.help)
        action_set.triggered.connect(self.settings)
        action_exit.triggered.connect(self.close)

        grid = QGridLayout()
        self.setLayout(grid)

        grid.setMenuBar(menu_bar)

        names = [
            'Собрать работы',
            'Удалить работы',
            'Пересоздать student',
            'Удалить student',
            'Открыть проводник',
        ]
        functions = [
            self.get_works,
            self.clean_works,
            self.backup_student,
            self.delete_student,
            self.open_sftp,
        ]

        for i in range(len(names)):
            button = QPushButton(names[i])
            button.clicked.connect(functions[i])
            grid.addWidget(button, i + 1, 0)

        button = QPushButton('Выбрать всё')
        button.clicked.connect(self.select_all)
        grid.addWidget(button, 1, 1)
        button = QPushButton('Очистить выбор')
        button.clicked.connect(self.select_none)
        grid.addWidget(button, 1, 2)

        self.hosts_items = QListWidget()
        self.hosts_items.setSelectionMode(QAbstractItemView.ExtendedSelection)
        font = QFont("Courier")
        font.setPixelSize(16)
        font.setBold(True)
        self.hosts_items.setFont(font)
        hosts_from_file = self.hosts.to_list()
        self.hosts_items.addItems(hosts_from_file)
        grid.addWidget(self.hosts_items, 2, 1, 5, 2)

        self.textfield = QPlainTextEdit()
        self.textfield.cursor = QTextCursor()
        self.textfield.setReadOnly(True)
        self.textfield.setStyleSheet("QPlainTextEdit {background-color: black; color: white;}")
        font = QFont('Courier New')
        font.setBold(True)
        font.setPixelSize(13)
        self.textfield.setFont(font)
        grid.addWidget(self.textfield, 8, 0, 1, 3)

        self.move(300, 150)
        self.setWindowTitle(f'Управление компьютерным кабинетом, версия {version}')
        self.setFixedWidth(600)
        # self.setFixedHeight(300)
        self.setMinimumHeight(300)

        self.show()

        if not hosts_from_file:
            self.help()

        self.thread = UpdateList()
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.progress_signal.connect(self.update_hosts_list)
        self.thread.start()

    # def get_all_items(self):
    #     items = []
    #     for item_index in range(self.hosts_items.count()):
    #         items.append(self.hosts_items.item(item_index))
    #     return items

    def get_selected_items(self):
        selected_items = self.hosts_items.selectedItems()
        items = []
        for item in selected_items:
            items.append(item.text())
        return items

    def get_selected_items_with_confirm(self):
        selected_items = self.hosts_items.selectedItems()
        items = []
        for item in selected_items:
            items.append(item.text())
        if not items:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()
            if button == QMessageBox.Ok:
                return None
        return items

    def update_hosts_list(self, hosts_list: list[QListWidgetItem]):
        self.hosts_items.blockSignals(True)

        current_selected_items = self.get_selected_items()
        self.hosts_items.clear()

        for host in hosts_list:
            self.hosts_items.addItem(host)
            if host.text() in current_selected_items:
                host.setSelected(True)

        self.hosts_items.blockSignals(False)

    def select_all(self):
        self.hosts_items.selectAll()

    def select_none(self):
        self.hosts_items.clearSelection()

    def update_textfield(self, message):
        self.textfield.appendPlainText(message)

    def get_works(self):
        self.textfield.clear()
        comps = self.get_selected_items_with_confirm()
        if comps:
            date = str(datetime.datetime.now().date())
            text, okPressed = QInputDialog.getText(self, "Введите название", "Название папки:", QLineEdit.Normal, "")
            if okPressed and text:
                self.thread = GetWorks()
                self.thread.hosts_list = comps
                self.thread.date = date
                self.thread.text = text

                self.thread.start_signal.connect(self.update_textfield)
                self.thread.progress_signal.connect(self.update_textfield)
                self.thread.finish_signal.connect(self.update_textfield)
                self.thread.finished.connect(self.thread.deleteLater)

                self.thread.start()

            elif okPressed and not text:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Ошибка")
                dlg.setText("Необходимо ввести название")
                button = dlg.exec()
                if button == QMessageBox.Ok:
                    return
            else:
                return

    def clean_works(self):
        self.textfield.clear()
        comps = self.get_selected_items_with_confirm()
        if comps:
            self.thread = CleanWorks()
            self.thread.hosts_list = comps

            self.thread.start_signal.connect(self.update_textfield)
            self.thread.progress_signal.connect(self.update_textfield)
            self.thread.finish_signal.connect(self.update_textfield)
            self.thread.finished.connect(self.thread.deleteLater)

            self.thread.start()

    def backup_student(self):
        self.textfield.clear()
        comps = self.get_selected_items_with_confirm()
        if comps:
            student_pass, okPressed = QInputDialog.getText(
                self, "Определите пароль", "Пароль для student:", QLineEdit.Password, ""
            )
            if okPressed and student_pass:
                self.thread = RecreateStudent()
                self.thread.hosts_list = comps
                self.thread.student_pass = student_pass

                self.thread.start_signal.connect(self.update_textfield)
                self.thread.progress_signal.connect(self.update_textfield)
                self.thread.finish_signal.connect(self.update_textfield)
                self.thread.finished.connect(self.thread.deleteLater)

                self.thread.start()
            elif okPressed and not student_pass:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Ошибка")
                dlg.setText("Необходимо ввести пароль для учётной записи student")
                button = dlg.exec()
                if button == QMessageBox.Ok:
                    return
            else:
                return

    def delete_student(self):
        self.textfield.clear()
        comps = self.get_selected_items_with_confirm()
        if comps:
            self.thread = DeleteStudent()
            self.thread.hosts_list = comps

            self.thread.start_signal.connect(self.update_textfield)
            self.thread.progress_signal.connect(self.update_textfield)
            self.thread.finish_signal.connect(self.update_textfield)
            self.thread.finished.connect(self.thread.deleteLater)

            self.thread.start()

    def open_sftp(self):
        self.textfield.clear()
        comps = self.get_selected_items_with_confirm()
        if comps:
            self.thread = OpenSFTP()
            self.thread.hosts_list = comps

            self.thread.start_signal.connect(self.update_textfield)
            self.thread.progress_signal.connect(self.update_textfield)
            self.thread.finish_signal.connect(self.update_textfield)
            self.thread.finished.connect(self.thread.deleteLater)

            self.thread.start()

    def settings(self):
        logging.info("Открыты настройки")
        new_window = SettingsWindow()
        self.windows.append(new_window)
        new_window.show()

    def help(self):
        logging.info("Открыта справка")
        new_window = HelpWindow()
        self.windows.append(new_window)
        new_window.show()
