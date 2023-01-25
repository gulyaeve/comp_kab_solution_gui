# Ярлыки на сетевую папку
network_share = """[Desktop Entry]
Icon=folder-remote
Name=Задания
Type=Application
Exec=dolphin smb://{teacher_host}.local/home/share
"""

network_share_for_teacher = """[Desktop Entry]
Icon=folder-remote
Name=Задания
Type=Link
URL[$e]=/home/share
"""

# Ярлык veyon
veyon_link = """[Desktop Entry]
Version=1.0
Type=Application
Exec=/usr/bin/veyon-master
Icon=/usr/share/icons/hicolor/scalable/apps/veyon-master.svg
Terminal=false
Name=Управление компьютерным классом
Comment=Monitor and control remote computers
Comment[de]=Entfernte Computer beobachten und steuern
Comment[ru]=Наблюдение за удалёнными компьютерами и управление ими (veyon)
Categories=Qt;Education;Network;RemoteAccess;
Keywords=classroom,control,computer,room,lab,monitoring,teacher,student
"""

# Ярлык на ssh-add для автозагрузки
ssh_add_link = """[Desktop Entry]
Exec=ssh-add
Icon=
Name=ssh-add
Path=
Terminal=False
Type=Application
"""

smb_conf = "[global]\n" \
           "dos charset = CP866\n" \
           "unix charset = utf8\n" \
           "display charset = cp1251\n" \
           "workgroup = WORKGROUP\n" \
           "server string = Filestore\n" \
           "security = USER\n" \
           "map to guest = Bad User\n" \
           "[Public]\n" \
           "path = /home/share\n" \
           "read only = Yes\n" \
           "guest ok = Yes\n" \
           "browseable = yes\n" \
           "writable = yes\n" \
           "create mask = 0777\n" \
           "force create mask = 0777\n" \
           "directory mask = 0777"
