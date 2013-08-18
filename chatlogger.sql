
CREATE TABLE `chatlog` (
  `id` int(11) unsigned NOT NULL auto_increment,
  `msg_time` int(10) unsigned NOT NULL,
  `msg_type` enum('ALL','TEAM','PM','SQUAD') NOT NULL,
  `client_id` int(11) unsigned NOT NULL,
  `client_name` varchar(32) NOT NULL,
  `client_team` tinyint(1) NOT NULL,
  `msg` varchar(528) NOT NULL,
  `target_id` int(11) unsigned default NULL,
  `target_name` varchar(32) default NULL,
  `target_team` tinyint(1) default NULL,
  PRIMARY KEY  (`id`),
  KEY `client` (`client_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `cmdlog` (
  `id` int(11) unsigned NOT NULL auto_increment,
  `cmd_time` int(10) unsigned NOT NULL,
  `admin_id` int(11) unsigned NOT NULL,
  `admin_name` varchar(32) NOT NULL,
  `command` varchar(100) NULL,
  `data` varchar(528) default NULL,
  `result` varchar(528) default NULL,
  PRIMARY KEY (`id`),
  KEY `client` (`admin_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

