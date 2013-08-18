# coding: utf-8
import logging
import os
import re
import codecs
from tempfile import mkdtemp
from textwrap import dedent
import unittest2 as unittest
from mockito import when
from chatlogger import ChatloggerPlugin
from b3 import TEAM_RED, TEAM_BLUE
from b3.config import CfgConfigParser
import b3.events
from chatlogger import __file__ as chatlogger__file__
from tests import B3TestCase, logging_disabled


CHATLOGGER_CONFIG_FILE = os.path.join(os.path.dirname(chatlogger__file__), 'conf/plugin_chatlogger.ini')

with logging_disabled():
    from b3.fake import FakeClient

    def sendsPM(self, msg, target):
        self.console.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_PRIVATE_SAY, msg, self, target))

    FakeClient.sendsPM = sendsPM


class Test_chatlogfile(B3TestCase):
    def setUp(self):
        B3TestCase.setUp(self)
        logging.getLogger('output').setLevel(logging.DEBUG)
        with logging_disabled():
            self.console.startup()
            self.conf = CfgConfigParser()
            self.p = ChatloggerPlugin(self.console, self.conf)

        when(self.console.config).get('b3', 'time_zone').thenReturn('GMT')

        self.conf.loadFromString(dedent("""
            [general]
            save_to_database: no
            save_to_file: yes

            [file]
            logfile: @conf/chat.log
            rotation_rate: D

            [purge]
            max_age: 0
            hour: 0
            min: 0
        """))
        self.temp_conf_folder = mkdtemp(suffix="b3_conf")
        when(b3).getConfPath().thenReturn(self.temp_conf_folder)
        with logging_disabled():
            self.p.onLoadConfig()
            self.p.onStartup()

        self.chat_log_file = os.path.join(self.temp_conf_folder, 'chat.log')

        with logging_disabled():
            self.joe = FakeClient(self.console, name="Joe", guid="joe_guid", team=TEAM_RED)
            self.simon = FakeClient(self.console, name="Simon", guid="simon_guid", team=TEAM_BLUE)
            self.joe.connects(1)
            self.simon.connects(3)

    def get_all_chatlog_lines_from_logfile(self):
        lines = []
        with codecs.open(self.chat_log_file, "r", encoding="utf-8") as f:
            for l in f.readlines():
                lines.append(l.strip())
        return lines

    def count_chatlog_lines(self):
        return len(self.get_all_chatlog_lines_from_logfile())

    def assert_log_line(self, line, expected):
        """
        remove time stamp at the beginning of the line and compare the remainder
        """
        clean_line = re.sub(r"^\d+-\d+-\d+ \d\d:\d\d:\d\d\t", "", line)
        self.assertEqual(clean_line, expected)

    def test_global_chat(self):
        # WHEN
        self.joe.says("hello")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assert_log_line(self.get_all_chatlog_lines_from_logfile()[0], "@1 [Joe] to ALL:\thello")

    def test_team_chat(self):
        # WHEN
        self.joe.says2team("hello")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assert_log_line(self.get_all_chatlog_lines_from_logfile()[0], "@1 [Joe] to TEAM:\thello")

    @unittest.skipUnless(hasattr(FakeClient, "says2squad"), "FakeClient.says2squad not available in this version of B3")
    def test_squad_chat(self):
        # WHEN
        self.joe.says2squad("hi")
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assert_log_line(self.get_all_chatlog_lines_from_logfile()[0], "@1 [Joe] to SQUAD:\thi")

    def test_private_chat(self):
        # WHEN
        self.joe.sendsPM("hi", self.simon)
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assert_log_line(self.get_all_chatlog_lines_from_logfile()[0], "@1 [Joe] to PM:\thi")

    def test_unicode(self):
        # WHEN
        self.joe.name = u"★joe★"
        self.simon.name = u"❮❮simon❯❯"
        self.joe.sendsPM(u"hi ✪", self.simon)
        # THEN
        self.assertEqual(1, self.count_chatlog_lines())
        self.assert_log_line(self.get_all_chatlog_lines_from_logfile()[0], u"@1 [★joe★] to PM:\thi ✪")

