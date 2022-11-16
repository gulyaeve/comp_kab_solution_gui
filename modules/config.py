from modules.system import user

# test config
# config_path = f'misc'

config_path = f'/home/{user}/.teacher_control'
hosts_file_path = f'{config_path}/hosts.json'
version = "1.0"
hostname_expression = r"(s[cmnpt][\w\d]+)(-[\w\d]+){1,3}.local"
ip_expression = r"((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$"
