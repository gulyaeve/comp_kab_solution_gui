from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel

from config import version

help_body = f"""<b>Инструменты организации работы в компьютерном классе</b>
<br>
<br>
Данное решение позволяет:
<dl>
  <dt>ИТ-специалисту:</dt>
  <dd>- Настроить SSH для пользователя root</dd>
  <dd>- Настроить сетевую папку sftp для выдачи задания учителем</dd>
  <dd>- Установить и настроить приложение veyon для управления и наблюдением за компьютерами учеников</dd>
  <dt>Учителю:</dt>
  <dd>- Удалённо собирать работы с компьютеров учеников</dd>
  <dd>- Очищать папки для сбора работ</dd>
  <dd>- Создавать и удалять локальную учётную запись student на компьютерах учеников</dd>
  <dd>- Открывать в проводнике содержимое компьютера ученика для просмотра и редактирования</dd>
</dl>
Для работы данного решения необходимо выполнить рекомендации по первоначальной настройке:
<ul>
  <li>Создать локальную учётную запись пользователя teacher на компьютерах учеников</li>
  <li>Переименовать компьютеры учеников, согласно 
  <a href="https://os.mos.ru/git/MOS/doc-standart/src/master/hostname-rules.md">рекомендациям</a></li>
  <li>Компьютеры учителя и учеников должны быть объединены в одну локальную сеть, находиться в одной подсети 
  (рекомендуется использовать проводное LAN соединение для работы всех функций)</li>
  <li>Внести имена компьютеров в окне настройки (Меню - Настройка) и выполнить все пункты настройки</li>
</ul>
<br>
Перед началом работы ознакомьтесь с документацией по ИТ-решению «Инструменты организации работы в компьютерном классе», 
по ссылке:  
<a href = "https://link.educom.ru/solutions/8/show">Страница решения</a>.
<br>
<br>
[Версия {version}] Разработано 
<a href="http://digitalcenter.moscow/">ГАУ «Центр цифровизации образования»</a>
"""


class HelpWindow(QWidget):
    def __init__(self):
        super().__init__()

        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle(f'Справка по настройке компьютерного кабинета')
        self.setFixedWidth(700)

        help_text = QLabel()
        help_text.setText(help_body)
        help_text.setOpenExternalLinks(True)
        help_text.setTextFormat(Qt.RichText)
        # help_text.setAlignment(Qt.AlignCenter)
        help_text.setWordWrap(True)

        grid.addWidget(help_text, 0, 0)

