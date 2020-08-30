#!/bin/bash

# NOTE: This script has to run inside Travis CI VM.

openssl aes-256-cbc -K $encrypted_f6077625039f_key -iv $encrypted_f6077625039f_iv \
  -in contrib/travis-ci/deployment/pypirc.enc -out pypirc -d

docker run -v $(pwd):/code:Z --rm -it registry.fedoraproject.org/fedora:32 /bin/bash -c "
  dnf \
    --disablerepo=fedora-modular --disablerepo=updates-modular --disablerepo=fedora-cisco-openh264 \
    install -y twine
  cd /code
  python3 setup.py sdist
  twine upload --config-file /code/pypirc dist/*
"
