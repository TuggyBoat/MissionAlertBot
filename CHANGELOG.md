# Changelog

## 2.1.1

- Removed channel_cleanup table from missions.db and related code
- Fixed incorrect timer for final channel deletion


## 2.1.0

Refactoring:

- Split `MissionGenerator.py` into `MissionGenerator.py` and `MissonCleaner.py`
- Major changes to the internal structure of the mission generator
    - Misison generation is now more resilient to errors and communicates better when something goes wrong
- Added `Commodities.py` in preparation for adding a method to build the Commodities database from scratch
- Added custom errors for interaction role and channel checks, and called them via the global error handler
- More errors handled elegantly
- More helpful notifications to bot-spam
- Many bot-spam messages converted to embeds
- Many response messages converted to embeds
- Many small changes here and there

Removed commands:
- `loadlegacy`, `unloadlegacy` have been removed
- legacy support has been removed
- `loadrp`, `unloadrp` have been removed

Changed commands:
- `load` and `unload` are now `/cco load` and `/cco unload` respectively
    - added describes to all parameters
    - added autocomplete for common commodities and pad size
    - ETA and RP text have been merged into the new "Message" feature:
        - "Message" is entered via Modal and sent to Discord destinations in a separate embed
    - buttons or select menu options for sends, replacing chat letter entry
        - note **you can SCROLL the select menu** to reveal additional options
    - added icons for send status embeds
    - completely new embed format for Discord
    - added ability to send via webhook
    - tweaks to Reddit format
    - demand/supply is now entered as an int/float (i.e. without the "k"), and is subject to validation
- `done` is now `/cco complete`. `/cco done` remains as an alias, for now
    - `/cco complete` now has optional parameters for whether the mission was `Completed` or `Failed`, with autocomplete, as well as for an explanation message
        - by default, status is assumed to be `Completed`
    - many small changes to how `/cco complete` reports
- `carrier_image` is now `/cco image`
- `m.complete` is now `/mission complete`
    - no more option to add a message as an argument
    - button menu asks user whether mission completed or cannot be completed
    - clicking unable to complete prompts user for an explanation message
- `/mission` is now `/mission information`
- `m.unlock_override` deletion check temporarily disabled.

New commands:
- `/cco webhook add` - CCO only - used to add a webhook to that CCO's personal list
- `/cco webhook view` - CCO only - shows their webhooks
- `/cco webhook delete` - CCO only - used to remove a webhook from their list
- `/cco edit` - CCO only - used to edit an in-progress mission. Presently only the original interaction parameters can be edited (i.e. the fields added via slash command). Editing message and mission type will be implemented in a future update.
- `/admin_delete_mission` - Admin only - used to manually remove a mission from the database (without cleanup). Intended for unresolvable error situations only.
- added **training mode** to `/cco load` and `/cco unload`. This will not affect webhooks but will send discord alerts to the new training channels, and reddit posts to the testing subreddit. Webhooks will be sent as normal, but it's expected trainees will add a training webhook anyway.

Other:
- When channel deletion is in its final 10 second countdown, a notice will appear in the mission-generator to warn that deletion is in progress and the channel lock is acquired. It is strongly advised not to attempt to "send" missions during this brief window. The message is removed once the lock is released.
- Automatically update PTN logos used by the bot during June.


## 2.0.0

Refactoring:

- Refactored the bot into standardised directory structure
- Refactored commands into Cogs
- Refactored auxiliary functions into modules
- New global error handlers for interactions and text commands respectively
- Implemented setup.py, the bot is now installed via `pip install -e.`
- Cleaned up requirements
- Removed interaction sync listener, replaced with command
    - sync is a high intensity action, best practice is to only do it when needed
- Added persistant data directory for use when containerised
    - this contains all carrier images, carrier backup images, and community channel images, as well as all database, database dump, and database backups
- Many small improvements to code
- Many, many more improvements to do

New environment variables:

- `PTN_MAB_DATA_DIR` - specifies the path to the `/data` directory where the bot stores all mutable files (databases, carrier images, community channel thumbnails)
- `PTN_MAB_RESOURCE_DIR` - specifies the path to the `/resource` directory which houses static non-Python files (default carrier images, mission template images, edmc off images, and fonts)

New commands:

- `/greet` - functionally identical to m.ping but as a slash command
- `m.sync` - syncs interactions with the server
    - this has to be done any time an interaction is added, removed, or has its definition changed

Changed commands

- `nom_count` is now `/cp_nominees_list`, and is ephemeral with the option to broadcast to channel
- `nom_delete` is now `/cp_delete_nominee_from_database`, and uses button confirmations
- `nom_details` is now `/cp_nomination_details`, and is ephemeral with the option to broadcast to channel
- `carrier_add` is now `/carrier_add`
- `carrier_delete` is now `/carrier_delete`, and uses button confirmations
- many slash commands have had descriptions added to their parameters
- mission generator returnflag has been (temporarily) removed, making error recovery less graceful (but still robust)
- some commands which usually take a while now have a "MissionAlertBot is typing..." status
    - this is in the experimental stages and needs to be properly tweaked