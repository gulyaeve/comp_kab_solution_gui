import logging
import os
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from modules.config import hosts_file_path, config_path
from modules.system import this_host, user, run_command, exit_app
from modules.teacher_control import TeacherWindow

if user == 'root':
    sys.exit(exit_app())

# Создание папки с конфигом
run_command(f'mkdir -p {config_path}')
run_command(f'touch {hosts_file_path}')
basedir = os.path.dirname(__file__)

# Настройка логирования
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    filename=f"{config_path}/log.txt",
    # filename="log.txt",
    format=u'%(asctime)s %(filename)s [LINE:%(lineno)d] [%(funcName)s()] #%(levelname)-15s %(message)s',
    level=logging.INFO,
)


if __name__ == '__main__':
    logging.info(f'Приложение запущено: {this_host=} {user=}')
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, 'teacher_control.svg')))
    app.setStyleSheet(open("style.css").read())
    ex = TeacherWindow()
    logging.info('Приложение завершило работу')
    sys.exit(app.exec_())
