rm -rf ~/RPM/SOURCES/
mkdir -p ~/RPM/SOURCES
cp * ~/RPM/SOURCES/
cp -r modules ~/RPM/SOURCES/modules
rpmbuild -ba teacher_control_package.spec