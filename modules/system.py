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
    run_command(f'xterm -e "{command}"')


# def run_command_in_xterm_hold(command: str):
#     run_command(f'xterm -hold -e "{command}"')


def run_command_by_root(command: str):
    run_command(f'xterm -e \'echo "Введите пароль суперпользователя" && su - root -c "{command}"\'')


def get_mac_address(hostname):
    ip_address = run_command(f"ping {hostname} -c1").split('(')[1].split(')')[0]
    ifconfig_output = run_command(f'ssh root@{hostname} "ifconfig"')
    mac_address = ''
    for s in ifconfig_output.split('\n'):
        if s.startswith('e'):
            mac_address = s.split('HWaddr ')[1].rstrip()
        if s.strip() == '':
            logging.info(f'Компьютер {hostname} не подключён к проводной сети')
            return ''
        if ip_address in s:
            return mac_address
    return mac_address


def test_ssh(host) -> bool:
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
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_system_host_keys()
    try:
        ssh.connect(hostname=host, port=22, timeout=1, username='root')
        return True
    except AuthenticationException as e:
        logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}: {e}")
        return True
    except Exception as e:
        logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}: {e}")
        return False
    finally:
        ssh.close()


def check_student_on_host(host: str) -> bool:
    check = run_command(f"ssh root@{host} file /home/student").strip()
    return True if check.endswith('directory') else False


# Получение имени компьютера и текущего пользователя
this_host = run_command('hostname').strip()
user = run_command('whoami').strip()


class CompKabSolutionWindow(QWidget):
    pass
