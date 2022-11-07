#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QPushButton, QLineEdit, \
                             QListWidget, QAbstractItemView, QMenuBar, \
                             QInputDialog, QProgressBar, QLabel, QMessageBox, QWidget, QGridLayout)

from config import config_path, version
from hosts import Hosts
from system import run_command, user, run_command_in_xterm
from settings_window import SettingsWindow


class TeacherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.windows = []
        self.hosts = Hosts()

        menu_bar = QMenuBar()
        menu_file = menu_bar.addMenu('Меню')
        action_set = menu_file.addAction('Настройка...')
        action_exit = menu_file.addAction('Выход')

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
        self.n = len(self.hosts_items)
        grid.addWidget(self.hosts_items, 2, 1, 5, 2)

        self.move(300, 150)
        self.setWindowTitle(f'Управление компьютерным кабинетом, версия {version}')
        self.setFixedWidth(600)
        self.setFixedHeight(300)

        self.show()

    def enterEvent(self, event):
        if event.type() == 10:
            self.hosts_items.clear()
            self.hosts = Hosts()
            hosts_from_file = self.hosts.to_list()
            self.hosts_items.addItems(hosts_from_file)
            self.n = len(self.hosts_items)

    def select_all(self):
        for i in range(self.n):
            self.hosts_items.item(i).setSelected(True)
        return

    def select_none(self):
        for i in range(self.n):
            self.hosts_items.item(i).setSelected(False)
        return

    def get_works(self):
        comps = self.hosts_items.selectedItems()
        n = len(comps)
        if n == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()

            if button == QMessageBox.Ok:
                return
        date = str(datetime.datetime.now().date())
        text, okPressed = QInputDialog.getText(self, "Введите название", "Название папки:", QLineEdit.Normal, "")
        if okPressed and text:
            self.pbar.setValue(0)
            self.pbar.show()

            for i in range(n):
                comp = comps[i].text().strip()
                print(comp)
                run_command(f'mkdir -p "/home/{user}/Рабочий стол/Работы/"' + date + '/' + text + '/' + comp)

                run_command(f'ssh root@{comp} \'mkdir -p \"/home/student/Рабочий стол/Сдать работы\" && \
                          chmod 777 \"/home/student/Рабочий стол/Сдать работы\"\' && \
                          scp -r root@{comp}:\'/home/student/Рабочий\ стол/Сдать\ работы/*\' \
                          \"/home/{user}/Рабочий стол/Работы/\"{date}/{text}/{comp}')
                self.infoLabel.setText(f'Собираем у {comp}')
                self.pbar.setValue((i + 1) * 100 // n)
            self.infoLabel.setText('Сбор работ завершён.')
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
        comps = self.hosts_items.selectedItems()
        n = len(comps)
        if n == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()

            if button == QMessageBox.Ok:
                return
        self.pbar.setValue(0)
        for i in range(n):
            comp = comps[i].text().strip()
            run_command(f'ssh root@{comp} \'rm -rf /home/student/Рабочий\ стол/Сдать\ работы/*\'')
            self.infoLabel.setText(f'Очищаем {comp}')
            self.pbar.setValue((i + 1) * 100 // n)
        self.infoLabel.setText('Очистка завершена.')

    def delete_student(self):
        comps = self.hosts_items.selectedItems()
        n = len(comps)
        if n == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()
            if button == QMessageBox.Ok:
                return
        self.pbar.setValue(0)
        for i in range(n):
            comp = comps[i].text().strip()
            try:
                self.infoLabel.setText(f'Удаляю student на {comp}...')

                run_command(f'ssh root@{comp} "echo \''
                            f'pkill -u student; '
                            f'userdel -rf student\' | at now"')

            except:
                self.infoLabel.setText(f'Не удалось подключиться к {comp}.')
        self.infoLabel.setText('Команда удаления выполнена на выбранных компьютерах.')

    def backup_student(self):
        comps = self.hosts_items.selectedItems()
        n = len(comps)
        if n == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()
            if button == QMessageBox.Ok:
                return
        self.pbar.setValue(0)
        # TODO: эти методы нужно тестировать в реальных условиях
        # run_command(f'tar -xf /usr/share/teacher_control/student.tar.gz -C {config_path}/')
        for i in range(n):
            comp = comps[i].text().strip()
            try:
                self.infoLabel.setText(f'Пересоздаю student на {comp}...')
                # self.pbar.setValue((i + 1) * 100 // n)
                # run_command(f'scp /usr/share/teacher_control/student.tar.gz root@{comp}:/home/ && '
                #             f'scp {config_path}/share.desktop root@{comp}:/home/ && '
                #             f'ssh root@{comp} "echo \'pkill -u student && sleep 3 &&'
                #             f'cd /home && rm -rf student && '
                #             f'tar xfz student.tar.gz && '
                #             f'mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && '
                #             f'cp share.desktop /home/student/Рабочий\ стол/ && '
                #             f'chown -R student:student student && '
                #             f'rm -f student.tar.gz share.desktop && '
                #             f'reboot\' | at now"')

                run_command(f'ssh root@{comp} "echo \''
                            f'pkill -u student; '
                            f'userdel -rf student; '
                            f'useradd student && '
                            f'chpasswd <<<\"student:1\"\' | at now"')

            except:
                self.infoLabel.setText(f'Не удалось подключиться к {comp}.')
        self.infoLabel.setText('Команда пересоздания выполнена на выбранных компьютерах.')

    def open_sftp(self):
        comps = self.hosts_items.selectedItems()
        n = len(comps)
        if n == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()

            if button == QMessageBox.Ok:
                return
        self.pbar.setValue(0)
        for i in range(n):
            comp = comps[i].text().strip()
            try:
                run_command_in_xterm(f'dolphin sftp://root@{comp}:/home')
                # run_command_in_xterm(f'mc cd sh://root@{comp}:/home')
                self.pbar.setValue((i + 1) * 100 // n)
                self.infoLabel.setText(f'Открываем {comp}...')

            except:
                self.infoLabel.setText(f'Не удалось подключиться к {comp}.')
        self.infoLabel.setText('Открыт Dolphin для всех доступных компьютеров.')


    def settings(self):
        logging.info("Открыты настройки")
        new_window = SettingsWindow()
        self.windows.append(new_window)
        new_window.show()
