import logging
import time

from PyQt5.QtCore import QThread, pyqtSignal

from modules.hosts import Hosts
from modules.system import test_ssh, run_command, user, run_command_in_xterm, check_student_on_host

works_folder = 'install -d -m 0755 -o student -g student \\"/home/student/Рабочий стол/Сдать работы\\"'


class UpdateList(QThread):
    progress_signal = pyqtSignal(list)
    hosts = None

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.continue_run = True

    def run(self):
        while self.continue_run:
            hosts = Hosts()
            if self.hosts.to_list() != hosts.to_list():
                self.progress_signal.emit(hosts.to_list())
                self.hosts = Hosts()
            time.sleep(1)

    def isFinished(self):
        self.continue_run = False


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
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nСбор работ начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    run_command(
                        f'mkdir -p "/home/{user}/Рабочий стол/Работы/"' + self.date + '/' + self.text + '/' + host
                    )

                    run_command(
                        f'ssh root@{host} \'{works_folder}\' && '
                        f'scp -r root@{host}:\'/home/student/Рабочий\ стол/Сдать\ работы/*\' '
                        f'\"/home/{user}/Рабочий стол/Работы/\"{self.date}/{self.text}/{host}'
                    )

                    self.progress_signal.emit(f'{host}: работы сохранены успешно')
                    logging.info(f'{host} работы сохранены успешно')
                    success_count += 1
                else:
                    self.progress_signal.emit(f'{host}: отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nСбор работ не выполнен.")
        else:
            self.finish_signal.emit(
                f"\nСбор работ завершился.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class CleanWorks(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nОчистка директорий для сбора работ начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    run_command(f'ssh root@{host} \'rm -rf /home/student/Рабочий\ стол/Сдать\ работы/*\'')
                    self.progress_signal.emit(f'{host}: очистка завершена')
                    logging.info(f'{host} очистка завершена')
                    success_count += 1
                else:
                    self.progress_signal.emit(f'{host}: отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nОчистка директорий для сбора работ не выполнена.")
        else:
            self.finish_signal.emit(
                f"\nОчистка директорий для сбора работ завершилась.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class RecreateStudent(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.student_pass = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nПересоздание student начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                command = f'echo \'' \
                          f'pkill -u student; ' \
                          f'sleep 2; ' \
                          f'userdel -rf student; ' \
                          f'useradd student && ' \
                          f'chpasswd <<<\'student:{self.student_pass}\' && ' \
                          f'{works_folder}\'| at now'
                if check_student_on_host(host):
                    run_command(f'ssh root@{host} \"{command}\"')
                    self.progress_signal.emit(f'{host}: student удален и создан заново')
                    logging.info(f'{host} student удален и создан заново')
                    success_count += 1
                else:
                    run_command(f'ssh root@{host} \"{command}\"')
                    self.progress_signal.emit(f'{host}: student создан')
                    logging.info(f'{host} student создан')
                    success_count += 1
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nПересоздание student не выполнено.")
        else:
            self.finish_signal.emit(
                f"\nПересоздание student завершилось.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class DeleteStudent(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None
        self.student_pass = None

    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nУдаление student начинается\n"
        )
        for host in self.hosts_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    command = f'echo \'pkill -u student; sleep 2; userdel -rf student\' | at now'
                    run_command(f'ssh root@{host} \"{command}\"')
                    self.progress_signal.emit(f'{host}: student удален')
                    logging.info(f'{host} student удален')
                    success_count += 1
                else:
                    self.progress_signal.emit(f'{host}: отсутствует student')
                    logging.info(f'{host} отсутствует student')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        if success_count == 0:
            self.finish_signal.emit(f"\nУдаление student не выполнено.")
        else:
            self.finish_signal.emit(
                f"\nУдаление student завершилось.\n"
                f"Было выбрано: {hosts_count}\n"
                f"Завершено успешно: {success_count}\n"
                f"Ошибок: {hosts_count - success_count}"
            )


class OpenSFTP(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.hosts_list = None

    # def run(self):
    #     hosts_count = len(self.hosts_list)
    #     success_count = 0
    #     self.start_signal.emit(
    #         f"Выбрано компьютеров: {hosts_count}\nДиректории открываются\n"
    #     )
    #     sftp_adresses = ["kde5 dolphin --new-window"]
    #     for host in self.hosts_list:
    #         if test_ssh(host):
    #             # sftp_adresses.append(f'"sftp://root@{host}:/home/"')
    #             sftp_adresses.append(f'fish://root@{host}:/home')
    #             # run_command_in_xterm(f'mc cd sh://root@{comp}:/home')
    #             self.progress_signal.emit(f'{host}: открыт проводник')
    #             logging.info(f'{host} открыт sftp')
    #             success_count += 1
    #         else:
    #             self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
    #             logging.info(f'{host} не в сети или не настроен ssh')
    #     command = " ".join(sftp_adresses)
    #     if success_count == 0:
    #         self.finish_signal.emit(f"\nОткрытие директорий не выполнено.")
    #     else:
    #         self.finish_signal.emit(
    #             f"\nОткрытие директорий завершилось.\n"
    #             f"Было выбрано: {hosts_count}\n"
    #             f"Завершено успешно: {success_count}\n"
    #             f"Ошибок: {hosts_count - success_count}"
    #         )
    #         run_command_in_xterm(command)
    def run(self):
        hosts_count = len(self.hosts_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nДиректории открываются\n"
        )
        # sftp_adresses = ["xdg-open"]
        for host in self.hosts_list:
            if test_ssh(host):
                # sftp_adresses.append(f'"sftp://root@{host}:/home/"')
                # sftp_adresses.append(f'sftp://root@{host}:/home/')
                self.progress_signal.emit(f'{host}: открыт проводник')
                logging.info(f'{host} открыт sftp')
                success_count += 1
                run_command_in_xterm(f'mc $HOME/Рабочий\ стол sh://root@{host}:/home')
                # run_command_in_xterm(f'dolphin --new-window sftp://root@{host}:/home')
            else:
                self.progress_signal.emit(f'{host}: не в сети или не настроен ssh')
                logging.info(f'{host} не в сети или не настроен ssh')
        # command = " ".join(sftp_adresses)
        if success_count == 0:
            self.finish_signal.emit(f"\nОткрытие директорий не выполнено.")
        else:
            self.finish_signal.emit(
                f"\nОткрытие директорий завершилось.\n"
                # f"Было выбрано: {hosts_count}\n"
                # f"Завершено успешно: {success_count}\n"
                # f"Ошибок: {hosts_count - success_count}"
            )
            # run_command_in_xterm(command)
