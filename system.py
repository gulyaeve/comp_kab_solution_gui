import logging
import subprocess
import sys

import paramiko
from paramiko.ssh_exception import AuthenticationException


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


def run_command_in_xterm_hold(command: str):
    run_command(f'xterm -hold -e "{command}"')
    # run_command(f'xterm -hold -e "{command}"')


def run_command_by_root(command: str):
    run_command(f'xterm -e \'echo "Введите пароль суперпользователя" && su - root -c "{command}"\'')
    # run_command(f'xterm -hold -e \'echo "Введите пароль суперпользователя" && su - root -c "{command}"\'')


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


def ping(host) -> bool:
    result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
    if result.returncode == 0:
        logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
        return True
    elif result.returncode == 2:
        logging.info(f"ping: {host}: {result=} {result.returncode=}")
        return False
    else:
        return False


def test_ssh(host) -> bool:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=host, port=22, timeout=5, username='root')
        logging.info(f"Подключено по ssh@root без пароля к {host}")
        return True
    except Exception as e:
        logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}: {e}")
        return False


# Получение имени компьютера и текущего пользователя
this_host = run_command('hostname').strip()
user = run_command('whoami').strip()
