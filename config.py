#!/usr/bin/env python

import yaml
import os.path

CONFIG_FILE = "%APPDATA%/BitMeter OS Client/config.yaml"

config = {}
configPath = os.path.expandvars(CONFIG_FILE)
if os.path.exists(configPath):
    config = yaml.safe_load(open(configPath))

app = {}
db = {}
