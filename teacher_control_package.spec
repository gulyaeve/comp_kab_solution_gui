Name: teacher_control
Group: Education
Version: 1
Release: 1
Summary: teacher control
License: MIT

%description
teacher control

%build
pyinstaller -n "teacher_control" --onefile %{_sourcedir}/app.py

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