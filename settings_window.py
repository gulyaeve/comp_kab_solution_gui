import sys

from PyQt5.QtWidgets import QWidget, QGridLayout


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle('Настройки компьютерного класса')
        self.setFixedWidth(300)
        self.setFixedHeight(150)
        # self.show()


# def settings():
#     print('Settings')
#     stngs = SettingsWindow()
    # stngs.show()

