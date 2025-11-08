#!/bin/bash
# run.sh

# source the environment/alias setup
source ./setalias.sh

# now python alias or env vars are visible
python launcher.py --num_tasks 2 --env secrets/secrets.env
