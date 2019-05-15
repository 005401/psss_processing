#!/bin/bash
VERSION=1.5.0
docker build --no-cache=true -t paulscherrerinstitute/psss_processing .
docker tag paulscherrerinstitute/psss_processing paulscherrerinstitute/psss_processing:$VERSION
docker push paulscherrerinstitute/psss_processing:$VERSION
docker push paulscherrerinstitute/psss_processing
