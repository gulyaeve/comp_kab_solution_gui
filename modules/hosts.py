import logging
from dataclasses import dataclass
from json import loads, dumps

from modules.config import hosts_file_path
from modules.system import test_ping, test_ssh, get_mac_address


@dataclass
class Host:
    hostname: str
    mac_address: str = ""
    ping: bool = False
    ssh: bool = False

    def name(self) -> str:
        return self.hostname.split('.local')[0]

    def to_dict(self):
        return {
            "hostname": self.hostname,
            "mac_address": self.mac_address
        }


class Hosts:
    def __init__(self):
        self.filename = hosts_file_path
        with open(self.filename, 'r', encoding='utf-8') as file:
            if not file.read():
                self.clean()
        self.hosts: dict = self._read()

    def __str__(self):
        result = ''
        for host in self.hosts:
            result += self.hosts[host]['hostname'] + '\n'
        return result

    def __len__(self) -> int:
        return len(self.hosts)

    def __getitem__(self, item: str):
        return Host(
            hostname=self.hosts[item]['hostname'],
            mac_address=self.hosts[item]['mac_address']
        )

    def __setitem__(self, key: str, hostname: str, mac_address: str = ''):
        key = key.replace(' ', '').strip()
        hostname = hostname.replace(' ', '').strip()
        if hostname.endswith('.local'):
            host = Host(hostname=hostname, mac_address=mac_address)
        else:
            host = Host(hostname=f"{hostname}.local", mac_address=mac_address)
        if key.endswith('.local'):
            key = key.split('.local')[0]
        self.hosts[key] = host.to_dict()
        self._write(self.hosts)
        return self

    def __add__(self, hostname: str, mac_address: str = ''):
        hostname = hostname.replace(' ', '').strip()
        if hostname.endswith('.local'):
            host = Host(hostname=hostname, mac_address=mac_address)
        else:
            host = Host(hostname=f"{hostname}.local", mac_address=mac_address)
        self.hosts[host.name()] = host.to_dict()
        self._write(self.hosts)
        return self

    def __delitem__(self, key):
        if key.endswith('.local'):
            key = key.split('.local')[0]
        del self.hosts[key]
        self._write(self.hosts)
        return self

    def save_mac_address(self, key, mac_address):
        if key.endswith('.local'):
            key = key.split('.local')[0]
        host = self.hosts[key]
        host['mac_address'] = mac_address
        self.hosts[key] = host
        self._write(self.hosts)
        return self

    def _read(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as file:
                return loads(file.read())
        except FileNotFoundError:
            logging.info('[error] Файл ' + self.filename + ' не найден')
            return None

    def _write(self, value):
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(dumps(value))
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None

    def to_list(self):
        result = []
        for host in self.hosts:
            result.append(self.hosts[host]['hostname'])
        return result

    def items_to_list(self) -> [Host]:
        result = []
        for host in self.hosts:
            result.append(Host(hostname=self.hosts[host]['hostname'], mac_address=self.hosts[host]['mac_address']))
        return result

    def items_with_status(self) -> [Host]:
        result = []
        for host in self.hosts:
            hostname = self.hosts[host]['hostname']
            host_ping = test_ping(hostname)
            host_ssh = False if host_ping is False else test_ssh(hostname)
            host_mac_address = '' if host_ssh is False else get_mac_address(hostname)
            result.append(
                Host(
                    hostname=hostname,
                    mac_address=host_mac_address,
                    ping=host_ping,
                    ssh=host_ssh
                )
            )
        return result

    def clean(self):
        value = {}
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(dumps(value))
            self.hosts: dict = self._read()
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None

    # def update(self, new_hosts: str):
    #     new_hosts = new_hosts.split('\n')
    #     self.clean()
    #     for new_host in new_hosts:
    #         self.hosts[new_host.split('.')[0]] = Host(hostname=new_host, mac_address='').to_dict()
    #     self._write(self.hosts)
    #     return self
