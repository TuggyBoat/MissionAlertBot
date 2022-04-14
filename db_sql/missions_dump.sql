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
            );INSERT INTO "missions" VALUES('P.T.N. ACHILLES','XZF-5XZ',963141103639470152,'Agronomic Treatment','load','Leesti','Georg Lucas',12,'L','20k',NULL,'u1e5e1','/r/PilotsTradeNetwork/comments/u1e5e1/ptn_news_trade_mission_ptn_achilles_xzf5xz_11/','i4bpxvp','/r/PilotsTradeNetwork/comments/u1e5e1/ptn_news_trade_mission_ptn_achilles_xzf5xz_11/i4bpxvp/',963141122094424094);COMMIT;