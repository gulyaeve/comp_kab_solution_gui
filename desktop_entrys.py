

# Ярлыки на сетевую папку
network_share = """[Desktop Entry]
Icon=folder-remote
Name=Задания
Type=Application
Exec=dolphin sftp://student@{teacher_host}.local/home/share
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

# Ярлык приложения "Собрать работы"
teacher_sh_link = f"""[Desktop Entry]
Icon=/usr/share/icons/breeze-dark/apps/48/rocs.svg
Name=Собрать работы
Type=Application
Exec=sh /home/teacher/teacher_control/teacher_control.sh
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
