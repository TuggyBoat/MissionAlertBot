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
            );INSERT INTO "missions" VALUES('P.T.N TESTER','123-456',843245964709199932,'Silver','load','Leesti','George Lucas',20,'M','25k','Hi commanders! Have fun with this! - *CMDR MANBOYCHILD*','nda7bl','/r/PTNBotTesting/comments/nda7bl/ptn_news_trade_mission_ptn_tester_123456_15_may/','gy9gwrn','/r/PTNBotTesting/comments/nda7bl/ptn_news_trade_mission_ptn_tester_123456_15_may/gy9gwrn/',843254297134628896);COMMIT;