echo 'Введите пароль суперпользователя' && su - root -c '
mkdir -p tmp &&
cd tmp &&
rm -f -r * &&
wget https://link.educom.ru/uploads/docs/it_auditory/it_solution_auditory/comp_kab_solution_package.tar.gz &&
tar -xvf comp_kab_solution_package.tar.gz &&
cd comp_kab_solution_package &&
cp teacher_control /usr/bin/teacher_control &&
cp teacher_control.svg /usr/share/icons/hicolor/scalable/apps/teacher_control.svg &&
cp teacher_control.desktop /usr/share/applications/teacher_control.desktop &&
mkdir /usr/share/teacher_control &&
cp student.tar.gz /usr/share/teacher_control/student.tar.gz
'