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

    def __len__(self) -> int:
        """
        Получение количества хостов
        :return: размер словаря
        """
        return len(self.hosts)

    def __getitem__(self, key: str) -> Host:
        """
        Получение элемента
        :param key: ключ
        :return: элемент Host
        """
        return Host(
            hostname=self.hosts[key]['hostname'],
            mac_address=self.hosts[key]['mac_address'],
            name=self.hosts[key]['name']
        )

    def __delitem__(self, key: str):
        """
        Удаление элемента
        """
        del self.hosts[key]
        self._write(self.hosts)
        return self

    def _read(self):
        """
        Чтение данных из файла
        :return: json loads или None если файла нет
        """
        try:
            with open(self.filename, 'r', encoding='utf-8') as file:
                return loads(file.read())
        except FileNotFoundError:
            logging.info('[error] Файл ' + self.filename + ' не найден')
            return None

    def _write(self, value: dict):
        """
        Запись данных в файл
        :param value: словарь для записи
        :return: None если ключа нет
        """
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(dumps(value, indent=4, ensure_ascii=False))
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None

    def clean(self):
        """
        Очистка файла и словаря
        """
        value = {}
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(dumps(value))
            self.hosts: dict = self._read()
        except KeyError:
            logging.info('[error] Ключ не найден')
            return None

    def set_item(self, key: str, hostname: str = '', mac_address: str = ''):
        """
        добавить/изменить элемент
        :param key: ключ
        :param hostname: адрес хоста
        :param mac_address: мак-адрес хоста
        :return: self
        """
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

    def to_list(self) -> list:
        """
        Получение имён хостов в виде списка
        :return: list
        """
        result = []
        for host in self.hosts:
            result.append(self.hosts[host]['name'])
        return result

    def items_to_list(self) -> [Host]:
        """
        Получение хостов в виде списка
        :return: list
        """
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
