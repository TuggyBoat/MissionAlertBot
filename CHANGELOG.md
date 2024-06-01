# Changelog

## 2.4.5
- Fix for WMM stock not grouping Inara carriers correctly due to bad capitalization on system names. (TuggyBoat)


## 2.4.4
- Updated `README.md` with testing instructions. (IndorilReborn)
- Message object will no longer be sent in place of channel ID if channel lock fails. (IndorilReborn)
- Relaxed pinned typing_extensions version. (IndorilReborn)
- Added filtering in commodity autocomplete. (IndorilReborn)
- WMM stock messages sorted according to (System, Station, Commodity). Minor refactoring. (IndorilReborn)
- [#691](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/691) Council Advisor role added to permissions. (TuggyBoat)
- [#688](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/688) `/stock` embed should now be a consistent width. (Sihmm)


## 2.4.3
- [#676](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/676) Fix for multi-word commodities not updating mission stock in alerts channel.
- [#674](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/674) Check for whether stock type (supply/demand) matches mission type (loading/unloading).
- [#670](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/670) Removed owner display name for mission channel MESSAGE embed, replaced with 'CARRIER OWNER'.
- [#668](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/668) Fix for order of checks/background tasks on startup, so background tasks should start at correct time.
- [#662](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/662) Added bot-spam notices for `/admin wmm start`, `/admin wmm stop`, `/admin wmm interval`, and `/cco wmm update`.


## 2.4.2
- [#665](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/665) Fixed WMM task breaking if carrier stock is low on two or more commodities


## 2.4.1
- Fixed reference to `;stock` in mission embed


## 2.4.0
Integrated stock tracking features from stockbot (with thanks to DudeInCorner and Durzo):
- `/stock`:
 - can be used in a carrier channel without parameters to check stock of that carrier.
 - can be used with carrier as a parameter to check stock for any carrier.
 - can optionally specify inara or capi as source; default is capi.
 - added information in footer as to stock source.
 - EDMC data notice is now context-sensitive:
   - EDMC notice will only show when source is 'inara'.
   - EDMC-off missions will show a reminder to disable EDMC, instead of the reminder to use it
- `/cco capi enable`: If capi auth is confirmed, will flag the carrier(s) as capi-enabled; otherwise, will send the target carrier owner a DM with OAuth link and explanation. Multiple carriers can be separated by commas.
- `/cco capi disable`: Will flag the carrier(s) as capi-disabled and prevent capi stock checks. Multiple carriers can be separated by commas.
- Adding carriers to Mission Alert Bot will no longer prompt the user to add to stockbot.

Integrated WMM tracking features from stockbot (with thanks to Durzo):
- WMM stock display in #wmm-stock and #cco-wmm-supplies.
- `/cco wmm enable`: Adds a carrier to WMM tracking; option to autocomplete station location from list.
- `/cco wmm disable`: Removes one or more carriers from WMM tracking. Multiple carriers can be separated by commas.
- `/cco wmm update`: Trigger manual refresh of all WMM stock.
- `/admin wmm status`: Check the status of the WMM background task; now shows time remaining until next loop, as well as current interval time.
- `/admin wmm stop`: Stop the WMM background task.
- `/admin wmm start`: Start or restart the WMM background task.
- `/admin wmm interval`: Set the WMM update interval in minutes.
- `m.wmm_list`: List active WMM carriers.

Other:
- `/carrier add` and `Add Carrier` no longer offer StockBot code for `;add_FC`.
- `/carrier add` no longer has a shortname field; all shortnames are now generated internally by MAB.
- `/carrier add` can now be used in #CCO-general-chat
- Changed references to `;stock <shortname>` to `/stock`.
- Removed shortname as a user-facing variable.
- Added cAPI status to carrier info embeds.
- Trade Alerts will now include updated supply/demand remaining if a user uses `/stock` for a carrier on a mission.
- Updated web links for loading/unloading images so Discord will finally stock mocking me with cached images from 3 months ago.
- `/admin capi_sync`: Intended for first run after StockBot migration: updates CAPI status for all registered PTN Fleet Carriers.
- Added initial `settings.txt` with option to disable WMM auto start and specific some command IDs; for now, only `/stock` is implemented:
 - `/admin settings view` to view settings.txt;
 - `/admin settings change` to change a setting in the file.


## 2.3.9
- Add author check to interaction buttons for `/carrier purge`


## 2.3.8
- All admin commands are now interactions in the 'admin' group:
    - `/admin_release_channel_lock` is now `/admin lock release`
    - `/admin_acquire_channel_lock` is now `/admin lock acquire`
    - `m.cron_status` is now `/admin cron_status`
    - `m.backup` is now `/admin backup`
    - `m.stopquit` is now `/admin stopquit`
    - `/admin_list_optins` is now `/admin list_cco_optins` and has moved to `GeneralCommands.py`
    - `/admin_delete_mission` is now `/admin delete_mission` and has moved to `GeneralCommands.py`
- Various cosmetic improvements to above commands
- New commmand: `/admin lock list` - lists all active channel locks for debugging purposes


## 2.3.7a
- Reverted `/carrier find` change because Discord is stupid


## 2.3.7
- All database commands beginning with `carrier_` are now in the `carrier` subgroup, and can be accessed via `/carrier <command>`. This includes `add`, `delete`, `edit`, `purge`, and `find`.
- `/find` is now `/carrier find`
- [#571](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/571) New command: `/carrier purge`: lists carriers belonging to owners who are no longer on the server, with option to delete.


## 2.3.6
- [#639](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/639) Automatically replace the letter "O" with zero when encountered in Fleet Carrier registrations to add to database
- [#637](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/637) Discord invites sent by MAB to Reddit now use the direct link: `https://discord.gg/ptn`
- [#635](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/635) `/cco load`, `unload`, and `edit` now properly use the target carrier's owner for all relevant purposes (including webhooks and trade alert 'author') instead of the interaction user
- [#642](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/642) `spamchannel` now properly defined for failure state when member cannot be found during mission generation
- [#642](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/642) `mission_temp_channel` now properly defined as `None` before `send_mission_to_discord()`, to avoid additional errors when said function returns early due to error
- [#642](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/642) `find_mission` now properly returns `mission_data` as `None` if no mission is found, rather than a class filled entirely with `None`
- [#642](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/642) Channel lock release should now work properly if the mission generator stops because of an error
- [#643](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/643) `/admin_release_channel_lock` and `/admin_acquire_channel_lock` now properly notify the user if the lock status is already as desired


## 2.3.5
- [#632](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/632) Removed footer of `Add Carrier` summary embed (no longer needed)


## 2.3.4
- [#629](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/629) Shortnames created via `Add Carrier` will no longer include non-alphanumeric characters
- [#628](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/628) `Add Carrier`'s confirmation buttons now include a check for which user is attempting the interaction
- [#626](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/626) `Add Carrier`'s "Please wait..." message will now be updated upon completion.


## 2.3.3
- [#620](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/620) `Add Carrier`'s initial response is now edited rather than deleted, to enhance clarity for observers.
- [#619](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/619) `Add Carrier` now sends the stockbot command to #bot-commands, with a ping for the command user.
- `Add Carrier` is now plural-aware.
- [#621](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/621) Mission summary for `/cco load`, `/cco unload`, and `/cco edit` now uses the alert text instead of embed with fields.
- Renamed `✍ Set Message` on `/cco edit` to `✍ Set or Remove Message`+
- Removed the `🗑 Remove Message` button from `/cco edit` and conformed `✍ Set or Remove Message` behaviour to match `✍ Set Message` on `/cco load` and `/cco unload`. 
- [#618](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/618) Bugfix: `build_directory_structure_on_startup()` now runs in `database.py` instead of `application.py`.
- Bugfix: channel delete on mission gen failure will now be properly called with `seconds_short()`


## 2.3.2
- Hotfix for missions not sending if user has no webhooks saved
- Mission preview now uses trade alert preview
    - In BC state, message will show in preview embed
- New graphics (thanks Sim!) to indicate load and unload, used in trade alerts and channel embeds
- Setting EDMC-OFF disables incompatible buttons (i.e. Reddit, Webhooks)
- Training mode Wine loads are always considered in BC state


## 2.3.1
- Fix for BC status not being detected on Live server


## 2.3.0
New commands:
- [#579](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/579) `/cco active` - toggles Active status for CCOs; CCOs set to active this way will not have the role removed for at least 28 days. Permissions: CCO, Fleet Reserve.
- [#577](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/577) `/rename_community_channel` - used in a Community Channel to rename both the channel and the role. Permissions: Community Mentor, Community Channel Owner.
- [#597](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/597) `Add Carrier` - Context Menu -> Message. Attempts to match PTN carrier name/ID format from a message and give the option of adding any matches to the database. Permissions: Council.
- `/admin_opt_in` - List all CCO opt-ins. (This is for database maintenance purposes.) Permissions: Council. 

CCO command behaviour changes:
- [#578](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/578) `/cco load` `/cco unload` `/cco image` `/cco complete` will now accept any of the following as carrier search terms: full name partial string (as per default behaviour prior to 2.3.0); shortname; carrier registration (e.g. K8Y-T2G); carrier database entry number (discoverable via `/find`)
- `/cco load` `/cco unload` mission send select menu has been replaced with buttons:
    - Buttons provide visual feedback as to which sends are seleted: selected sends are blue, deselected are grey, disabled are greyed out (faded and not clickable)
    - Default sends remain the same
    - Buttons can be clicked to toggle a send on/off
    - Clicking the "EDMC-OFF" button will toggle the EDMC-off option, and reset send options to default for the currently active profile (i.e. EDMC-OFF: ping, no external sends, EDMC-ON: ping, external sends)
    - Clicking the "Send" button will send using all enabled sends, rather than sending to all by default
    - Option to select Webhook sends will be greyed out if user has no registered webhooks
    - External sends (Reddit, Webhooks) will be greyed out if profit is < 10k
    - A warning will display when profit is < 10k
    - "Notify Haulers" will be available but deselected by default if profit is < 10k
- [#600](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/600) The 'Set Message' button for `/cco load` `/cco unload` `/cco edit` now remembers your message, if any. It can also be submitted blank to erase the currently-set message.
    - Better feedback from 'Set Message': The message will now display continuously after being set, rather than disappearing if the user changes options.
- `/cco edit` will now re-send Discord alerts and messages if found to be missing
- [#593](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/593) All Reddit interactions will now abandon and return appropriate errors after a certain amount of time
- [#588](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/588) Added cAPI information and ;stock inara command to local mission information embed, unless mission is flagged EDMC-OFF

CCO Wine load changes:
- Wine loads are now affected by the state of the Booze Cruise #wine-cellar-loading channel
    - open is considered "BC active"
        - a notice appears when posting a Wine load under BC conditions
    - closed is considered "BC inactive"
- Wine loads posted under BC inactive conditions are considered normal trades and will send to #official-trade-alerts
- Wine loads are no longer prohibited from external sends
- Non-BC Wine loads no longer skip Hauler pings
    - Pings are disabled for BC Wine loads
- EDMC-OFF option disabled for BC Wine loads
- [#570](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/570) BC Wine load format changed to BC standard format
    - BC Wine load alerts no longer use embeds
- [#445](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/445) CCO Message Text will now display directly after BC wine loads as a temporary solution until [#20](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/20) is implemented, to allow posting of Wine + Tritium loads in #wine-cellar-loading
- [#259](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/259) Wine alerts channel automatically selected based on BC status

Technical changes:
- ChannelDefs now stored in classes/ChannelDefs.py and relevant type annotation added to MissionParams
- More type annotation throughout
- If a role ping is used by `/cco load` or `/cco unload`, the role's ID will be stored in mission_params. This makes mission editing more straightforward.
- The trade alert channel used by `/cco load` and `/cco unload` is now stored in mission_params. This makes mission cleanup/editing more straightforward.
- Version number at time of mission creation added to MissionParams to aid with future backwards compatibility tests.
- [#596](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/596) Fixed TimeoutError -> asyncio.TimeoutError. TimeoutErrors now handled by ErrorHandler.py via their own error class.
- More errors moved to error handler; better handling of certain errors


## 2.2.7
- [#590](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/590) (Temporary?) workaround for PRAW websocket error; bumped praw versions
- [#572](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/572) `/cco complete` now resolves carrier search term against carriers db instead of missions db. (This will make it consistent with all other instances of using a specific search term to look for a carrier.)
- Converted bot-spam notices for `/create_community_channel`, `/restore_community_channel`, `/remove_community_channel` to embeds
- [#575](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/575) Error handling for channel deletion sequence upon mission complete
- [#565](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/565) Update carrier channel mission embed creation to use guild user avatar rather than global
- [#564](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/564) Archiving community channels now checks for successful permission sync and retries on failure
- [#563](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/563) Fixed month not updating for image choice purposes
- [#566](https://github.com/PilotsTradeNetwork/MissionAlertBot/ifssues/566) Fixed unloads showing carrier supply as if it was station demand
- [#561](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/561) `m.complete` now includes an interactable link for `/mission complete`
- [#560](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/560) Verify Member now includes a jumpurl in the bot-spam notification
- [#569](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/569) Handle errors caused by users blocking DMs for all role-grant commands


## 2.2.6
- [#50](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/50) Logic to create commodities table from scratch
- Logic to add new commodities
- [#580](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/580) Check background tasks aren't running before starting them from `on_ready`
- [#573](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/573) Prevent bots from being nominated for Community Pillar 


## 2.2.5
- More minor error/status report tidy-ups


## 2.2.4
- [#554](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/554) Corrected time on mission generator channel lock alert.
- [#556](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/556) Wine loads will no longer ping the BubbleWineLoader role even if the Select Menu is used to attempt to do so.


## 2.2.3
- [#548](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/548) Errors on commodity search during mission generation now handled by the global error handler.
- [#550](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/550) Role grant/removal context menu commands should now be more resilient to Discord lag.
- [#549](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/549) Moved most CCOCommands errors to error handler

Error message tweaks:

- Various small tweaks to most error message formats
- User-facing text now generally reads "❌" intead of "ERROR"
- New custom error class: CustomError
 - takes a custom message to return to the user
 - response can be set private or public


## 2.2.2
- [#545](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/545) `/cco load` and `/cco unload` now have the option to send to Discord at the top, with a note that it is mandatory.
 - Using it no longer sends exclusively to Discord, ignoring other selections.
- [#544](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/544) Training and Live missions will now only attempt to re-use channels in the correct category.
- [#541](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/541) Using `/carrier_add` now also outputs the code needed to add the carrier to stockbot.
- [#540](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/540) Reason given for mission failure (or success!) now included in bot spam notification.
- [#543](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/543) Added pad size to the station info embed.
- [#513](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/513) Display names and usernames will now be added in parentheses for nominees shown using `/cp_nomination_details` or `/cp_nominees_list`.
- The `this mission channel will be removed in...` notice now clarifies removal will take place `unless a new mission is started.`


## 2.2.1

- [#533](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/533) `Make Full CCO` now removes Trainee, Recruit, and ACO roles from target user
- [#534](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/534) Notify bot-spam on role grants and removals


## 2.2

New commands:
- [#473](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/473) App command `Toggle Event Organiser` to grant Verified Member role, usably by Community Mentors, Mods, and Admins.
- [#475](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/475) App command `Verify Member` to grant or remove Event Organiser role, usably by Community Mentors, Mods, and Admins.
- [#474](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/474) App command `Make CCO Trainee` to grant or remove the CCO Trainee role, usable by CCO Mentors, Mods, and Admins.
- [#474](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/474) App command `Make Full CCO` to grant the Certified Carrier and P.T.N. Fleet Reserve roles, usable by CCO Mentors, Mods, and Admins.

Other changes:

- [#529](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/529) EDMC OFF text above channel alert is now an image
 - random shh/secret/ninja gifs used in embed in place of previous superhero images


## 2.1.4

- [#521](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/521) `Pads` parameter will be vastly more forgiving of acceptable input (`/cco load`, `/cco unload`, `/cco edit`)
- [#523](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/523) The channel removal timer for `/mission complete` "Failed" now uses hammertime.
- [#520](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/520) Channel unlocks will now check if the lock is acquired before attempting to release.
- [#524](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/524) Webhook mission image will now change if mission type is changed with `/cco edit`.
 - also made image replacement method more resilient to Discord being fucking weird
- temp images used during `/cco edit` are now properly cleaned up afterwards


## 2.1.3

- [#507](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/507) Re-implemented startup check for orphaned mission channels
- Added logging to bot-spam of trade channel deletions
- [#516](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/516) Increased view timeouts to 5 minutes from 30 seconds (button view) and 2 minutes (select view) respectively
- [#517](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/517) Mission type (loading/unload) and mission message can now be edited with `/cco edit`


## 2.1.2

- [#505](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/505) Added dynamic channel locks
- #504 Redesigned `m.unlock_override`, is now `/admin_release_channel_lock` and takes channel lock name as parameter


## 2.1.1

- Removed channel_cleanup table from missions.db and related code
- [#508](https://github.com/PilotsTradeNetwork/MissionAlertBot/issues/508) Fixed incorrect timer for final channel deletion


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