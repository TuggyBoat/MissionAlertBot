# MissionAlertBot
MissionAlertBot is a Discord bot created by the Pilot's Trade Network for the advertisment of Fleet Carrier (FC) trade missions in the video game Elite Dangerous.


## Functionality

The MissionAlertBot's features primarily allow Fleet Carrier Owners (FCOs) to publish Load/Unload Missions for use by haulers/loaders/cutter-pilots on the Pilot's Trade Network Discord (https://discord.gg/2Y65EwS599) and Subreddit (/r/PilotsTradeNetwork).

A Mission contains the following details:

* The Carrier's ID, formatted XXX-XXX
* The Carrier's in-game name, eg: P.T.N. NJORD
* The Carrier's discord channel, eg: #ptn-njord
* The System wherein the Carrier is conducting its mission, eg: HR 7297
* The Station the Carrier is Loading or Unloading at, eg: O'LEARY CITY
* Whether the Carrier is Loading or Unloading at the station
* The minimum landing-pad size of the Station: 'M' or 'L'
* The Commodity the Carrier is trading, eg: GOLD
* The Profit per Unit (or Ton) the Carrier is trading at (minimum 10k/Unit), eg: 20k/Unit
* The number of units of that commodity being traded, eg: 20k units
* (optional) the ETA of the carrier in minutes
* (optional) Accompanying RolePlay (RP) text, which can be used for any purpose within reason

These details are sufficient for any Elite Dangerous player to determine a mission's location, value, and overall viability.

MissionAlertBot also serves as the main repository for all PTN carriers' and FCOs' details.  For this reason, additional functionality beyond trade missions exists in this bot.

## Technology Used

Carrier and active mission details are stored on an SQL database.