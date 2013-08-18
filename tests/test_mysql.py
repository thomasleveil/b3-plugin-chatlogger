# coding: utf-8
import logging
import os
from textwrap import dedent
import unittest
from mock import Mock
from mockito import when
from chatlogger import ChatloggerPlugin
from b3 import TEAM_RED, TEAM_BLUE
from b3.config import CfgConfigParser
from b3.storage import DatabaseStorage
import b3.events
from chatlogger import __file__ as chatlogger__file__
from tests import B3TestCase, logging_disabled


"""
    NOTE: to work properly you must be running a MySQL database on localhost
    which must have a user named 'b3test' with password 'test' which has
    all privileges over a table (already created or not) named 'b3_test'
"""
MYSQL_HOST = 'localhost'
MYSQL_USER = 'b3test'
MYSQL_PASSWORD = 'test'
MYSQL_DB = 'b3_test'

#===============================================================================
#
# check if we can run the MySQL tests
#
#===============================================================================

is_mysql_ready = True
no_mysql_reason = ''

try:
    import MySQLdb
except ImportError:
    is_mysql_ready = False
    no_mysql_reason = "no MySQLdb module available"
else:
    try:
        MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD)
    except MySQLdb.Error, err:
        is_mysql_ready = False
        no_mysql_reason = "%s" % err[1]
    except Exception, err:
        is_mysql_ready = False
        no_mysql_reason = "%s" % err

CHATLOGGER_CONFIG_FILE = os.path.join(os.path.dirname(chatlogger__file__), 'conf/plugin_chatlogger.ini')
CHATLOGGER_SQL_FILE = os.path.join(os.path.dirname(chatlogger__file__), '../chatlogger.sql')

with logging_disabled():
    from b3.fake import FakeClient

    def sendsPM(self, msg, target):
        print "\n%s PM to %s : \"%s\"" % (self.name, msg, target)
        self.console.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_PRIVATE_SAY, msg, self, target))

    FakeClient.sendsPM = sendsPM


@unittest.skipIf(not is_mysql_ready, no_mysql_reason)
class Test_mysql(B3TestCase):
    def setUp(self):
        B3TestCase.setUp(self)
        logging.getLogger('output').setLevel(logging.DEBUG)
        with logging_disabled():
            self.console.startup()
            self.conf = CfgConfigParser()
            self.p = ChatloggerPlugin(self.console, self.conf)

        ## prepare the mysql test database
        db = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD)
        db.query("DROP DATABASE IF EXISTS %s" % MYSQL_DB)
        db.query("CREATE DATABASE %s CHARACTER SET utf8;" % MYSQL_DB)

        self.console.storage = DatabaseStorage(
            'mysql://%s:%s@%s/%s' % (MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB), self.console)
        self.console.storage.executeSql("@b3/sql/b3.sql")
        self.console.storage.executeSql(CHATLOGGER_SQL_FILE)

        when(self.console.config).get('b3', 'time_zone').thenReturn('GMT')
        self.p.setup_fileLogger = Mock()

        self.conf.loadFromString(dedent("""
            [general]
            save_to_database: Yes
            save_to_file: no

            [file]
            logfile: @conf/chat.log
            rotation_rate: D

            [purge]
            max_age: 0
            hour: 0
            min: 0
        """))
        with logging_disabled():
            self.p.onLoadConfig()
            self.p.onStartup()
            self.joe = FakeClient(self.console, name="Joe", guid="joe_guid", team=TEAM_RED)
            self.simon = FakeClient(self.console, name="Simon", guid="simon_guid", team=TEAM_BLUE)
            self.joe.connects(1)
            self.simon.connects(3)

        self.assertEqual(0, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())

    def count_chatlog_lines(self):
        cursor = self.console.storage.query("select count(*) as `count` from chatlog")
        count = cursor.getValue("count")
        cursor.close()
        return count

    def count_cmdlog_lines(self):
        cursor = self.console.storage.query("select count(*) as `count` from cmdlog")
        count = cursor.getValue("count")
        cursor.close()
        return count

    def get_all_chatlog_lines_from_db(self):
        cursor = self.console.storage.query("select msg_type, client_id, client_name, client_team, msg, target_id, "
                                            "target_name, target_team from chatlog")
        lines = []
        if cursor:
            while not cursor.EOF:
                lines.append(cursor.getRow())
                cursor.moveNext()
            cursor.close()
        return lines

    def get_all_cmdlog_lines_from_db(self):
        cursor = self.console.storage.query("select admin_id, admin_name, command, data, result from cmdlog")
        lines = []
        if cursor:
            while not cursor.EOF:
                lines.append(cursor.getRow())
                cursor.moveNext()
            cursor.close()
        return lines

    def test_global_chat_gets_saved_to_db(self):
        # WHEN
        self.joe.says("hello")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())
        self.assertDictEqual({'client_id': 1,
                              'client_name': 'Joe',
                              'client_team': TEAM_RED,
                              'msg': 'hello',
                              'msg_type': 'ALL',
                              'target_id': None,
                              'target_name': None,
                              'target_team': None},
                             self.get_all_chatlog_lines_from_db()[0])

    def test_team_chat_gets_saved_to_db(self):
        # WHEN
        self.joe.says2team("hi")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())
        self.assertDictEqual({'client_id': self.joe.id,
                              'client_name': 'Joe',
                              'client_team': self.joe.team,
                              'msg': 'hi',
                              'msg_type': 'TEAM',
                              'target_id': None,
                              'target_name': None,
                              'target_team': None},
                             self.get_all_chatlog_lines_from_db()[0])

    @unittest.skipUnless(hasattr(FakeClient, "says2squad"), "FakeClient.says2squad not available in this version of B3")
    def test_squad_chat_gets_saved_to_db(self):
        # WHEN
        self.joe.says2squad("hi")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())
        self.assertDictEqual({'client_id': self.joe.id,
                              'client_name': 'Joe',
                              'client_team': self.joe.team,
                              'msg': 'hi',
                              'msg_type': 'SQUAD',
                              'target_id': None,
                              'target_name': None,
                              'target_team': None},
                             self.get_all_chatlog_lines_from_db()[0])

    def test_private_chat_gets_saved_to_db(self):
        # WHEN
        self.joe.sendsPM("hi", self.simon)
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())
        self.assertDictEqual({'client_id': self.joe.id,
                              'client_name': 'Joe',
                              'client_team': self.joe.team,
                              'msg': 'hi',
                              'msg_type': 'PM',
                              'target_id': self.simon.id,
                              'target_name': "Simon",
                              'target_team': self.simon.team},
                             self.get_all_chatlog_lines_from_db()[0])

    def test_command_gets_saved_to_db(self):
        # WHEN
        self.joe.says("!help")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assertEqual(1, self.count_cmdlog_lines())
        self.assertDictEqual({'client_id': self.joe.id,
                              'client_name': 'Joe',
                              'client_team': self.joe.team,
                              'msg': '!help',
                              'msg_type': 'ALL',
                              'target_id': None,
                              'target_name': None,
                              'target_team': None},
                             self.get_all_chatlog_lines_from_db()[0])
        self.assertDictEqual({'admin_id': 1,
                              'admin_name': 'Joe',
                              'command': 'help',
                              'data': '',
                              'result': None},
                             self.get_all_cmdlog_lines_from_db()[0])

    def test_unicode(self):
        # WHEN
        self.joe.name = u"★joe★"
        self.simon.name = u"❮❮simon❯❯"
        self.joe.sendsPM(u"hi ✪", self.simon)
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())
        self.assertDictEqual({'client_id': self.joe.id,
                              'client_name': u"★joe★",
                              'client_team': self.joe.team,
                              'msg': u"hi ✪",
                              'msg_type': 'PM',
                              'target_id': self.simon.id,
                              'target_name': u"❮❮simon❯❯",
                              'target_team': self.simon.team},
                             self.get_all_chatlog_lines_from_db()[0])

    def test_sql_injection(self):
        # WHEN
        self.joe.says("sql injec;tion ' test")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())

        # WHEN
        self.joe.sendsPM("sql; injection ' test", self.simon)
        # THEN
        self.assertEqual(2, self.count_chatlog_lines())
        self.assertEqual(0, self.count_cmdlog_lines())

        # WHEN
        self.joe.says("!help sql injection ' test;")
        # THEN
        self.assertEqual(3, self.count_chatlog_lines())
        self.assertEqual(1, self.count_cmdlog_lines())

        # WHEN
        self.joe.name = "j'oe"
        self.joe.says("sql injection test2")
        # THEN
        self.assertEqual(4, self.count_chatlog_lines())
        self.assertEqual(1, self.count_cmdlog_lines())

        # WHEN
        self.joe.name = "joe"
        self.simon.name = "s;m'n"
        self.joe.sendsPM("sql injection test2", self.simon)
        # THEN
        self.assertEqual(5, self.count_chatlog_lines())
        self.assertEqual(1, self.count_cmdlog_lines())
