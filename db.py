#!/usr/bin/env python

from dataclasses import dataclass
import sqlite3
import os
import sys
from operator import attrgetter
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import logging
import gettext

from numpy import number

_=gettext.gettext

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
            logging.error(_('Database file not found') + ': ' + dbPath)
            sys.exit(1)

        return dbPath

    def getAlertIntervals(self):
        q = self.conn.cursor()
        q.execute("SELECT * from interval")
        self.intervals = {}
        for row in q.fetchall():
            data = dict(row)
            interval = AlertInterval(data['id'], year=data['yr'], month=data['mn'], day=data['dy'], week=data['wk'], hour=data['hr'])
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
            amount = Bandwidth(data['amount'])
            alert = Alert(id=id, name=data['name'], interval=interval, filter=filter, amount=amount)
            if not id in self.alerts or self.alerts[id] != alert:
                self.alerts[id] = alert
        return self.alerts

    def getSortedAlerts(self, specs=[('percent', True)]):
        """ specs=(attribue, reverse) """
        sortedAlerts = []
        now = datetime.now()
        for id, alert in self.alerts.items():
            self.getAlertUsage(id, now)
            sortedAlerts.append(alert)
        self.multisort(sortedAlerts, specs)
        return sortedAlerts

    def multisort(self, xs, specs):
        """ multisort(list(student_objects), (('grade', True), ('age', False))) """
        for key, reverse in reversed(specs):
            xs.sort(key=attrgetter(key), reverse=reverse)
        return xs

    def getHighestAlertPercent(self):
        alerts = self.getSortedAlerts([('percent', True)])
        return (alerts[0], alerts[0].percent, alerts[0].usage)
    
    def getAlertUsage(self, alertId, now):
        alert = self.alerts[alertId]
        timestamp = alert.getTimeStamp(now)

        query = f"SELECT ts, dr, SUM(vl) as vl FROM data WHERE fl={alert.filter.id} and ts>={timestamp};"
        q = self.conn.cursor()
        q.execute(query)
        for row in q.fetchall():
            data = dict(row)
            usage = Bandwidth(data['vl'])
            alert.setUsage(usage)
        #logging.debug(f"{usage.bytes}, {data['vl']}")
        
        return alert.usage
        
class Bandwidth():
    factors = { 'K': 1024, 'M': 1024*1024, 'G': 1024*1024*1024, 'T': 1024*1024*1024*1024 }

    def __init__(self, numBytes):
        self.bytes = 0 if numBytes == None else numBytes

    def __str__(self):
        return self.toString()

    def __repr__(self):
        return f"<{self.toString()}>"

    def __lt__(self, other):
        if isinstance(other, Bandwidth):
            return self.bytes < other.bytes
        return False

    def __eq__(self, other):
        if isinstance(other, Bandwidth):
            return self.bytes == other.bytes
        return False

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

@dataclass
class AlertInterval():
    id: int
    year: str = "*"
    month: str = "*"
    day: str = "*"
    week: str = "*"
    hour: str = "*"
    
    def getTimeStamp(self, now=None):
        now = datetime.now() if now == None else now
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

    def __lt__(self, other):
        if isinstance(other, AlertInterval):
            if self.isFieldLt(other, 'year'):
                return True
            if self.isFieldLt(other, 'month'):
                return True
            if self.isFieldLt(other, 'day'):
                return True
            if self.isFieldLt(other, 'week'):
                return True
            if self.isFieldLt(other, 'hour'):
                return True
        return False

    def isFieldLt(self, other, field):
        thisField = getattr(self, field)
        thatField = getattr(other, field)
        # a "*" is always less than or equal to a number in the same position
        if thisField == "*" and thatField != "*":
            return True
        if self.isInt(thisField) and self.isInt(thatField):
            thisInt = int(thisField)
            thatInt = int(thatField)
            #  a positive value is always less than a rolling value (<0)
            if thisInt >= 0 and thatInt < 0:
                return True
            # a rolling value (<0) is less than another rolling value if this < that
            if thisInt < 0 and thatInt < 0 and thisInt < thatInt:
                return True
            # both numbers > 0, the smaller value will occur before the larger
            if thisInt > 0 and thatInt > 0 and thisInt < thatInt:
                return True
        return False

    def isInt(self, val):
        try:
            int(val)
            return True
        except:
            return False

@dataclass
class Filter():
    id: int
    name: str
    desc: str
    expr: str = None
    host: str = None

@dataclass
class Alert():
    id: int
    name: str
    interval: AlertInterval
    filter: Filter
    amount: Bandwidth
    usage: int = 0
    percent: float = 0
    lastNotified: int = 0

    def __str__(self):
        return f"[{self.id}: {self.percent}% ({self.usage}/{self.amount})"

    def __repr__(self):
        return f"<{self.id}: {self.percent}% ({self.usage}/{self.amount})>"

    def getTimeStamp(self, now):
        return self.interval.getTimeStamp(now)

    def setUsage(self, usage):
        self.usage = usage
        self.percent = self.usage.bytes / self.amount.bytes * 100.0

    def __eq__(self, other):
        if isinstance(other, Alert):
            return self.id == other.id \
                and self.name == other.name \
                and self.amount.bytes == other.amount.bytes \
                and self.interval == other.interval \
                and self.filter == other.filter
        return False

