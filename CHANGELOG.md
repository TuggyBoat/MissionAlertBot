# Changelog

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