#!/bin/bash -ex

version=$1

if [ -z "$version" ]; then
    echo "Missing version"
    exit 1
fi

git clone https://github.com/Nitrate/Nitrate.git
cd Nitrate

if ! git tag | grep "v$version" >/dev/null; then
    echo "🧯 Version v$version is not tagged yet."
    exti 1
fi

python3 setup.py sdist

# Need to config pypirc with authentication credential
twine upload dist/*
echo "🍋 Source distribution is published to PyPI"

dnf \
    --disablerepo=fedora-modular --disablerepo=updates-modular --disablerepo=fedora-cisco-openh264 \
    install -y copr-cli

# Need to config the copr-cli config file well
copr-cli buildscm \
    --method make_srpm \
    --type git \
    --clone-url https://github.com/Nitrate/python-nitrate-tcms.git \
    -r fedora-31-x86_64 \
    -r fedora-32-x86_64 \
    cqi/python-nitrate-tcms

echo "🍋 RPM is built in Copr"

CONTAINER=docker RELEASE_VERSION=$version make release-image publish-release-image

echo "🍋 Release image has been pushed to Quay.io"
