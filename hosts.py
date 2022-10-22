import logging
from dataclasses import dataclass
from json import loads, dumps

from config import hosts_file_path


@dataclass
class Host:
    hostname: str
    mac_address: str
    # name: str

    # def __init__(self, name: str, hostname: str, mac_address: str = ''):
    #     self.name = hostname.split('.')[0]
    #     self.hostname = hostname
    #     self.mac_address = mac_address

    def name(self) -> str:
        return self.hostname.split('.')[0]

    def to_dict(self):
        return {"hostname": self.hostname, "mac_address": self.mac_address}


class Hosts:
    def __init__(self):
        self.filename = hosts_file_path
        with open(self.filename, 'r', encoding='utf-8') as file:
            if not file.read():
                self.clean()
        self.hosts: dict = self.read()

    def __str__(self):
        result = ''
        for host in self.hosts:
            result += self.hosts[host]['hostname'] + '\n'
        return result

    def __len__(self) -> int:
        return len(self.hosts)

    def __getitem__(self, item: str):
        host = Host(hostname=self.hosts[item]['hostname'], mac_address=self.hosts[item]['mac_address'])
        return host

    def __add__(self, host: Host):
        self.hosts[host.name()] = host.to_dict()
        self.write(self.hosts)
        return self

    def __delitem__(self, key):
        del self.hosts[key]
        return self.hosts

    def to_list(self):
        result = []
        for host in self.hosts:
            result.append(self.hosts[host]['hostname'])
        return result

    def read(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as file:
                return loads(file.read())
        except FileNotFoundError:
            logging.info('[error] Файл ' + self.filename + ' не найден')
            return None

    def write(self, value):
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(dumps(value))
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None
        else:
            return 0

    def clean(self):
        value = {}
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(dumps(value))
            self.hosts: dict = self.read()
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None

    def update(self, new_hosts: str):
        new_hosts = new_hosts.split('\n')
        self.clean()
        for new_host in new_hosts:
            self.hosts[new_host.split('.')[0]] = Host(hostname=new_host, mac_address='').to_dict()
        self.write(self.hosts)
        return self
