
CREATE TABLE `chatlog` (
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
  PRIMARY KEY  (`id`),
  KEY `client` (`client_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
