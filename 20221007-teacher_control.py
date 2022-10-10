#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import (QWidget, QGridLayout,
    QPushButton, QApplication, QTextEdit, QLineEdit, \
    QListWidget, QAbstractItemView, QMenu, QMenuBar, \
                             QToolBar, QMainWindow)



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
    
    def initUI(self):
   
        menu_bar = QMenuBar()
        menu_file = menu_bar.addMenu('Меню')
        action_set = menu_file.addAction('Настройка...')
        action_exit = menu_file.addAction('Выход')
        action_exit.triggered.connect(self.close)

        grid = QGridLayout()
        self.setLayout(grid)
        
        grid.setMenuBar(menu_bar)

        names = ['Собрать работы', 'Очистить работы', 'Восстановить', 'Открыть Veyon', 'Открыть sftp', 'Команда']

        positions = [(i,0) for i in range(6)]

        for position, name in zip(positions, names):

            button = QPushButton(name)
            grid.addWidget(button, position[0], 0)
        
        button = QPushButton('Выбрать всё')
        button.clicked.connect(self.selectAll)
        grid.addWidget(button, 0, 1)
        button = QPushButton('Очистить выбор')
        button.clicked.connect(self.selectNone)
        grid.addWidget(button, 0, 2)


        self.hosts = QListWidget()
        self.hosts.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.hosts.addItems(['comp1', 'comp2', 'comp3', 'comp4', 'comp5'])
        self.n = len(self.hosts)
        grid.addWidget(self.hosts, 1, 1, 5, 2)        

        self.move(300, 150)
        self.setWindowTitle('Teacher Control ver. 1.0')
        self.setFixedWidth(600)
        self.show()
        



if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())