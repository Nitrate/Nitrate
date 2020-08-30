#!/bin/bash

# NOTE: this script has to run inside Travis CI VM.

openssl aes-256-cbc -K $encrypted_67fe40463319_key -iv $encrypted_67fe40463319_iv \
  -in contrib/travis-ci/deployment/copr-cli.conf.enc -out copr-cli.conf -d

docker run -v $(pwd):/code:Z --rm -it registry.fedoraproject.org/fedora:32 /bin/bash -c "
  dnf \
    --disablerepo=fedora-modular --disablerepo=updates-modular --disablerepo=fedora-cisco-openh264 \
    install -y copr-cli

  copr-cli \
    --config /code/copr-cli.conf \
    buildscm --method make_srpm \
             --type git \
             --clone-url https://github.com/Nitrate/python-nitrate-tcms.git \
             -r fedora-31-x86_64 \
             -r fedora-32-x86_64 \
             cqi/python-nitrate-tcms
"
