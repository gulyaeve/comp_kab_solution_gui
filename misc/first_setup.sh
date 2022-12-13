#!/bin/sh

if [[ $(whoami) == 'root' ]]
then
    teacher_pass=$(kdialog --title="Создание пользователя teacher" --inputbox "Введите пароль, который будет установлен для учётной записи teacher" $teacher_pass)
    useradd teacher && gpasswd -a teacher wheel && chpasswd <<<"teacher:$teacher_pass"

    myhostname=$(hostname)
    myhostname=$(kdialog --title="Переименование компьютера" --inputbox "Введите имя компьютера" $myhostname)
    rm -f /etc/machine-id && rm -f /var/lib/dbus/machine-id && dbus-uuidgen --ensure && systemd-machine-id-setup
    hostnamectl hostname $myhostname

    reboot
else
    echo 'Требуется запускать от суперпользователя'
fi
