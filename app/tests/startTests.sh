#! /usr/bin/env bash
echo "Waiting 1 seconds and run test"
sleep 1
pytest -v -s --cache-clear --log-level=INFO