#!/usr/bin/env python3
import os
from getpass import getpass
import subprocess
import logging
import time
from socket import *
import paramiko
from paramiko.channel import Channel
from paramiko.ssh_exception import AuthenticationException, SSHException

from system import this_host, user, exit_app, run_command
from desktop_entrys import ssh_add_link, veyon_link, teacher_sh_link, network_share, network_share_for_teacher







#
# if __name__ == "__main__":
#     main()
