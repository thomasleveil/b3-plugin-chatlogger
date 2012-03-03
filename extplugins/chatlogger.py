# encoding: utf-8
#
# ChatLogger Plugin for BigBrotherBot
# Copyright (C) 2008 Courgette
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# Changelog:
#
# 28/07/2008 - 0.0.1
# - manage say, teamsay and privatesay messages
# 14/08/2008 - 0.1.0
# - fix security issue with player names of messages containing double quote or antislash characters (Thx to Anubis for report and tests)
# - allows to setup a daily purge of old messages to keep your database size reasonable
# 13/09/2008 - 0.1.1
# - in config, the hour defined for the purge is now understood in the timezone defined in the main B3 config file (before, was understood as UTC time)
# - fix mistake in log text
# 7/11/2008 - 0.1.2 - xlr8or
# - added missing 'import b3.timezones'
# 22/12/2008 - 0.2.0 - Courgette
# - allow to use a customized table name for storing the
#   log to database. Usefull if multiple instances of the
#   bot share the same database.
#   Thanks to Eire.32 for bringing up the idea and testing.
# 11/04/2011 - 0.2.1 - Courgette
# - update the sql script to use the utf8 charset
# 16/04/2011 - 1.0.0 - Courgette
# - can log to a file instead of logging to db (or both) 
# - requires B3 1.6+
# 01/09/2011 - 1.1.0 - BlackMamba
# - log commands to db
# 01/09/2011 - 1.1.1 - Courgette
# - refactoring to reduce code duplication
# - better test coverage
# 12/09/2011 - 1.1.2 - Courgette
# - start without failure even if the plugin is loaded before the admin plugin
# - do not fail to handle SQLite database errors
# 20/12/2011 - 1.1.3 - Courgette
# - fixes #2 : Error DELETE FROM cmdlog WHERE msg_time (thanks to Mariodu62)
#
__version__ = '1.1.3'
__author__    = 'Courgette, xlr8or, BlackMamba'

import b3, time, threading, re
import logging
from b3 import clients
import b3.events
import b3.plugin
import b3.cron
import b3.timezones
import datetime, string
from b3 import functions

#--------------------------------------------------------------------------------------------------
class ChatloggerPlugin(b3.plugin.Plugin):
    _cronTab = None
    _max_age_in_days = None
    _hours = None
    _minutes = None
    _db_table = None
    _db_table_cmdlog = None
    _file_name = None
    _filelogger = None
    _save2db = None
    _save2file = None
    _file_rotation_rate = None
    
    
    def onLoadConfig(self):
        # remove eventual existing crontab
        if self._cronTab:
            self.console.cron - self._cronTab

        try:
            self._save2db = self.config.getboolean('general', 'save_to_database')
            self.debug('save chat to database : %s', 'enabled' if self._save2db else 'disabled')
        except b3.config.ConfigParser.NoOptionError:
            self._save2db = True
            self.info("Using default value '%s' for save_to_database", self._save2db)
        except ValueError, err:
            self._save2db = True
            self.warning('Unexpected value for save_to_database. Using default value (%s) instead. (%s)', self._save2db, err) 

        try:
            self._save2file = self.config.getboolean('general', 'save_to_file')
            self.debug('save chat to file : %s', 'enabled' if self._save2file else 'disabled')
        except b3.config.ConfigParser.NoOptionError:
            self._save2file = False
            self.info("Using default value '%s' for save_to_file", self._save2file)
        except ValueError, err:
            self._save2file = False
            self.warning('Unexpected value for save_to_file. Using default value (%s) instead. (%s)', self._save2file, err) 
                
        if not (self._save2db or self._save2file):
                self.warning("your config explicitly specify to log nowhere. Disabling plugin")
                self.disable()
                
        if self._save2db:
                self.loadConfig_database()
        if self._save2file:
                self.loadConfig_file()
    
    
    def loadConfig_file(self):
        try:
            self._file_name = self.config.getpath('file', 'logfile')
            self.info('Using file (%s) to store log', self._file_name)
        except Exception, e:
            self.error('error while reading logfile name. disabling logging to file')
            self._save2file = False
            return
        
        try:
            self._file_rotation_rate = self.config.get('file', 'rotation_rate')
            if self._file_rotation_rate.upper() not in ('H', 'D', 'W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6'):
                    raise ValueError, 'Invalid rate specified: %s' % self._file_rotation_rate
            self.info("Using value '%s' for the file rotation rate", self._file_rotation_rate)
        except b3.config.ConfigParser.NoOptionError:
            self._file_rotation_rate = 'D'
            self.info("Using default value '%s' for the file rotation rate", self._file_rotation_rate)
        except ValueError, e:
            self._file_rotation_rate = 'D'
            self.warning("unexpected value for file rotation rate. Falling back on default value : '%s' (%s)", self._file_rotation_rate, e)
        
        self.setup_fileLogger()

            
    def setup_fileLogger(self):
        try:
            self._filelogger = logging.getLogger('chatlogfile')
            handler = logging.handlers.TimedRotatingFileHandler(self._file_name, when=self._file_rotation_rate, encoding="UTF-8")
            handler.setFormatter(logging.Formatter('%(asctime)s\t%(message)s', '%y-%m-%d %H:%M:%S'))
            self._filelogger.addHandler(handler)
            self._filelogger.setLevel(logging.INFO)
        except Exception, e:
            self._save2file = False
            self.error("cannot setup file chat logger. disabling logging to file (%s)", e)
    
    
    def loadConfig_database(self):
        try:
            self._db_table = self.config.get('database', 'db_table')
            self.debug('Using table (%s) to store log', self._db_table)
        except:
            self._db_table = 'chatlog'
            self.debug('Using default value (%s) for db_table', self._db_table) 

        try:
            self._db_table_cmdlog = self.config.get('database', 'db_table_cmdlog')
            self.debug('Using table (%s) to store command log', self._db_table_cmdlog)
        except:
            self._db_table_cmdlog = 'cmdlog'
            self.debug('Using default value (%s) for db_table_cmdlog', self._db_table_cmdlog) 
            
        try:
            max_age = self.config.get('purge', 'max_age')
        except:
            days = 0
            self.debug('Using default value (%s) for max_age', days)
            
# convert max age string to days. (max age can be written as : 2d for 'two days', etc)
        try:
            if max_age[-1:] == 'd':
                days = int(max_age[:-1])
            elif max_age[-1:] == 'w':
                days = int(max_age[:-1]) * 7
            elif max_age[-1:] == 'm':
                days = int(max_age[:-1]) * 30
            elif max_age[-1:] == 'y':
                days = int(max_age[:-1]) * 365
            else:
                days = int(max_age)
        except ValueError:
            self.error("Could not convert %s to a valid number of days."%max_age)
            days = 0
        
        self.debug('max age : %s => %s days'%(max_age, days))
        
        # force max age to be at least one day
        if days != 0 and days < 1:
            self._max_age_in_days = 1
        else:
            self._max_age_in_days = days

        try:
            max_age_cmd = self.config.get('purge', 'max_age_cmd')
        except:
            days_cmd = 0
            self.debug('Using default value (%s) for max_age_cmd', days_cmd)
            
# convert max age string to days. (max age can be written as : 2d for 'two days', etc)
        try:
            if max_age_cmd[-1:] == 'd':
                days_cmd = int(max_age_cmd[:-1])
            elif max_age_cmd[-1:] == 'w':
                days_cmd = int(max_age_cmd[:-1]) * 7
            elif max_age_cmd[-1:] == 'm':
                days_cmd = int(max_age_cmd[:-1]) * 30
            elif max_age_cmd[-1:] == 'y':
                days_cmd = int(max_age_cmd[:-1]) * 365
            else:
                days_cmd = int(max_age_cmd)
        except ValueError:
            self.error("Could not convert %s to a valid number of days."%max_age_cmd)
            days_cmd = 0
        
        self.debug('max age cmd : %s => %s days'%(max_age_cmd, days_cmd))
        
        # force max age to be at least one day
        if days_cmd != 0 and days_cmd < 1:
            self._max_age_cmd_in_days = 1
        else:
            self._max_age_cmd_in_days = days_cmd

        
        try:
            self._hours = self.config.getint('purge', 'hour')
            if self._hours < 0:
                self._hours = 0
            elif self._hours > 23:
                self._hours = 23
        except:
            self._hours = 0
            self.debug('Using default value (%s) for hours', self._hours)
            
        try:
            self._minutes = self.config.getint('purge', 'min')
            if self._minutes < 0:
                self._minutes = 0
            elif self._minutes > 59:
                self._minutes = 59
        except:
            self._minutes = 0
            self.debug('Using default value (%s) for minutes', self._minutes)
        
        if (self._max_age_in_days != 0) or (self._max_age_cmd_in_days != 0):
            # Get time_zone from main B3 config
            tzName = self.console.config.get('b3', 'time_zone').upper()
            tzOffest = b3.timezones.timezones[tzName]
            hoursGMT = (self._hours - tzOffest)%24
            self.debug("%02d:%02d %s => %02d:%02d UTC" % (self._hours, self._minutes, tzName, hoursGMT, self._minutes))
            self.info('everyday at %2d:%2d %s, chat messages older than %s days will be deleted'%(self._hours, self._minutes, tzName, self._max_age_in_days))
            self.info('everyday at %2d:%2d %s, chat commands older than %s days will be deleted'%(self._hours, self._minutes, tzName, self._max_age_cmd_in_days))
            self._cronTab = b3.cron.PluginCronTab(self, self.purge, 0, self._minutes, hoursGMT, '*', '*', '*')
            self.console.cron + self._cronTab
        else:
            self.info("chat log messages are kept forever")
            
    
    def startup(self):
        """\
        Initialize plugin settings
        """
        
        # listen for client events
        self.registerEvent(self.console.getEventID('EVT_CLIENT_SAY'))
        self.registerEvent(self.console.getEventID('EVT_CLIENT_TEAM_SAY'))
        self.registerEvent(self.console.getEventID('EVT_CLIENT_PRIVATE_SAY'))
        self.registerEvent(self.console.getEventID('EVT_ADMIN_COMMAND'))



    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if not event.client or event.client.cid == None or len(event.data) <= 0:
            return
        
        if event.type == b3.events.EVT_CLIENT_SAY:
            chat = ChatData(self, event)
            chat._table = self._db_table
            chat.save()
        if event.type == b3.events.EVT_CLIENT_TEAM_SAY:
            chat = TeamChatData(self, event)
            chat._table = self._db_table
            chat.save()
        if event.type == b3.events.EVT_CLIENT_PRIVATE_SAY:
            chat = PrivateChatData(self, event)
            chat._table = self._db_table
            chat.save()
        if event.type == b3.events.EVT_ADMIN_COMMAND:
            cmd = CmdData(self, event)
            cmd._table = self._db_table_cmdlog
            cmd.save()
 
    def purge(self):
        if self._max_age_in_days and (self._max_age_in_days != 0):
            self.info('purge of chat messages older than %s days ...'%self._max_age_in_days)
            q = "DELETE FROM %s WHERE msg_time < %i"%(self._db_table, self.console.time() - (self._max_age_in_days*24*60*60)) 
            self.debug(q)
            cursor = self.console.storage.query(q)
            #self.debug('cursor : %s'%cursor)
        else:
            self.warning('max_age is invalid [%s]'%self._max_age_in_days)

        if self._max_age_cmd_in_days and (self._max_age_cmd_in_days != 0):
            self.info('purge of commands older than %s days ...'%self._max_age_cmd_in_days)
            q = "DELETE FROM %s WHERE cmd_time < %i"%(self._db_table_cmdlog, self.console.time() - (self._max_age_cmd_in_days*24*60*60))
            self.debug(q)
            cursor = self.console.storage.query(q)
        else:
            self.warning('max_age_cmd is invalid [%s]'%self._max_age_cmd_in_days)

        
class AbstractData(object):

    def __init__(self, plugin):
        #default name of the table for this data object
        self._table = None
        self.plugin = plugin

    def _insertquery(self):
            raise NotImplementedError

    def save(self):
            """should call self._save2db with correct parameters"""
            raise NotImplementedError

    def _save2db(self, data):
        q = self._insertquery()
        try:
            cursor = self.plugin.console.storage.query(q, data)
            if (cursor.rowcount > 0):
                self.plugin.debug("rowcount: %s, id:%s" % (cursor.rowcount, cursor.lastrowid))
            else:
                self.plugin.warning("inserting into %s failed" % self._table)
        except Exception, e:
            if e[0] == 1146:
                self.plugin.error("Could not save to database : %s" % e[1])
                self.plugin.info("Refer to this plugin readme file for instruction on how to create the required tables")
            else:
                raise e


class CmdData(AbstractData):

    def __init__(self, plugin, event):
        AbstractData.__init__(self, plugin)
        #default name of the table for this data object
        self._table = 'cmdlog'

        self.admin_id = event.client.id
        self.admin_name = event.client.name

        self.command = event.data[0]
        self.data = event.data[1]
        self.result = event.data[2]
        self.event = event

    def _insertquery(self):
        return """INSERT INTO {table_name}
             (cmd_time, admin_id, admin_name, command, data, result)
             VALUES (%(time)s, %(admin_id)s, %(admin_name)s, %(command)s, %(data)s, %(result)s) """.format(table_name=self._table)

    def save(self):
        self.plugin.debug("%s, %s, %s, %s, %s" % (self.admin_id, self.admin_name, self.command, self.data, self.result))
        data = {'time':self.plugin.console.time(), 
         'admin_id': self.admin_id, 
         'admin_name': self.admin_name, 
         'command': self.command.command,
         'data': self.data,
         'result': self.result
         }
        if self.plugin._save2db:
            self._save2db(data)

        
class ChatData(AbstractData):
    
    #fields of the table
    msg_type = 'ALL' # ALL, TEAM or PM
    client_id = None
    client_name = None
    client_team = None
    msg = None
    
    def __init__(self, plugin, event):
        AbstractData.__init__(self, plugin)
        #default name of the table for this data object
        self._table = 'chatlog'

        self.client_id = event.client.id
        self.client_name = event.client.name
        self.client_team = event.client.team
        self.msg = event.data
        self.target_id = None
        self.target_name = None
        self.target_team = None
        
    def _insertquery(self):
        return """INSERT INTO {table_name} 
            (msg_time, msg_type, client_id, client_name, client_team, msg, target_id, target_name, target_team) 
            VALUES (%(time)s, %(type)s, %(client_id)s, %(client_name)s, %(client_team)s, %(msg)s, %(target_id)s, 
            %(target_name)s, %(target_team)s )""".format(table_name=self._table)
                
    def save(self):
        self.plugin.debug("%s, %s, %s, %s"% (self.msg_type, self.client_id, self.client_name, self.msg))
        data = {'time':self.plugin.console.time(), 
         'type': self.msg_type, 
         'client_id': self.client_id, 
         'client_name': self.client_name, 
         'client_team': self.client_team,
         'msg': self.msg,
         'target_id': self.target_id, 
         'target_name': self.target_name, 
         'target_team': self.target_team,
         }
        
        if self.plugin._save2file:
            self._save2file(data)
        if self.plugin._save2db:
            self._save2db(data)

    def _save2file(self, data):
        self.plugin.debug("writing to file")
        self.plugin._filelogger.info("@%(client_id)s [%(client_name)s] to %(type)s:\t%(msg)s" % data)


class TeamChatData(ChatData):
    msg_type = 'TEAM'
    
    
class PrivateChatData(ChatData):
    msg_type = 'PM'
    
    def __init__(self, plugin, event):
        ChatData.__init__(self, plugin, event)
        self.target_id = event.target.id
        self.target_name = event.target.name
        self.target_team = event.target.team
        



if __name__ == '__main__':
    import MySQLdb
    from b3.fake import FakeClient, fakeConsole, joe, simon
    from b3.storage import DatabaseStorage

    db = MySQLdb.connect(host='localhost', user='b3test', passwd='test')
    db.query("DROP DATABASE IF EXISTS b3_test")
    db.query("CREATE DATABASE b3_test CHARACTER SET utf8;")
    
    fakeConsole.storage = DatabaseStorage("mysql://b3test:test@localhost/b3_test", fakeConsole)
    fakeConsole.storage.executeSql("@b3/sql/b3.sql")
    fakeConsole.storage.query("""CREATE TABLE `chatlog` (
        `id` int(11) unsigned NOT NULL auto_increment,
        `msg_time` int(10) unsigned NOT NULL,
        `msg_type` enum('ALL','TEAM','PM') NOT NULL,
        `client_id` int(11) unsigned NOT NULL,
        `client_name` varchar(32) NOT NULL,
        `client_team` tinyint(1) NOT NULL,
        `msg` varchar(528) NOT NULL,
        `target_id` int(11) unsigned default NULL,
        `target_name` varchar(32) default NULL,
        `target_team` tinyint(1) default NULL,
        PRIMARY KEY    (`id`),
        KEY `client` (`client_id`)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8;""")
    fakeConsole.storage.query("""CREATE TABLE `cmdlog` (
        `id` int(11) unsigned NOT NULL auto_increment,
        `cmd_time` int(10) unsigned NOT NULL,
        `admin_id` int(11) unsigned NOT NULL,
        `admin_name` varchar(32) NOT NULL,
        `command` varchar(100) NULL,
        `data` varchar(528) default NULL,
        `result` varchar(528) default NULL,
        PRIMARY KEY (`id`),
        KEY `client` (`admin_id`)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8;""")

    def sendsPM(self, msg, target):
        print "\n%s PM to %s : \"%s\"" % (self.name, msg, target)
        self.console.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_PRIVATE_SAY, msg, self, target))
    FakeClient.sendsPM = sendsPM

    conf1 = b3.config.XmlConfigParser()
    conf1.loadFromString("""
    <configuration plugin="chatlogger">

        <settings name="general">
         <!-- do you want to save chat log to database ? -->
         <set name="save_to_database">Yes</set>
         
         <!-- do you want to save chat log to a file ? -->
         <set name="save_to_file">no</set>
            </settings>
    
        <settings name="file">
            <!-- location of the chat log file -->
            <set name="logfile">@conf/chat.log</set>
            <!-- file rotation rate. Can be either :
                H : every hour
                D : every day
                W0 : every monday
                W1 : every tuesday
                W6 : every sunday
             -->
                <set name="rotation_rate">D</set>
        </settings>
    
        <!-- optionally you can choose a different name for the table used 
        to store the log. Default is 'chatlog'. To do so, uncomment the 
        following part: -->
        <!--<settings name="database">
            <set name="db_table">chatlog2</set>
        </settings>-->
            
            <settings name="purge">
                <!-- how long (in days) do you want the history to be kept for. 
                    0 : keep chat log history for ever (default value)
                    You can use the following syntax as well
                    3d : purge all chat older than 3 days
                    2w : two weeks
                    6m : six month
                    1y : one year
                -->
                <set name="max_age">0</set>

                <!-- The purge action takes place once a day at the time define below.
                Default time is midnight -->
                <set name="hour">0</set>
                <!-- hour between 0 and 23 -->
                <set name="min">0</set>
                <!-- min between 0 and 59 -->
            </settings>
    </configuration>
    """)
    p = ChatloggerPlugin(fakeConsole, conf1)
    p.onLoadConfig()
    p.onStartup()
    
    joe.connects(1)
    simon.connects(3)
    
    joe.says("sql injec;tion ' test")
    joe.sendsPM("sql; injection ' test", simon)
    joe.says("!help sql injection ' test;")
    
    joe.name = "j'oe"
    simon.name = "s;m'n"
    joe.says("sql injection test2")
    joe.sendsPM("sql injection test2", simon)
    joe.says("!help sql injection test2")
    
    joe.name = "Joe"
    simon.name = "Simon"
    
    while True:
        joe.says("hello")
        simon.says2team("team test")
        joe.sendsPM("PM test", simon)
        simon.says("!help test command")
        
        time.sleep(20)
