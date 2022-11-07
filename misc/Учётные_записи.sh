#!/bin/sh

if [[ $(whoami) == 'root' ]]
then
    echo 'Задайте пароль учителю:'
    read p
    useradd teacher && gpasswd -a teacher wheel && chpasswd <<<"teacher:$p"
    echo 'Задайте пароль ученику:'
    read p
    useradd student && chpasswd <<<"student:$p"
    if id student &>/dev/null
    then
        sed -i'.bak' -E -e 's,^Session.+,Session=plasma,' -e 's,^User.+,User=student,' /etc/X11/sddm/sddm.conf
    fi
    reboot
else
    echo 'Требуется запускать от суперпользователя'
fi
