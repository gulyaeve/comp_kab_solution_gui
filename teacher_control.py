#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QPushButton, QLineEdit, \
                             QListWidget, QAbstractItemView, QMenuBar, \
                             QInputDialog, QProgressBar, QLabel, QMessageBox, QWidget, QGridLayout)

from system import run_command
from settings_window import SettingsWindow


class TeacherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.windows = []
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

        names = ['Собрать работы', 'Очистить работы', 'Восстановить', 'Открыть Veyon', 'Открыть sftp', 'Команда']
        functions = [self.get_works, self.clean_works, self.backup_student, self.open_veyon, self.open_sftp,
                     self.run_command]

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

        self.hosts = QListWidget()
        self.hosts.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # hosts_from_file = open('~/.teacher_control/hosts.txt', 'r').readlines()
        hosts_from_file = ['sm2222-3-313-2.local', 'sm2222-3-313-3.local']
        self.hosts.addItems(hosts_from_file)
        self.n = len(self.hosts)
        grid.addWidget(self.hosts, 2, 1, 5, 2)

        self.move(300, 150)
        self.setWindowTitle('Teacher Control ver. 1.0')
        self.setFixedWidth(600)
        self.show()

    def select_all(self):
        for i in range(self.n):
            self.hosts.item(i).setSelected(True)
        return

    def select_none(self):
        for i in range(self.n):
            self.hosts.item(i).setSelected(False)
        return

    def get_works(self):
        comps = self.hosts.selectedItems()
        n = len(comps)
        if n == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()

            if button == QMessageBox.Ok:
                return
        date = str(datetime.datetime.now().date())
        text = ''
        while text == '':
            text, okPressed = QInputDialog.getText(self, "Введите название", "Название папки:", QLineEdit.Normal, "")

        self.pbar.setValue(0)
        self.pbar.show()

        for i in range(n):
            comp = comps[i].text().strip()
            run_command('mkdir -p "/home/teacher/Рабочий стол/Работы/"' + date + '/' + text + '/' + comp)

            run_command(f'ssh root@{comp} \'mkdir -p \"/home/student/Рабочий стол/Сдать работы\" && \
                      chmod 777 \"/home/student/Рабочий стол/Сдать работы\"\' && \
                      scp -r root@{comp}:\'/home/student/Рабочий\ стол/Сдать\ работы/*\' \
                      \"/home/teacher/Рабочий стол/Работы/\"{date}/{text}/{comp}')

            """
            subprocess.Popen(['ssh', f'root@{comps[i].text().strip()}', 'mkdir -p \"/home/student/Рабочий стол/Сдать работы\" && chmod 777 \"/home/student/Рабочий стол/Сдать работы\"'])
            subprocess.Popen(['scp', '-r', f"root@{comps[i].text().strip()}:\'/home/student/Рабочий стол/Сдать работы/*\'", '"/home/teacher/Рабочий стол/Работы/"' + date + '/' + text + '/' + comps[i].text().strip()])
            """
            self.pbar.setValue((i + 1) * 100 // n)
            self.infoLabel.setText(f'Собираем у {comp}')
        self.infoLabel.setText('Сбор работ завершён.')

    def clean_works(self):
        comps = self.hosts.selectedItems()
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
            self.pbar.setValue((i + 1) * 100 // n)
            self.infoLabel.setText(f'Очищаем {comp}')
        self.infoLabel.setText('Очистка завершена.')

    def backup_student(self):
        comps = self.hosts.selectedItems()
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
                run_command(f'ssh root@{comp} "pkill -u student"')
                self.infoLabel.setText(f'Восстанавливаем {comp}...')
                self.pbar.setValue((i + 1) * 100 // n)
                run_command(f'rsync -avz --delete /home/teacher/ root@{comp}:/home/student/')
            except:
                self.infoLabel.setText(f'Не удалось подключиться к {comp}.')
        self.infoLabel.setText('Команда восстановления выполнена на выбранных компьютерах.')

    def open_veyon(self):
        pass

    def open_sftp(self):
        comps = self.hosts.selectedItems()
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
                run_command(f'dolphin sftp://student@{comp}')
                self.infoLabel.setText(f'Открываем {comp}...')
                self.pbar.setValue((i + 1) * 100 // n)
            except:
                self.infoLabel.setText(f'Не удалось подключиться к {comp}.')
        self.infoLabel.setText('Открыт Dolphin для всех доступных компьютеров.')

    def run_command(self):
        comps = self.hosts.selectedItems()
        n = len(comps)
        if n == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Ошибка")
            dlg.setText("Выберите хотя бы один компьютер из списка")
            button = dlg.exec()

            if button == QMessageBox.Ok:
                return
        dialog, pressed = QInputDialog.getText(self, 'Команда',
                                               'Введите команду для выполнения на компьютерах учеников',
                                               QLineEdit.Normal)
        for i in range(n):
            comp = comps[i].text().strip()
            run_command(f'ssh root@{comp} "{dialog}"')

    def settings(self):
        print('Settings')
        new_window = SettingsWindow()
        self.windows.append(new_window)
        new_window.show()
