#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QPushButton, QLineEdit, \
                             QListWidget, QAbstractItemView, QMenuBar, \
                             QInputDialog, QProgressBar, QLabel, QMessageBox, QWidget, QGridLayout, QListWidgetItem)

from modules.command_worker import SSHCommandExec
from modules.config import version
from modules.help import HelpWindow
from modules.hosts import Hosts
from modules.ping_ssh_worker import PingSSH
from modules.system import run_command, user, run_command_in_xterm
from modules.settings_window import SettingsWindow


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

        self.infoLabel = QLabel('')
        self.infoLabel.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.infoLabel, 0, 0, 1, 3)

        self.pbar = QProgressBar(self)
        self.pbar.setGeometry(200, 10, 200, 20)

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
        hosts_from_file = self.hosts.to_list()
        self.hosts_items.addItems(hosts_from_file)
        grid.addWidget(self.hosts_items, 2, 1, 5, 2)

        self.move(300, 150)
        self.setWindowTitle(f'Управление компьютерным кабинетом, версия {version}')
        self.setFixedWidth(600)
        self.setFixedHeight(300)

        self.show()

        if not hosts_from_file:
            self.help()

        self.thread = PingSSH()
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

    def get_works(self):
        comps = self.get_selected_items_with_confirm()
        if comps:
            date = str(datetime.datetime.now().date())
            text, okPressed = QInputDialog.getText(self, "Введите название", "Название папки:", QLineEdit.Normal, "")
            if okPressed and text:
                self.pbar.setValue(0)
                self.pbar.show()
                for i, comp in enumerate(comps):
                    check_student = run_command(f"ssh root@{comp} file /home/student").strip()
                    if check_student.endswith('directory'):
                        run_command(f'mkdir -p "/home/{user}/Рабочий стол/Работы/"' + date + '/' + text + '/' + comp)

                        run_command(f'ssh root@{comp} \'{works_folder}\' && \
                                    scp -r root@{comp}:\'/home/student/Рабочий\ стол/Сдать\ работы/*\' \
                                    \"/home/{user}/Рабочий стол/Работы/\"{date}/{text}/{comp}')
                        self.infoLabel.setText(f'Собираем у {comp}')
                    else:
                        self.infoLabel.setText(f'Нет student на {comp}')
                    self.pbar.setValue((i + 1) * 100 // len(comps))
                # self.infoLabel.setText('Сбор работ завершён.')
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
        comps = self.get_selected_items_with_confirm()
        if comps:
            self.pbar.setValue(0)
            for i, comp in enumerate(comps):
                check_student = run_command(f"ssh root@{comp} file /home/student").strip()
                if check_student.endswith('directory'):
                    run_command(f'ssh root@{comp} \'rm -rf /home/student/Рабочий\ стол/Сдать\ работы/*\'')
                    self.infoLabel.setText(f'Очищаем {comp}')
                else:
                    self.infoLabel.setText(f'Нет student на {comp}')
                self.pbar.setValue((i + 1) * 100 // len(comps))
            self.infoLabel.setText('Очистка завершена.')

    def delete_student(self):
        comps = self.get_selected_items_with_confirm()
        if comps:
            self.pbar.setValue(0)
            for i, comp in enumerate(comps):
                check_student = run_command(f"ssh root@{comp} file /home/student").strip()
                if check_student.endswith('directory'):
                    self.infoLabel.setText(f'Удаляю student на {comp}...')
                    command = f'echo \'pkill -u student; sleep 2; userdel -rf student\' | at now'
                    self.thread = SSHCommandExec()
                    self.thread.hosts_list = [comp]
                    self.thread.command = command

                    # self.thread.progress_signal.connect(self.update_textfield)
                    self.thread.finished.connect(self.thread.deleteLater)
                    self.thread.start()

                    self.thread.finished.connect(
                        lambda: self.infoLabel.setText(f'Команда удаления student отправлена на {comp}.')
                    )
                else:
                    self.infoLabel.setText(f'Нет student на {comp}')

                self.pbar.setValue((i + 1) * 100 // len(comps))

    def backup_student(self):
        comps = self.get_selected_items_with_confirm()
        if comps:
            self.pbar.setValue(0)
            student_pass, okPressed = QInputDialog.getText(
                self, "Определите пароль", "Пароль для student:", QLineEdit.Normal, ""
            )
            if okPressed and student_pass:
                for i, comp in enumerate(comps):
                    self.infoLabel.setText(f'Пересоздаю student на {comp}...')
                    command = f'echo \'' \
                              f'pkill -u student; ' \
                              f'sleep 2; ' \
                              f'userdel -rf student; ' \
                              f'useradd student && ' \
                              f'chpasswd <<<\"student:{student_pass}\" && ' \
                              f'{works_folder}\'| at now'
                    self.thread = SSHCommandExec()
                    self.thread.hosts_list = [comp]
                    self.thread.command = command

                    # self.thread.progress_signal.connect(self.update_textfield)
                    self.thread.finished.connect(self.thread.deleteLater)
                    self.thread.start()

                    self.thread.finished.connect(
                        lambda: self.infoLabel.setText(f'Команда пересоздания student отправлена на {comp}.')
                    )

                    self.pbar.setValue((i + 1) * 100 // len(comps))

    def open_sftp(self):
        comps = self.get_selected_items_with_confirm()
        if comps:
            if len(comps) != 1:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Ошибка")
                dlg.setText("Выберите один компьютер из списка")
                button = dlg.exec()
                if button == QMessageBox.Ok:
                    return

            self.pbar.setValue(0)
            for i, comp in enumerate(comps):
                try:
                    run_command_in_xterm(f'kde5 dolphin sftp://root@{comp}:/home')
                    # run_command_in_xterm(f'mc cd sh://root@{comp}:/home')
                    self.pbar.setValue((i + 1) * 100 // len(comps))
                    self.infoLabel.setText(f'Открываем {comp}...')
                except:
                    self.infoLabel.setText(f'Не удалось подключиться к {comp}.')
                finally:
                    self.pbar.setValue((i + 1) * 100 // len(comps))

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
