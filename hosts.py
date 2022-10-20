import logging
from dataclasses import dataclass
from json import loads, dumps
from system import user


filename = f'/home/{user}/.teacher_control/hosts.json'


@dataclass
class Host:
    hostname: str
    mac_address: str

    def to_dict(self):
        return {"hostname": self.hostname, "mac_address": self.mac_address}


class Hosts:
    def __init__(self):
        self.filename = filename
        with open(self.filename, 'r', encoding='utf-8') as file:
            if not file.read():
                self.clean()
        self.hosts: list = self.read()

    def __str__(self):
        result = ''
        for host in self.hosts:
            result += host['hostname'] + '\n'
        return result

    def __len__(self) -> int:
        return len(self.hosts)

    def __getitem__(self, item: int):
        host = Host(hostname=self.hosts[item]['hostname'], mac_address=self.hosts[item]['mac_address'])
        return host

    def __add__(self, host: Host):
        self.hosts.append(host.to_dict())
        self.write(self.hosts)
        return self

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
        value = []
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(dumps(value))
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None

    def update(self, new_hosts: str):
        new_hosts = new_hosts.split('\n')
        self.clean()
        for new_host in new_hosts:
            self.hosts.append(Host(hostname=new_host, mac_address='').to_dict())
        self.write(self.hosts)
        return self
