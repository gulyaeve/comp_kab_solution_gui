import logging
import re
from dataclasses import dataclass
from json import loads, dumps

from modules.config import hosts_file_path, ip_expression


@dataclass
class Host:
    name: str
    hostname: str = ""
    mac_address: str = ""

    # def name(self) -> str:
    #     return self.hostname.split('.local')[0]

    def to_dict(self):
        return {
            "name": self.name,
            "hostname": self.hostname,
            "mac_address": self.mac_address,
        }


class Hosts:
    def __init__(self):
        self.filename = hosts_file_path
        with open(self.filename, 'r', encoding='utf-8') as file:
            if not file.read():
                self.clean()
        self.hosts: dict = self._read()

    def __str__(self) -> str:
        result = ''
        for host in self.hosts:
            result += self.hosts[host]['hostname'] + '\n'
        return result

    def __len__(self) -> int:
        return len(self.hosts)

    def __getitem__(self, item_key: str) -> Host:
        return Host(
            hostname=self.hosts[item_key]['hostname'],
            mac_address=self.hosts[item_key]['mac_address'],
            name=self.hosts[item_key]['name']
        )

    def set_item(self, key: str, hostname: str = '', mac_address: str = ''):
        hostname = hostname.replace(' ', '').strip()
        if not hostname:
            host = Host(hostname="", mac_address=mac_address, name=key)
        elif hostname.endswith('.local'):
            host = Host(hostname=hostname, mac_address=mac_address, name=key)
        elif re.match(ip_expression, hostname):
            host = Host(hostname=hostname, mac_address=mac_address, name=key)
        else:
            host = Host(hostname=f"{hostname}.local", mac_address=mac_address, name=key)
        self.hosts[key] = host.to_dict()
        self._write(self.hosts)
        return self

    # def __add__(self, hostname: str, mac_address: str = ''):
    #     hostname = hostname.replace(' ', '').strip()
    #     if hostname.endswith('.local'):
    #         host = Host(hostname=hostname, mac_address=mac_address)
    #     elif re.match(ip_expression, hostname):
    #         host = Host(hostname=hostname, mac_address=mac_address)
    #     else:
    #         host = Host(hostname=f"{hostname}.local", mac_address=mac_address)
    #     self.hosts[host.name()] = host.to_dict()
    #     self._write(self.hosts)
    #     return self

    def __delitem__(self, key):
        del self.hosts[key]
        self._write(self.hosts)
        return self

    def save_hostname(self, key, hostname):
        if hostname.endswith('.local'):
            host = Host(hostname=hostname, name=key)
        elif re.match(ip_expression, hostname):
            host = Host(hostname=hostname, name=key)
        else:
            host = Host(hostname=f"{hostname}.local", name=key)
        self.hosts[key] = host.to_dict()
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
                file.write(dumps(value, indent=4, ensure_ascii=False))
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None

    def to_list(self) -> list:
        result = []
        for host in self.hosts:
            result.append(self.hosts[host]['name'])
        return result

    def items_to_list(self) -> [Host]:
        result = []
        for host in self.hosts:
            result.append(
                Host(
                    hostname=self.hosts[host]['hostname'],
                    mac_address=self.hosts[host]['mac_address'],
                    name=self.hosts[host]['name']
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
