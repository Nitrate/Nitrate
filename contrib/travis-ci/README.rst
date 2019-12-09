Dockerfile and script to run tests inside Travis-CI.

Build the image::

    make testbox-image

Push image to Quay.io::

    make push-testbox-image

.. important::

   Image has to be pushed to Quay.io before running tests inside Travis-CI.

Sometimes, it would fail to push image to Quay.io due to some network issues.
In this case, just push directly using option ``skip_build=1``. For example::

    make push-testbox-image skip_build=1

Remove the built image::

    make remove-testbox-image
