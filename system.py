import logging
import subprocess
import sys


def exit_app():
    """
    Выход из приложения
    """
    logging.info("Выход из программы")
    print('Выход из программы...')
    sys.exit(0)


def run_command(command: str) -> str:
    """
    Выполнение команды и сохранение вывода в лог
    :param command: команда shell
    :return: результат работы команды
    """
    ret = subprocess.run(command, capture_output=True, shell=True)
    print(ret.stdout.decode())
    logging.info(ret.stdout.decode())
    return ret.stdout.decode()


# Получение имени компьютера и текущего пользователя
this_host = subprocess.run(['hostname'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0]
user = subprocess.run(['whoami'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0]
