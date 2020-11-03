#!/bin/bash
# Run this script from the project root directory
set -ex
disablerepos=("--disablerepo=fedora-modular" "--disablerepo=updates-modular" "--disablerepo=fedora-cisco-openh264")
dnf "${disablerepos[@]}" install -y dnf-utils make rpm-build
dnf copr enable -y cqi/python-nitrate-tcms
dnf "${disablerepos[@]}" builddep -y python-nitrate-tcms.spec
make tarball rpm
