**This project is a work in progress. As a result, the bot may frequently be offline. Furthermore, some features may be unstable or incomplete!**

# STW Bot
STW Bot is a Discord companion bot that allows you to remotely access your Epic Games account as well as your Fortnite: Save The World profile.

# How to use:
- Follow this [invite link](https://discord.com/api/oauth2/authorize?client_id=1083374667982704710&permissions=67387392&scope=bot) and add the bot to one of your servers.
- Run the `/account login` command and follow the instructions on screen to log in.
- The bot requires an "Auth Code" to be submitted. This is then automatically exchanged for an Auth session, which the bot will use to access your account on your behalf.
- Once you've logged in, you'll have access to all commands and features!
- You can use the `/account logout` command at any time if you no longer wish for the bot to have access to your account. Your Auth session will immediately be terminated to keep your account secure.

# Features
- View your Epic Games account details and search for other users.
- Add/remove friends and block/unblock other Epic games accounts.
- View daily mission alerts.
- Manage your in-game progress such as schematics, hero loadouts, quests and account resources.
- Craft, upgrade, evolve and recycle items.
- View the progress of other Fortnite players.

More features on the way!

# Resources
- The bot uses the [discord.py](https://github.com/Rapptz/discord.py) library to interact with Discord's API.
- [This repository](https://github.com/LeleDerGrasshalmi/FortniteEndpointsDocumentation) does a great job of documenting Epic Games' public API services, and is what made this project possible.