Dockerfiles and script to run tests inside Travis-CI.

Build image for running tests with specific Python version::

    make testenv-image testenv_pybin=python3.[67]

Push image to Quay.io::

    make push-testenv-image testenv_pybin=python3.[67]

.. note::
   Images have to be pushed to Quay.io before running tests inside Travis-CI.

Sometimes, it would fail to push image to Quay.io due to some network issues.
In this case, just push directly using option ``force_push=true`` without
building image again. For example::

    make push-testenv-image testenv_pybin=python3.7 force_push=true
