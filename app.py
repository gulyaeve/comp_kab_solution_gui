import logging
import os
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

from modules.config import hosts_file_path, config_path, icon_file, style
from modules.system import this_host, user, run_command
from modules.teacher_control import TeacherWindow

# Директория приложения
basedir = os.path.dirname(__file__)

if user == 'root':
    # Выход для root
    logging.info("Запуск от root, выход из приложения")
    print("Данное приложение не работает с пользователем root")
    sys.exit(0)

# Создание папки с конфигом
run_command(f'mkdir -p {config_path}')

# Создание файла для хранения
run_command(f'touch {hosts_file_path}')

# Настройка логирования
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    filename=f"{config_path}/log.txt",
    format=u'%(asctime)s %(filename)s [LINE:%(lineno)d] [%(funcName)s()] #%(levelname)-15s %(message)s',
    level=logging.INFO,
)


if __name__ == '__main__':
    # Запуск приложения
    logging.info(f'Приложение запущено: {this_host=} {user=}')
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, icon_file)))
    app.setStyleSheet(open(os.path.join(basedir, style), 'r').read())
    ex = QWidget()
    try:
        ex = TeacherWindow(app)
        app.exec_()
    except Exception as e:
        error_box = QMessageBox.warning(ex, "Ошибка", f"{e}")
        logging.info(f"Root exception: {e}")
