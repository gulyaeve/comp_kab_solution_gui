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
    logging.info(f"[{command}]>{ret.stdout.decode()}")
    return ret.stdout.decode()


def run_command_in_xterm(command: str):
    run_command(f'xterm -e "{command}"')
    # run_command(f'xterm -hold -e "{command}"')


def run_command_by_root(command: str):
    run_command(f'xterm -e \'echo "Введите пароль суперпользователя" && su - root -c "{command}"\'')
    # run_command(f'xterm -hold -e \'echo "Введите пароль суперпользователя" && su - root -c "{command}"\'')


# Получение имени компьютера и текущего пользователя
this_host = run_command('hostname').strip()
user = run_command('whoami').strip()
