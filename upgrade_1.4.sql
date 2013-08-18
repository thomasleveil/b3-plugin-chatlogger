-- MySQL upgrade script for chatlogger v1.4
-- Adds 'SQUAD' to the msg_type possible values. Really only needed for games which have squads
ALTER TABLE `chatlog` MODIFY COLUMN `msg_type` ENUM('ALL','TEAM','PM','SQUAD') NOT NULL;

