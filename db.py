#!/usr/bin/env python

import config
import sqlite3
import os
import sys
#import datetime
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re

from numpy import number

class Database():
    def __init__(self):
        dbPath = self.getDbPath()
        self.conn = sqlite3.connect(dbPath)
        self.conn.row_factory = sqlite3.Row
        self.alerts = {}
        self.intervals = {}
        self.filters = {}

    def getDbPath(self):
        dbPath = os.getenv('BITMETER_DB')
        if sys.platform == 'win32':
          # Windows
            #dbPath = dbPath or "/Documents and Settings/All Users/Application Data/BitMeterOS/bitmeter.db"
            dbPath = dbPath or os.path.expandvars("%ProgramData%/BitMeterOS/bitmeter.db") #"C:/ProgramData/BitMeterOS/bitmeter.db"
            
        elif sys.platform == 'darwin':
          # Mac OSX
            dbPath = dbPath or "/Library/Application Support/BitMeter/bitmeter.db"
            
        elif sys.platform.startswith('linux'):
          # Linux
            dbPath = dbPath or "/var/lib/bitmeter/bitmeter.db"
        
        if not os.path.exists(dbPath):
            print (_('Database file not found') + ': ' + dbPath)
            sys.exit(1)

        return dbPath

    def getAlertIntervals(self):
        q = self.conn.cursor()
        q.execute("SELECT * from interval")
        self.intervals = {}
        for row in q.fetchall():
            data = dict(row)
            interval = AlertInterval(id=data['id'], year=data['yr'], month=data['mn'], day=data['dy'], week=data['wk'], hour=data['hr'])
            self.intervals[data['id']] = interval
        return self.intervals

    def getFilters(self):
        q = self.conn.cursor()
        q.execute("SELECT * from filter")
        self.filters = {}
        for row in q.fetchall():
            data = dict(row)
            filter = Filter(id=data['id'], desc=data['desc'], name=data['name'], expr=data['expr'], host=data['host'])
            self.filters[data['id']] = filter
        return self.intervals

    def getAlerts(self):
        q = self.conn.cursor()
        q.execute('''
        SELECT id, name, bound as interval, filter, amount
        FROM alert
        WHERE active = 1;
        ''')

        #self.alerts = {}
        self.getAlertIntervals()
        self.getFilters()
        for row in q.fetchall():
            data = dict(row)
            interval = self.intervals[data['interval']]
            filter = self.filters[data['filter']]
            id = data['id']
            alert = Alert(id=id, name=data['name'], interval=interval, filter=filter, amount=data['amount'])
            if not id in self.alerts or self.alerts[id] != alert:
                self.alerts[id] = alert
        return self.alerts

    def getHighestAlertPercent(self):
        highest = 0
        amount = 0
        highestAlert = {}
        for id, alert in self.alerts.items():
            (usage, percent) = self.getAlertUsage(id)
            if percent > highest:
                highest = percent
                highestAlert = alert
        return (highestAlert, highest, usage)

    def getAlertUsage(self, alertId):
        alert = self.alerts[alertId]
        timestamp = alert.getTimeStamp()

        query = f"SELECT ts, dr, SUM(vl) as vl FROM data WHERE fl={alert.filter.id} and ts>={timestamp};"
        q = self.conn.cursor()
        q.execute(query)
        for row in q.fetchall():
            data = dict(row)
            usage = Bandwidth(data['vl'])
        
        percent = usage.bytes / alert.amount * 100.0
        return (usage, percent)
        
class Bandwidth():
    factors = { 'K': 1024, 'M': 1024*1024, 'G': 1024*1024*1024, 'T': 1024*1024*1024*1024 }

    def __init__(self, numBytes):
        self.bytes = numBytes

    def fromString(str):
        matches = re.search("(?P<num>[0-0,.]+)\s*(?P<factor>[kMGT])B", str, re.IGNORECASE);
        num = matches.group("num")
        factor = matches.group("factor").upper()
        return Bandwidth(num * Bandwidth.factors[factor])

    def toString(self):
        if self.bytes < self.factors['K']:
            bytes = self.bytes
            units = ""
        elif self.bytes < self.factors['M']:
            bytes = self.bytes/self.factors['K']
            units = "K"
        elif self.bytes < self.factors['G']:
            bytes = self.bytes/self.factors['M']
            units = "M"
        elif self.bytes < self.factors['T']:
            bytes = self.bytes/self.factors['G']
            units = "G"
        else:
            bytes = self.bytes/self.factors['T']
            units = "T"
        return f"{bytes:.2f} {units}B"

class Alert():
    def __init__(self, id, name, interval, filter, amount):
        self.id = id
        self.name = name
        self.interval = interval
        self.filter = filter
        self.amount = amount
        self.lastNotified = 0

    def getTimeStamp(self):
        return self.interval.getTimeStamp()

    def getUsage(self):
        (usage, percent) = config.db.getAlertUsage(self.id)
        return (usage, percent)

    def __eq__(self, other):
        if isinstance(other, Alert):
            return self.id == other.id \
                and self.name == other.name \
                and self.amount == other.amount \
                and self.interval == other.interval \
                and self.filter == other.filter
        return False

class AlertInterval():
    def __init__(self, id, year, month, day, week, hour):
        self.id = id
        self.year = year
        self.month = month
        self.day = day
        self.week = week
        self.hour = hour
    
    def getTimeStamp(self):
        now   = datetime.now()
        delta = timedelta(0)

        year  = now.year  if self.year  == "*" else int(self.year)
        month = now.month if self.month == "*" else int(self.month)
        day   = now.day   if self.day   == "*" else int(self.day)
        week  = 0         if self.week  == "*" else int(self.week)
        hour  = now.hour  if self.hour  == "*" else int(self.hour)
        if year < 0 or month < 0 or day < 0 or week < 0 or hour < 0:
            # rolling period
            years  = 0 if self.year  == "*" else int(self.year)
            months = 0 if self.month == "*" else int(self.month)
            days   = 0 if self.day   == "*" else int(self.day)
            weeks  = 0 if self.week  == "*" else int(self.week)
            hours  = 0 if self.hour  == "*" else int(self.hour)
            delta = relativedelta(years=years, months=months, days=days, weeks=weeks, hours=hours)
            dt = now + delta

        else:
            if hour > now.hour:
                delta -= relativedelta(days = 1)
            if day > now.day:
                delta -= relativedelta(months = 1)
            if month > now.month:
                delta -= relativedelta(years = 1)

            dt = datetime(year, month, day, hour) + delta

        timestamp = int(round(dt.timestamp()))
        return timestamp

    def __eq__(self, other):
        if isinstance(other, AlertInterval):
            return self.id == other.id \
                and self.year == other.year and self.month == other.month \
                and self.day == other.day and self.week == other.week \
                and self.hour == other.hour
        return False

class Filter():
    def __init__(self, id, desc, name, expr=None, host=None):
        self.id = id
        self.desc = desc
        self.expr = expr
        self.host = host
    
    def __eq__(self, other):
        if isinstance(other, Filter):
            return self.id == other.id and self.desc == other.desc \
                and self.expr == other.expr and self.host == other.host
        return False