# RONAVI & RONAVI STUDIO — Example Project

This is a small example that demonstrates how typical Roblox (Lua) scripts would look if the platform and editor were renamed to "RONAVI" and "RONAVI STUDIO". This is purely a fictional rename for demonstration and learning purposes.

Files:
- `ronavi_server.lua` — Server-side script. Place in ServerScriptService (RONAVI STUDIO).
- `ronavi_local.lua` — Client-side LocalScript. Place in StarterPlayerScripts (RONAVI STUDIO).

What the example does:
- Creates a simple spawn location named `RONAVISpawn`.
- Adds a `leaderstats` folder and a `Coins` IntValue for each player.
- Shows a simple HUD with a button that gives the player +10 coins.

How to use in RONAVI STUDIO (Roblox Studio equivalent):
1. Open RONAVI STUDIO.
2. Create a Script in ServerScriptService and paste `ronavi_server.lua`.
3. Create a LocalScript in StarterPlayerScripts and paste `ronavi_local.lua`.
4. Run the experience (play) and test joining players.

Notes:
- Some APIs and behaviors are the same as Roblox's Lua/instance model; this example assumes the standard Roblox API (Instance.new, Players, PlayerGui).
- This is illustrative code — adjust positions, permissions, and GUI styling for your experience.