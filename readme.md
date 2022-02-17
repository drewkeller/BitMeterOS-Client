# BitMeter OS Client

This project provides a client interface to the BitMeter OS project version 0.8 (https://github.com/codebox/bitmeteros), which has the ability to track internet traffic separately from local network traffic. BitMeter OS version 0.7 has a client interface, but I needed one for version 0.8.

This client runs as a taskbar icon with a context menu available when you right click the icon.

The program reads the BitMeter database and checks the status of each alert. The taskbar icon and tooltip text change depending on the highest percentage used out of all of the alerts. The menu indicates an icon, percentage used and usage of each alert. If an alert exceeds a configurable threshold percentage, a toast notification is displayed.

The menu also provides a way to open the webpage for the localhost and any other hosts called out by the configuration file.


## Installation

This client can be compiled into an executable or be run using an installed version of python.


### Creating an Executable

> This creates an executable file that can run on Windows without requiring an installation of Python on the target computer. The biggest drawback is, the executable uses 200+ MB of memory.

1. Install **Py Auto to Exe** (https://pypi.org/project/auto-py-to-exe/).

    `pip install auto-py-to-exe`

2. Start auto-py-to-exe and load/import the settings from the configuration file included in this repository, *py-auto-cfg.json*

3. Click the big button at the bottom to compile. The generated files can be found in the *output* subfolder.

4. To install on a target system, see below.


### Installing on a Target Computer

1. Install BitMeter OS version 0.8 or higher from https://codebox.net/pages/bitmeteros

2. (Python installation only) Install Python. Python can be installed from one of the packages here: https://www.python.org/downloads/.

    > IMPORTANT: wxPython doesn't fully work on python 3.10, yet, so install a python version 3.9 or less.

3. (Python installation only) Install the remaining dependencies. Open a command prompt and execute the following.

    `pip install wxPython dateutils pyyaml`

4. Copy the files from this repository into an installation location of your choice, such as ***%APPDATA%\BitMeter OS Client***.

5. Create a shortcut to bitmeter.py (*%APPDATA%\Microsoft\Windows\Start Menu\Programs\BitMeter OS Client\BitMeter OS Client.lnk*). In the Target field, prepend with "pythonw". Optionally, change the icon. Put the shortcut in the Windows Start menu (*%APPDATA%\Microsoft\Windows\Start Menu\Programs\Bitmeter OS Client*)

6. Optionally, if you want the client to run at Windows startup, copy the shortcut to the startup folder (*%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup*).

7. Copy the default configuration file to *%APPDATA%\BitMeter OS Client* or run the program once to create it and edit it as desired.

## Configuration

The configuration file is %APPDATA%\BitMeter OS Client\config.yaml. If it doesn't exist, it is created upon first run of the program, with default values. For the most part, the names are self-explanatory, but some are described below.

### Hosts

Menu items are created for each host named in the configuration file. Here's an example to show the formatting for items that will open http://myhostname1:2605 and http://myhostname2:1234.

  0:
    label: This label appears in the menu
    name: myhostname1
  1:
    label: Another menu item
    name: myhostname2
    port: 1234
