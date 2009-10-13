chatlogger plugin for Big Brother Bot (www.bigbrotherbot.com)
=============================================================

By #UbU#Courgette


Description
-----------

This plugin logs to database all clients' messages (chat, team chat, private chat).
Forum : http://www.bigbrotherbot.com/forums/index.php?topic=423


Installation
------------

 * copy chatlogger.py into b3/extplugins
 * copy plugin_chatlogger.xml into b3/extplugins/conf
 * create the chatlog table in your database importing the chatlogger.sql file.
 * update your main b3 config file with :
<plugin name="chatlogger" priority="18" config="@b3/extplugins/conf/plugin_chatlogger.xml"/>

NOTE : if you are using the censor plugin, make sure the priority of the chatlogger plugin is less
than the priority of the censor plugin or you won't log any messages containing censored words.

Changelog
---------

28/07/2008 - 0.0.1
 - manage say, teamsay and privatesay messages
 
14/08/2008 - 0.1.0
 - fix security issue with player names or messages containing double quote or antislash characters (Thx to Anubis for report and tests)
 - option to setup a daily purge of old messages to keep your database size reasonable
 
13/09/2008 - 0.1.1
 - in config, the hour defined for the purge is now understood in the timezone defined in the main B3 config file (before, was understood as UTC time)
 - fix mistake in log text

7/11/2008 - 0.1.2 - xlr8or
 - added missing 'import b3.timezones'

22/12/2008 - 0.2.0 - Courgette
 - allow to use a customized table name for storing the
   log to database. Usefull if multiple instances of the
   bot share the same database.
   Thanks to Eire.32 for bringing up the idea and testing.