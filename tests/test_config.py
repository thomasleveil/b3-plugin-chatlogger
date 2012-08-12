import logging
import unittest
from mock import Mock
from mockito import when
import sys

import b3
from chatlogger import ChatloggerPlugin
from b3.config import XmlConfigParser

from tests import B3TestCase
from chatlogger import __file__ as chatlogger__file__
import os

CHATLOGGER_CONFIG_FILE = os.path.join(os.path.dirname(chatlogger__file__), 'conf/plugin_chatlogger.xml')


class Test_Config(B3TestCase):

    def setUp(self):
        self.log = logging.getLogger('output')
        self.log.propagate = False

        B3TestCase.setUp(self)
        self.console.startup()
        self.log.propagate = True
        self.log.setLevel(logging.DEBUG)

        self.conf = XmlConfigParser()
        self.p = ChatloggerPlugin(self.console, self.conf)

        when(self.console.config).get('b3', 'time_zone').thenReturn('GMT')
        when(b3).getB3Path().thenReturn("c:\\b3_folder")
        when(b3).getConfPath().thenReturn("c:\\b3_conf_folder")
        self.p.setup_fileLogger = Mock()


    def init(self, config_content=None):
        """ load plugin config and initialise the plugin """
        if config_content:
            self.conf.loadFromString(config_content)
        else:
            if os.path.isfile(CHATLOGGER_CONFIG_FILE):
                self.conf.load(CHATLOGGER_CONFIG_FILE)
            else:
                unittest.skip("default config file '%s' does not exists" % CHATLOGGER_CONFIG_FILE)
                return
        self.p.onLoadConfig()
        self.p.onStartup()


    def test_default_config(self):
        self.init()
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
        self.init("""<configuration plugin="chatlogger" />""")
        self.assertTrue(self.p._save2db)
        self.assertFalse(self.p._save2file)
        self.assertIsNone(self.p._file_name)
        self.assertIsNone(self.p._file_rotation_rate)
        self.assertEqual(0, self.p._max_age_in_days)
        self.assertEqual(0, self.p._max_age_cmd_in_days)
        self.assertEqual(0, self.p._hours)
        self.assertEqual(0, self.p._minutes)


    def test_conf1(self):
        self.init("""
            <configuration plugin="chatlogger">
                <settings name="purge">
                    <set name="max_age">7d</set>
                    <set name="hour">4</set>
                    <set name="min">0</set>
                </settings>
            </configuration>
        """)
        self.assertTrue(self.p._save2db)
        self.assertFalse(self.p._save2file)
        self.assertIsNone(self.p._file_name)
        self.assertIsNone(self.p._file_rotation_rate)
        self.assertEqual(7, self.p._max_age_in_days)
        self.assertEqual(0, self.p._max_age_cmd_in_days)
        self.assertEqual(4, self.p._hours)
        self.assertEqual(0, self.p._minutes)
