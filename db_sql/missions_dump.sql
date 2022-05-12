BEGIN TRANSACTION;CREATE TABLE missions(
            "carrier"	TEXT NOT NULL UNIQUE,
            "cid"	TEXT,
            "channelid"	INTEGER,
            "commodity"	TEXT,
            "missiontype"	TEXT,
            "system"	TEXT NOT NULL,
            "station"	TEXT,
            "profit"	INTEGER,
            "pad"	TEXT,
            "demand"    TEXT,
            "rp_text"	TEXT,
            "reddit_post_id"	TEXT,
            "reddit_post_url"	TEXT,
            "reddit_comment_id"	TEXT,
            "reddit_comment_url"	TEXT,
            "discord_alert_id"	INT
            );INSERT INTO "missions" VALUES('P.T.N. ALPHABET MAFIA','H8B-84Y',974183507968532560,'Agronomic Treatment','load','Leesti','George Lucas',12,'L','20k','Due to Leesti being a busy system we have had to park on Leesti 2 meaning it is a 291Ls travel distance. If a slot becomes available we will micro jump closer.','untwe1','/r/PilotsTradeNetwork/comments/untwe1/ptn_news_trade_mission_ptn_alphabet_mafia_h8b84y/','i8a96jo','/r/PilotsTradeNetwork/comments/untwe1/ptn_news_trade_mission_ptn_alphabet_mafia_h8b84y/i8a96jo/',974183603120521246);INSERT INTO "missions" VALUES('P.T.N STORM WARNING','T5H-LQN',974183756841766952,'Agronomic Treatment','load','Leesti','George Lucas',12,'L','23k','Due to Leesti being a busy system we have had to park on Leesti 2 meaning it is a 291Ls travel distance. If a slot becomes available we will micro jump closer.','untwv7','/r/PilotsTradeNetwork/comments/untwv7/ptn_news_trade_mission_ptn_storm_warning_t5hlqn/','i8a99de','/r/PilotsTradeNetwork/comments/untwv7/ptn_news_trade_mission_ptn_storm_warning_t5hlqn/i8a99de/',974183830862852136);INSERT INTO "missions" VALUES('P.T.N. SKY CORPS','HLQ-L9Q',974342825632235560,'Indite','load','Brani','Wundt Hub',20,'L','22k',NULL,'uo4m9i','/r/PilotsTradeNetwork/comments/uo4m9i/ptn_news_trade_mission_ptn_sky_corps_hlql9q_12/','i8c1h8e','/r/PilotsTradeNetwork/comments/uo4m9i/ptn_news_trade_mission_ptn_sky_corps_hlql9q_12/i8c1h8e/',974342843940339783);INSERT INTO "missions" VALUES('PTN SNOWY SUMMIT','H7F-0XZ',974390511102197770,'Wine','load','Niaba','Alten Orbital',5,'L','21K',NULL,NULL,NULL,NULL,NULL,974390539870945300);COMMIT;