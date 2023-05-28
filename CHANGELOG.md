# Changelog

## 2.0.0

Refactoring:

- Refactored the bot into standardised directory structure
- Refactored commands into Cogs
- Refactored auxiliary functions into modules
- New global error handlers for interactions and text commands respectively
- Implemented setup.py, the bot is now installed via `pip install -e.`
- Cleaned up requirements
- Added persistant data directory for use when containerised
    - this contains all carrier images, carrier backup images, and community channel images, as well as all database, database dump, and database backups
- Many small improvements to code
- Many, many more improvements to do

New commands:

- `/greet` - functionally identical to m.ping but as a slash command

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