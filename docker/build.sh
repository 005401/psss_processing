#!/bin/bash
VERSION=1.5.0
docker build --no-cache=true -t docker.psi.ch:5000/psss_processing .
docker tag docker.psi.ch:5000/psss_processing docker.psi.ch:5000/psss_processing:$VERSION
docker push docker.psi.ch:5000/psss_processing:$VERSION
docker push docker.psi.ch:5000/psss_processing
