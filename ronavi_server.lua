-- ronavi_server.lua
-- Server script for RONAVI (place in ServerScriptService in RONAVI STUDIO)

local Players = game:GetService("Players")
local Workspace = game:GetService("Workspace")

-- Create a simple spawn location in the world
local spawn = Instance.new("SpawnLocation")
spawn.Name = "RONAVISpawn"
spawn.Size = Vector3.new(12, 1, 12)
spawn.Position = Vector3.new(0, 5, 0)
spawn.Anchored = true
spawn.Transparency = 0.3
spawn.BrickColor = BrickColor.new("Bright purple")
spawn.TopSurface = Enum.SurfaceType.Smooth
spawn.Parent = Workspace

-- Welcome players and give leaderstats
Players.PlayerAdded:Connect(function(player)
	-- Create leaderstats folder
	local leaderstats = Instance.new("Folder")
	leaderstats.Name = "leaderstats"
	leaderstats.Parent = player

	-- Add a Coins IntValue
	local coins = Instance.new("IntValue")
	coins.Name = "Coins"
	coins.Value = 100 -- starting coins
	coins.Parent = leaderstats

	-- Optional: ensure character loads at spawn
	player.CharacterAdded:Connect(function(char)
		-- You can customize the character on spawn here
		print("RONAVI: " .. player.Name .. " spawned with " .. tostring(coins.Value) .. " coins.")
	end)

	-- Server-side welcome log
	print("Welcome to RONAVI, " .. player.Name .. "!")
end)