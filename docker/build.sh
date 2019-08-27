#!/bin/bash
VERSION=1.6.2
docker build --no-cache=true -t paulscherrerinstitute/psss_processing .
docker tag paulscherrerinstitute/psss_processing paulscherrerinstitute/psss_processing:$VERSION
docker push paulscherrerinstitute/psss_processing:$VERSION
docker push paulscherrerinstitute/psss_processing
