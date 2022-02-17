#!/usr/bin/env python

import dataclasses
from dataclasses import dataclass, field
import typing
import yaml
import os
import os.path

CONFIG_DIR = "%APPDATA%/BitMeter OS Client"
CONFIG_FILE = "config.yaml"

# global variables
app = {}
db = {}

@dataclass
class Host():
    label: str
    name: str
    port: int = 2605

# interesting alternatives for config files:
#   https://martin-thoma.com/configuration-files-in-python/
@dataclass
class Config():
    taskbar_theme: str = "dark"
    menu_theme: str = "light"
    warning_threshold_percent: int = 75
    hosts: typing.List[Host] = field(default_factory=list)

    def __post_init__(self):
        if len(self.hosts) > 0:
            for k,v in self.hosts.items():
                self.hosts[k] = Host(**v)
        pass

configPath = os.path.join(os.path.expandvars(CONFIG_DIR), CONFIG_FILE)
config = Config()
success = False
if os.path.exists(configPath):
    try:
        with open(configPath) as file:
            data = yaml.safe_load(file)
            config = Config(**data)
            success = True
    except:
        success = False
else:
    # write a default config file if it doesn't exist
    os.makedirs(os.path.expandvars(CONFIG_DIR), exist_ok=True)
    with open(configPath, "w") as f:
        dict = dataclasses.asdict(config)
        str = yaml.safe_dump(dict, default_flow_style=False, indent=4)
        f.write(str)

