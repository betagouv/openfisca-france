#! /usr/bin/env bash

if git diff-index HEAD -- **/*.yaml
then
    echo "One YAML file or more is not appropriately formatted"
    echo "Run openfisca_france/scripts/yaml_round_trip.py to format files and git diff to see the differences."
    exit 3
fi
