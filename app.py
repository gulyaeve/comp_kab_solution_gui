import logging
import sys

from PyQt5.QtWidgets import QApplication

from system import this_host, user, run_command
from teacher_control import TeacherWindow


# Создание папки с конфигом
run_command(f'mkdir -p /home/{user}/.teacher_control')
run_command(f'touch /home/{user}/.teacher_control/hosts.txt')

# Настройка логирования
logging.basicConfig(filename=f'/home/{user}/.teacher_control/log.txt',
                    format=u'%(asctime)s %(filename)s [LINE:%(lineno)d] [%(funcName)s()] #%(levelname)-15s %(message)s',
                    level=logging.INFO,
                    )


if __name__ == '__main__':
    logging.info(f'Приложение запущено: {this_host=} {user=}')
    app = QApplication(sys.argv)
    ex = TeacherWindow()
    logging.info('Приложение завершило работу')
    sys.exit(app.exec_())
