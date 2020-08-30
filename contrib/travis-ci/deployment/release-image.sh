#!/bin/bash

# NOTE: this script has to run inside Travis CI VM.

CONTAINER=docker RELEASE_VERSION=${TRAVIS_TAG#v} make release-image
CONTAINER=docker make publish-release-image
