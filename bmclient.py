import cfg
import sys
import os
import subprocess
import re
from datetime import datetime, timedelta
import gettext

_ = gettext.gettext

class bmclient():
    def __init__(self):
        self.path = os.getenv('BitMeter_Dir')
        if self.path:
            self.path = self.path + os.sep + 'bmclient'
        else:
            print(_('Failed to get BITMETER_DIR'))
            sys.exit(1)

    def runCommand(self, command):
        #try:
            command = f"{self.path} {command}"
            print(command)
            output = subprocess.check_output(command).decode()
            #print(output)
            return output
        #except:
        #    print(f"Running command failed: '{command}'")

    def printSummary(self):
        print(self.runCommand("-m summary"))

    def getUsage(self, range):
        usage = self.runCommand(f"-mq idl -f idl -r {range}")
        #pattern = r"(?P<total>TOTAL:[ ]*[0-9.]+[ ]{0,1}[kMGT]{0,1}B)"
        pattern = "Total:(.*)"
        matches = re.search(pattern, usage, re.MULTILINE)
        total = matches.group(1).strip()
        print(total)
        return total
    
    def getRangeString(self, start, end):
        startStr = start.strftime("%Y%m%d%H")
        endStr = end.strftime("%Y%m%d%H")
        return f"{startStr}-{endStr}"

    def getTodayUsage(self):
        dt = datetime.now()
        return self.getUsage(dt.strftime("%Y%m%d"))

    def get24HourUsage(self):
        now = datetime.now()
        delta = now - timedelta(1)


    def getBillingPeriodUsage(self):
        now = datetime.now()
        billingDay = cfg.config['billing_day_of_month']
        if now.day == billingDay:
            dt = datetime(now.year, now.month, now.day)
        elif now.day > billingDay:
            dt = datetime(now.year, now.month, 18)
        else:
            # pick the previous month
            lastMonth = now - timedelta(billingDay - 1)
            dt = datetime(lastMonth.year, lastMonth.month, billingDay)
        range = self.getRangeString(dt, now)
        return self.getUsage(range)

