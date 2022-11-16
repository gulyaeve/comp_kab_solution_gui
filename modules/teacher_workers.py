import logging

from PyQt5.QtCore import QThread, pyqtSignal

from modules.system import test_ssh, run_command, user, run_command_in_xterm

works_folder = 'install -d -m 0755 -o student -g student \"/home/student/Рабочий стол/Сдать работы\"'


class GetWorks(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.date = None
        self.text = None

    def run(self):
        self.start_signal.emit("Сбор работ начинается")
        for host in self.hosts_list:
            if test_ssh(host):
                check_student = run_command(f"ssh root@{host} file /home/student").strip()
                if check_student.endswith('directory'):
                    run_command(
                        f'mkdir -p "/home/{user}/Рабочий стол/Работы/"' + self.date + '/' + self.text + '/' + host
                    )

                    run_command(
                        f'ssh root@{host} \'{works_folder}\' && '
                        f'scp -r root@{host}:\'/home/student/Рабочий\ стол/Сдать\ работы/*\' '
                        f'\"/home/{user}/Рабочий стол/Работы/\"{self.date}/{self.text}/{host}'
                    )

                    self.progress_signal.emit(f'{host} работы сохранены успешно')
                    logging.info(f'{host} работы сохранены успешно')
                else:
                    self.progress_signal.emit(f'{host} отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host} не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        self.finish_signal.emit("Сбор работ завершился")


class CleanWorks(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None

    def run(self):
        self.start_signal.emit("Очистка директорий для сбора работ начинается")
        for host in self.hosts_list:
            if test_ssh(host):
                check_student = run_command(f"ssh root@{host} file /home/student").strip()
                if check_student.endswith('directory'):
                    run_command(f'ssh root@{host} \'rm -rf /home/student/Рабочий\ стол/Сдать\ работы/*\'')
                    self.progress_signal.emit(f'{host} очистка завершена')
                    logging.info(f'{host} очистка завершена')
                else:
                    self.progress_signal.emit(f'{host} отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host} не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        self.finish_signal.emit("Очистка директорий для сбора работ завершилась")


class RecreateStudent(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.student_pass = None

    def run(self):
        self.start_signal.emit("Пересоздание student начинается")
        for host in self.hosts_list:
            if test_ssh(host):
                check_student = run_command(f"ssh root@{host} file /home/student").strip()
                command = f'echo \'' \
                          f'pkill -u student; ' \
                          f'sleep 2; ' \
                          f'userdel -rf student; ' \
                          f'useradd student && ' \
                          f'chpasswd <<<\"student:{self.student_pass}\" && ' \
                          f'{works_folder}\'| at now'
                if check_student.endswith('directory'):
                    run_command(f'ssh root@{host} \'{command}\'')
                    self.progress_signal.emit(f'{host} student удален и создан заново')
                    logging.info(f'{host} student удален и создан заново')
                else:
                    run_command(f'ssh root@{host} \'{command}\'')
                    self.progress_signal.emit(f'{host} student создан')
                    logging.info(f'{host} student создан')
            else:
                self.progress_signal.emit(f'{host} не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        self.finish_signal.emit("Пересоздание student завершено")


class DeleteStudent(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.student_pass = None

    def run(self):
        self.start_signal.emit("Удаление student начинается")
        for host in self.hosts_list:
            if test_ssh(host):
                check_student = run_command(f"ssh root@{host} file /home/student").strip()
                if check_student.endswith('directory'):
                    command = f'echo \'pkill -u student; sleep 2; userdel -rf student\' | at now'
                    run_command(f'ssh root@{host} \'{command}\'')
                    self.progress_signal.emit(f'{host} student удален')
                    logging.info(f'{host} student удален')
                else:
                    self.progress_signal.emit(f'{host} отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host} не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        self.finish_signal.emit("Удаление student завершено")


class OpenSFTP(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None

    def run(self):
        self.start_signal.emit("Открываем директории")
        for host in self.hosts_list:
            if test_ssh(host):
                run_command_in_xterm(f'nohup kde5 dolphin sftp://root@{host}:/home')
                # run_command_in_xterm(f'mc cd sh://root@{comp}:/home')
                self.progress_signal.emit(f'{host} открыт sftp')
                logging.info(f'{host} открыт sftp')
            else:
                self.progress_signal.emit(f'{host} не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        self.finish_signal.emit("Директории открыты")
