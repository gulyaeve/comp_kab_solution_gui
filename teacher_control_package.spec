Name: teacher_control
Group: Education
Version: 1
Release: 1

Summary: Setup computer auditory
Summary(ru_RU.UTF-8): Инструменты организации работы в компьютерном классе

License: GPLv3
ExclusiveArch: x86_64

%description
Scripts for computer auditory

%description -l ru_RU.UTF-8
Данное решение позволяет:
ИТ-специалисту:
- настроить доступ по SSH для пользователя root на компьютеры учеников;
- настроить сетевую папку sftp для выдачи задания учителем;
- установить и настроить приложение veyon для управления и наблюдением за компьютерами учеников.
Учителю:
- удалённо собирать работы с компьютеров учеников;
- очищать папки для сбора работ;
- создавать и удалять локальную учётную запись student на компьютерах учеников;
- открывать в проводнике содержимое компьютера ученика для просмотра и редактирования.

%build
pyinstaller -n "teacher_control" --onefile %{_sourcedir}/app.py --add-data %{_sourcedir}/style.css:.

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps/
mkdir -p %{buildroot}/usr/share/applications/
cp %{_sourcedir}/teacher_control.svg teacher_control.svg
cp %{_sourcedir}/teacher_control.desktop teacher_control.desktop
install -m 755 dist/teacher_control %{buildroot}%{_bindir}/teacher_control
install -m 755 teacher_control.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/teacher_control.svg
install -m 755 teacher_control.desktop %{buildroot}/usr/share/applications/teacher_control.desktop

%files
%{_bindir}/teacher_control
/usr/share/icons/hicolor/scalable/apps/teacher_control.svg
/usr/share/applications/teacher_control.desktop
