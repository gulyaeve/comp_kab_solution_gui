rm -rf ~/rpmbuild/SOURCES/
mkdir -p ~/rpmbuild/SOURCES
cp * ~/rpmbuild/SOURCES/
cp -r modules ~/rpmbuild/SOURCES/modules
rpmbuild -ba teacher_control_package.spec