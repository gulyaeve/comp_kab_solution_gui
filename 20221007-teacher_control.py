#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, os, datetime, subprocess
from PyQt5.QtWidgets import (QWidget, QGridLayout,
                             QPushButton, QApplication, QTextEdit, QLineEdit, \
                             QListWidget, QAbstractItemView, QMenu, QMenuBar, \
                             QToolBar, QMainWindow, QInputDialog, QProgressBar, QLabel, QMessageBox)
from PyQt5.QtCore import Qt


class Example(QWidget):

    def __init__(self):
        super().__init__()

        self.initUI()

    def selectAll(self):
        for i in range(self.n):
            self.hosts.item(i).setSelected(True)
        return

    def selectNone(self):
        for i in range(self.n):
            self.hosts.item(i).setSelected(False)
        return

    def getWorks(self):
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
        self.pbar = QProgressBar(self)
        self.pbar.setGeometry(200, 10, 200, 20)
        self.pbar.setValue(0)
        self.pbar.show()

        for i in range(n):
            # print(comps[i].text())
            comp = comps[i].text().strip()
            os.system('mkdir -p "/home/teacher/Рабочий стол/Работы/"' + date + '/' + text + '/' + comp)

            os.system(f'ssh root@{comp} \'mkdir -p \"/home/student/Рабочий стол/Сдать работы\" && \
                      chmod 777 \"/home/student/Рабочий стол/Сдать работы\"\' && \
                      scp -r root@{comp}:\'/home/student/Рабочий\ стол/Сдать\ работы/*\' \
                      \"/home/teacher/Рабочий стол/Работы/\"{date}/{text}/{comp}')

            """
            subprocess.Popen(['ssh', f'root@{comps[i].text().strip()}', 'mkdir -p \"/home/student/Рабочий стол/Сдать работы\" && chmod 777 \"/home/student/Рабочий стол/Сдать работы\"'])
            subprocess.Popen(['scp', '-r', f"root@{comps[i].text().strip()}:\'/home/student/Рабочий стол/Сдать работы/*\'", '"/home/teacher/Рабочий стол/Работы/"' + date + '/' + text + '/' + comps[i].text().strip()])
            """
            self.pbar.setValue((i + 1) * 100 // n)
            self.infoLabel.setText('Собираем у ' + comps[i].text().strip())
        self.infoLabel.setText('Сбор работ завершён.')
        return

    def cleanWorks(self):
        pass

    def backupStudent(self):
        pass

    def openVeyon(self):
        pass

    def openSftp(self):
        pass

    def runCommand(self):
        pass

    def initUI(self):

        menu_bar = QMenuBar()
        menu_file = menu_bar.addMenu('Меню')
        action_set = menu_file.addAction('Настройка...')
        action_exit = menu_file.addAction('Выход')
        action_exit.triggered.connect(self.close)

        grid = QGridLayout()
        self.setLayout(grid)

        grid.setMenuBar(menu_bar)

        self.infoLabel = QLabel('')
        self.infoLabel.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.infoLabel, 0, 1)

        names = ['Собрать работы', 'Очистить работы', 'Восстановить', 'Открыть Veyon', 'Открыть sftp', 'Команда']
        functions = [self.getWorks, self.cleanWorks, self.backupStudent, self.openVeyon, self.openSftp, self.runCommand]

        for i in range(len(names)):
            button = QPushButton(names[i])
            button.clicked.connect(functions[i])
            grid.addWidget(button, i + 1, 0)

        button = QPushButton('Выбрать всё')
        button.clicked.connect(self.selectAll)
        grid.addWidget(button, 1, 1)
        button = QPushButton('Очистить выбор')
        button.clicked.connect(self.selectNone)
        grid.addWidget(button, 1, 2)

        self.hosts = QListWidget()
        self.hosts.setSelectionMode(QAbstractItemView.ExtendedSelection)
        hosts_from_file = open('/home/teacher/teacher_control/hosts.txt', 'r').readlines()
        self.hosts.addItems(hosts_from_file)
        self.n = len(self.hosts)
        grid.addWidget(self.hosts, 2, 1, 5, 2)

        self.move(300, 150)
        self.setWindowTitle('Teacher Control ver. 1.0')
        self.setFixedWidth(600)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
