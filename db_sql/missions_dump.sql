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
        );INSERT INTO "missions" VALUES('PTN STARSCAPE OLYMPUS','K8Y-T2G',801566562976399431,'Agronomic Treatment','unload','Test','Test',0,'M','0',NULL,NULL,NULL,NULL,NULL,NULL);COMMIT;