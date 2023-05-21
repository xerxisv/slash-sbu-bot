# Commands

## Banlist
Type: slash & prefix </br>
Aliases: [`bl`]
- `banlist check <IGN>`:
  - Permissions: `@everyone`
  - Aliases: [`c`]
  - Check whether user with given IGN is in the banlist
- `banlist add <IGN> <reason>`:
  - Permissions: `Moderator`
  - Aliases: [`a`]
  - Add a user to the banlist
- `banlist remove <IGN>`:
  - Type: Slash & Prefix
  - Permissions: `Moderator`
  - Aliases: [`r`, `rm`, `delete`, `del`]
  - Remove a user from the banlist
- `banlist info <IGN>`:
  - Permissions: `@everyone`
  - Aliases: [`i`]
  - List information regarding a person's ban

## Crisis
Type: slash & prefix </br>
Permissions: `Jr. Admin`
- `crisis initialize`:
  - Initialize a crisis
- `crisis restore`:
  - Permissions: `Admin`
  - Restore the changes from an ongoing crisis
- `crisis add <channel>`:
  - Add a channel to an ongoing crisis
- `crisis list changes`:
  - List channel changes made in the ongoing crisis
- `crisis list errors`
  - List errors raised during the crisis initialization

## Files
Type: slash </br>
Permissions: `Admin`
- `file fetch <file_name>`:
  - Fetch a file with the given name from the data folder

## Helper Academy
Type: slash </br>
Permissions: `Moderator`
- `lookup_section`
  - Post look-up examples for Helper Academy

## Inactives
Type: slash </br>
Permissions: `Jr. Moderator`
- `inactive check <guild>`:
  - Check for inactive players in the given guild
- `inactive add <time>`:
  - Permissions: `@everyone`
  - Stop command invoker from being flagged as inactive for the duration of time given
- `inactive list`:
  - List all the users with an inactivity notice
- `inactive force add <ign> <time>`:
  - Add given user to the inactivity list
- `inactive force remove <ign>`:
  - Remove given user from the inactivity list

## Masters
- `checkreq <ign> [profile]`:
  - Type: slash & prefix </br>
  - Permissions: `@everyone`
  - Check if user with given IGN fills the requirements for masters
- `checkreqjr <ign> [profike]`:
  - Check if user with given IGN fills the requirements for masters jr
  - Type: slash & prefix </br>
  - Permissions: `@everyone`
- `change_reqs <guild> [weight_req] [slayer_req] [dungeon_req]`:
  - Type: slash
  - Permissions: `Admin`
  - Change the requirements for the given guild

## Misc

- `pat [user]`:
  - Type: prefix </br>
  - Permissions: `@active`
  - Create a gif with the user's avatar being patted 

## Moderation

Type: slash & prefix </br>
Permissions: `Jr. Moderator`
- `ban <user> <reason> [dm]`:
  - Permissions: `Moderator`
  - Ban the given user
- `unban <user> <reason>`:
  - Permissions: `Moderator`
  - Unban the given user
- `mute <user> <time> [reason]`:
  - Mute the given user
- `unmute <user>`:
  - Unmute the given user

## Rep

Type: slash </br>
Permissions: `Jr. Admin`
- `rep give <receiver> <comments> <value> <collateral>`:
  - Permissions: `@everyone`
  - Give reputation to a user
- `rep remove <rep_id>`:
  - Remove a rep from the database
- `rep list <user> [page]`:
  - List reps the user has received

## Stats

Permissions: `@everyone`
- `hypixel <ign>`:
  - Type: prefix
  - Show hypixel related info of the given user
- `skycrypt <ign> [profile]`:
  - Type: prefix
  - Aliases: ['s']
  - Send the skycrypt link for the given profile
- `weight_check [profile]`:
  - Type: slash
  - Give weight roles

## Suggestions

Type: slash </br>
Permissions: `Admin`
- `suggest <suggestion>`:
  - Type: prefix
  - Permissions: `@everyone`
  - Add a suggestion to the suggestions channel
- `suggestion approve <suggestion> [reason]`:
  - Approve the given suggestion
- `suggestion deny <suggestion> [reason]`:
  - Deny the given suggestion
- `suggestion delete <suggestion>`:
  - Delete the given suggestion
- `suggestion list [author] [answered] [approved]`:
  - List filtered suggestion

## Triggers

Type: slash </br>
Permissions: `Jr. Admin`
- `trigger add <trigger> <owner> <response> [overwrite] [user1-4] [response2-5]`:
  - Add a new trigger
- `trigger remove <trigger>`:
  - Remove given trigger

## Verify

Type: slash & prefix </br>
Permissions: `@everyone`
- `verify <ign>`:
  - Type: prefix
  - Link hypixel account to discord
- `unverify`:
  - Type: prefix
  - Unlink hypixel account from discord
- `force-verify <member> <ign>`:
  - Type: slash
  - Link given user to hypixel account
- `user_info [user] [ign]`:
  - Type: slash
  - Return the info of the given user stored in the database
