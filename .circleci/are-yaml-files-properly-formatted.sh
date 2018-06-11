#! /usr/bin/env bash

shopt -s globstar

if ! git diff-index --name-only --exit-code HEAD -- **/*.yaml
then
    echo "This or those files are not appropriately formatted."
    echo "Run openfisca_france/scripts/yaml_round_trip.py to format files and git diff to see the differences."
    exit 3
fi
