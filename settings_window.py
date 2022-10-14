import sys

from PyQt5.QtWidgets import QWidget, QGridLayout


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle('Настройки компьютерного класса')
        self.show()


def settings():
    print('Settings')
    stngs = SettingsWindow()
    stngs.show()

