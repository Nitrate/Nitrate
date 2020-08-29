#!/bin/bash
set -ex
disablerepos=(--disablerepo=fedora-modular --disablerepo=updates-modular --disablerepo=fedora-cisco-openh264)
dnf ${disablerepos[@]} install -y dnf-utils make rpm-build
dnf copr enable -y cqi/python-nitrate-tcms
cd /code
dnf ${disablerepos[@]} builddep -y python-nitrate-tcms.spec
make tarball rpm
