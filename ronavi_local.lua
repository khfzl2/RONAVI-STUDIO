-- ronavi_local.lua
-- LocalScript for RONAVI (place in StarterPlayerScripts in RONAVI STUDIO)

local Players = game:GetService("Players")
local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

-- Create a simple HUD
local screenGui = Instance.new("ScreenGui")
screenGui.Name = "RonaviHUD"
screenGui.ResetOnSpawn = false

local title = Instance.new("TextLabel")
title.Name = "TitleLabel"
title.Size = UDim2.new(0, 300, 0, 50)
title.Position = UDim2.new(0, 10, 0, 10)
title.BackgroundTransparency = 0.4
title.TextScaled = true
title.Text = "Welcome to RONAVI!"
title.Parent = screenGui

local coinLabel = Instance.new("TextLabel")
coinLabel.Name = "CoinLabel"
coinLabel.Size = UDim2.new(0, 200, 0, 40)
coinLabel.Position = UDim2.new(0, 10, 0, 70)
coinLabel.BackgroundTransparency = 0.4
coinLabel.Text = "Coins: --"
coinLabel.Parent = screenGui

local earnButton = Instance.new("TextButton")
earnButton.Name = "EarnButton"
earnButton.Size = UDim2.new(0, 140, 0, 40)
earnButton.Position = UDim2.new(0, 220, 0, 70)
earnButton.Text = "Earn 10 Coins"
earnButton.Parent = screenGui

screenGui.Parent = playerGui

-- Update coin display when leaderstats change
local function updateCoins()
	local leader = player:FindFirstChild("leaderstats")
	if leader and leader:FindFirstChild("Coins") then
		coinLabel.Text = "Coins: " .. tostring(leader.Coins.Value)
	else
		coinLabel.Text = "Coins: 0"
	end
end

-- Listen for leaderstats being added
player.ChildAdded:Connect(function(child)
	if child.Name == "leaderstats" then
		child:WaitForChild("Coins").Changed:Connect(updateCoins)
		updateCoins()
	end
end)

-- Button click — increment coins client-side (replicate to server via RemoteEvent in production)
earnButton.MouseButton1Click:Connect(function()
	local leader = player:FindFirstChild("leaderstats")
	if leader and leader:FindFirstChild("Coins") then
		leader.Coins.Value = leader.Coins.Value + 10
	end
end)