import logging
import subprocess

import paramiko
from PyQt5.QtWidgets import QWidget
from paramiko.ssh_exception import AuthenticationException


def run_command(command: str) -> str:
    """
    Выполнение команды и сохранение вывода в лог
    :param command: команда shell
    :return: результат работы команды
    """
    ret = subprocess.run(command, capture_output=True, shell=True)
    logging.info(f"[{command}]>{ret.stdout.decode()}")
    print(f"[{command}]>{ret.stdout.decode()}")
    return ret.stdout.decode()


def run_command_in_xterm(command: str):
    """
    Выполнение команды в xterm
    :param command: команда для выполнения
    """
    run_command(f'xterm -e "{command}"')


def run_command_in_konsole(command: str):
    """
    Выполнение команды в новом окне терминала
    :param command: команда для выполнения
    """
    run_command(f'konsole -e "{command}"')


def run_command_by_root(command: str):
    """
    Выполнение команды с правами root в xterm
    :param command: команда для выполнения
    """
    run_command(f'xterm -e \'echo "Введите пароль суперпользователя" && su - root -c "{command}"\'')


def get_mac_address(hostname):
    """
    Получение мак-адреса удаленного хоста
    :param hostname: адрес хоста
    :return: мак-адрес хоста
    """
    get_nmcli = run_command(
        f'ssh root@{hostname} nmcli c show | grep \"Проводное соединение 1\"'
    )
    if get_nmcli:
        device_name = get_nmcli.split()[-1]
        if device_name and device_name != "--":
            hwaddr = run_command(
                f'ssh root@{hostname} nmcli dev show {device_name} | grep \"GENERAL.HWADDR\"'
            ).split()[-1]
            logging.info(f"Получен мак-адрес {hwaddr} для {hostname}")
            return hwaddr
    return ""


def test_ssh(host) -> bool:
    """
    Проверка ssh для пользователя root на удаленном хосте
    :param host: адрес хоста
    :return: bool, в зависимости от подключения
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_system_host_keys()
    try:
        ssh.connect(hostname=host, port=22, timeout=1, username='root')
        return True
    except Exception as e:
        logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}: {e}")
        return False
    finally:
        ssh.close()


def test_ping(host) -> bool:
    """
    Проверка подключения к удаленному хосту
    :param host: адрес хоста
    :return: bool, в зависимости от подключения
    """
    result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
    if result.returncode == 0:
        logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
        return True
    elif result.returncode == 2:
        logging.info(f"ping: {host}: {result=} {result.returncode=}")
        return False
    else:
        logging.info(host + f" неизвестная ошибка {result=} {result.returncode=}")
        return False


def check_student_on_host(host: str) -> bool:
    """
    Проверка наличия директории пользователя student на удаленном хосте
    :param host: адрес хоста
    :return: bool в зависимости от наличия
    """
    check = run_command(f"ssh root@{host} file /home/student").strip()
    return True if check.endswith('directory') else False


# Получение имени компьютера и текущего пользователя
this_host = run_command('hostname').strip()
user = run_command('whoami').strip()


class CompKabSolutionWindow(QWidget):
    pass
