import logging
import unittest
import sys
import os
from textwrap import dedent
from mock import Mock
from mockito import when

import b3
from chatlogger import ChatloggerPlugin
from b3.config import CfgConfigParser
from tests import B3TestCase, logging_disabled
from chatlogger import __file__ as chatlogger__file__


CHATLOGGER_CONFIG_FILE = os.path.join(os.path.dirname(chatlogger__file__), '../conf/plugin_chatlogger.ini')


class Test_Config(B3TestCase):
    def setUp(self):
        B3TestCase.setUp(self)
        with logging_disabled():
            self.console.startup()

        logging.getLogger('output').setLevel(logging.DEBUG)

        self.conf = CfgConfigParser()
        self.p = ChatloggerPlugin(self.console, self.conf)

        when(self.console.config).get('b3', 'time_zone').thenReturn('GMT')
        self.p.setup_fileLogger = Mock()

    def init(self, config_content=None):
        """ load plugin config and initialise the plugin """
        if config_content:
            self.conf.loadFromString(config_content)
        else:
            if os.path.isfile(CHATLOGGER_CONFIG_FILE):
                self.conf.load(CHATLOGGER_CONFIG_FILE)
            else:
                raise unittest.SkipTest("default config file '%s' does not exists" % CHATLOGGER_CONFIG_FILE)
        self.p.onLoadConfig()
        self.p.onStartup()

    def test_default_config(self):
        # GIVEN
        when(b3).getB3Path().thenReturn("c:\\b3_folder")
        when(b3).getConfPath().thenReturn("c:\\b3_conf_folder")
        # WHEN
        self.init()
        # THEN
        self.assertTrue(self.p._save2db)
        self.assertTrue(self.p._save2file)
        expected_log_file = 'c:\\b3_conf_folder\\chat.log' if sys.platform == 'win32' else 'c:\\b3_conf_folder/chat.log'
        self.assertEqual(expected_log_file, self.p._file_name)
        self.assertEqual("D", self.p._file_rotation_rate)
        self.assertEqual(0, self.p._max_age_in_days)
        self.assertEqual(0, self.p._max_age_cmd_in_days)
        self.assertEqual(0, self.p._hours)
        self.assertEqual(0, self.p._minutes)

    def test_empty_config(self):
        self.init("""
        """)
        self.assertTrue(self.p._save2db)
        self.assertFalse(self.p._save2file)
        self.assertIsNone(self.p._file_name)
        self.assertIsNone(self.p._file_rotation_rate)
        self.assertEqual(0, self.p._max_age_in_days)
        self.assertEqual(0, self.p._max_age_cmd_in_days)
        self.assertEqual(0, self.p._hours)
        self.assertEqual(0, self.p._minutes)
        self.assertEqual("chatlog", self.p._db_table)
        self.assertEqual("cmdlog", self.p._db_table_cmdlog)

    def test_conf1(self):
        self.init(dedent("""
            [purge]
            max_age:7d
            hour:4
            min:0
        """))
        self.assertTrue(self.p._save2db)
        self.assertFalse(self.p._save2file)
        self.assertIsNone(self.p._file_name)
        self.assertIsNone(self.p._file_rotation_rate)
        self.assertEqual(7, self.p._max_age_in_days)
        self.assertEqual(0, self.p._max_age_cmd_in_days)
        self.assertEqual(4, self.p._hours)
        self.assertEqual(0, self.p._minutes)

    def test_database(self):
        self.init(dedent("""
            [database]
            db_table: chatlog2
            db_table_cmdlog: cmdlog2
        """))
        self.assertEqual("chatlog2", self.p._db_table)
        self.assertEqual("cmdlog2", self.p._db_table_cmdlog)
