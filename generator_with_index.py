#!/usr/bin/env python3
"""
generator_with_index.py

Extension of the RONAVI generator that maintains an index file called "rgeres_index.json"
(you asked: "make sure rgeres index").

Features:
 - Generates RONAVI Lua scripts (local templates or via AI if configured).
 - Writes/updates a local index file (rgeres_index.json) inside the output directory,
   listing generated files, timestamps, source (local/ai), and optional GitHub blob SHA.
 - Optionally pushes generated files and the index to a GitHub repository (via the
   Contents API) if --repo and --github-token are provided.

Usage examples:
 - Local generation + update local index:
     python generator_with_index.py --mode local --type both --outdir ./output
 - Generate and push to GitHub (creates/updates files and index on the specified branch):
     python generator_with_index.py --mode local --type both --outdir ./output \
       --repo khfzl2/my-repo --branch main --github-token GH_TOKEN \
       --commit-message "Add RONAVI scripts + rgeres index"
"""

import os
import argparse
import textwrap
import json
import base64
from datetime import datetime
from typing import Optional, Dict

try:
    import requests
except Exception:
    requests = None

try:
    import openai
except Exception:
    openai = None

AI_SYSTEM_PROMPT = (
    "You are an assistant that only outputs valid Lua code for RONAVI (a fictional rename of "
    "Roblox). Do NOT include markdown fences or explanations — return only the Lua code. "
    "Assume the target environment is 'RONAVI STUDIO' with the same API surface as Roblox (game, "
    "Instance.new, Players, etc.)."
)

LOCAL_TEMPLATES = {
    "server": textwrap.dedent("""\
        -- ronavi_server.lua
        -- Server script for RONAVI (place in ServerScriptService in RONAVI STUDIO)

        local Players = game:GetService("Players")
        local Workspace = game:GetService("Workspace")

        if not Workspace:FindFirstChild("RONAVISpawn") then
            local spawn = Instance.new("SpawnLocation")
            spawn.Name = "RONAVISpawn"
            spawn.Size = Vector3.new(12, 1, 12)
            spawn.Position = Vector3.new(0, 5, 0)
            spawn.Anchored = true
            spawn.Transparency = 0.3
            spawn.BrickColor = BrickColor.new("Bright purple")
            spawn.TopSurface = Enum.SurfaceType.Smooth
            spawn.Parent = Workspace
        end

        Players.PlayerAdded:Connect(function(player)
            local leaderstats = Instance.new("Folder")
            leaderstats.Name = "leaderstats"
            leaderstats.Parent = player

            local coins = Instance.new("IntValue")
            coins.Name = "Coins"
            coins.Value = 100
            coins.Parent = leaderstats

            print("RONAVI: Welcome " .. player.Name .. "! Starting coins: " .. tostring(coins.Value))
        end)
    """),
    "local": textwrap.dedent("""\
        -- ronavi_local.lua
        -- LocalScript for RONAVI (place in StarterPlayerScripts in RONAVI STUDIO)

        local Players = game:GetService("Players")
        local player = Players.LocalPlayer
        local playerGui = player:WaitForChild("PlayerGui")

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

        local function updateCoins()
            local leader = player:FindFirstChild("leaderstats")
            if leader and leader:FindFirstChild("Coins") then
                coinLabel.Text = "Coins: " .. tostring(leader.Coins.Value)
            else
                coinLabel.Text = "Coins: 0"
            end
        end

        player.ChildAdded:Connect(function(child)
            if child.Name == "leaderstats" then
                child:WaitForChild("Coins").Changed:Connect(updateCoins)
                updateCoins()
            end
        end)

        earnButton.MouseButton1Click:Connect(function()
            local leader = player:FindFirstChild("leaderstats")
            if leader and leader:FindFirstChild("Coins") then
                leader.Coins.Value = leader.Coins.Value + 10
            end
        end)
    """)
}


INDEX_FILENAME = "rgeres_index.json"


def save_file(contents: str, outdir: str, filename: str) -> str:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(contents)
    return path


def update_local_index(outdir: str, filename: str, source: str = "local", blob_sha: Optional[str] = None):
    """
    Update or create the local rgeres_index.json file in outdir.
    Each entry: name, path (relative), source, timestamp (UTC ISO), blob_sha (optional).
    """
    idx_path = os.path.join(outdir, INDEX_FILENAME)
    entries = []

    if os.path.exists(idx_path):
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
                if not isinstance(entries, list):
                    entries = []
        except Exception:
            entries = []

    rel_path = os.path.relpath(os.path.join(outdir, filename), start=outdir)
    now = datetime.utcnow().isoformat() + "Z"

    # Update existing entry with same name/path, else append
    updated = False
    for e in entries:
        if e.get("path") == rel_path:
            e.update({"name": filename, "source": source, "timestamp": now, "blob_sha": blob_sha})
            updated = True
            break

    if not updated:
        entries.append({
            "name": filename,
            "path": rel_path,
            "source": source,
            "timestamp": now,
            "blob_sha": blob_sha
        })

    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    return idx_path


# GitHub helpers --------------------------------------------------------------
GITHUB_API = "https://api.github.com"


def _gh_headers(token: str):
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}


def gh_get_file(repo: str, path: str, ref: str, token: str) -> Optional[Dict]:
    """
    Return GitHub contents API response for file if exists, else None.
    """
    if requests is None:
        raise RuntimeError("requests package not installed. Install with: pip install requests")
    owner, name = repo.split("/", 1)
    url = f"{GITHUB_API}/repos/{owner}/{name}/contents/{path}"
    resp = requests.get(url, params={"ref": ref}, headers=_gh_headers(token))
    if resp.status_code == 200:
        return resp.json()
    return None


def gh_put_file(repo: str, path: str, content_bytes: bytes, branch: str, token: str, message: str, sha: Optional[str] = None):
    """
    Create or update a file via GitHub Contents API.
    Returns the API JSON response.
    """
    if requests is None:
        raise RuntimeError("requests package not installed. Install with: pip install requests")
    owner, name = repo.split("/", 1)
    url = f"{GITHUB_API}/repos/{owner}/{name}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=_gh_headers(token), json=payload)
    if resp.status_code in (200, 201):
        return resp.json()
    else:
        raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")


def generate_local_script(script_type: str) -> str:
    if script_type not in LOCAL_TEMPLATES:
        raise ValueError("unknown type: " + script_type)
    return LOCAL_TEMPLATES[script_type]


def main():
    parser = argparse.ArgumentParser(description="RONAVI generator with rgeres index")
    parser.add_argument("--mode", choices=["local", "ai"], default="local")
    parser.add_argument("--type", choices=["server", "local", "both"], default="both")
    parser.add_argument("--outdir", default="./output")
    parser.add_argument("--repo", help="owner/repo to push files to (optional)")
    parser.add_argument("--branch", default="main", help="branch to push to when --repo provided")
    parser.add_argument("--github-token", help="GitHub token with repo access (optional)")
    parser.add_argument("--commit-message", default="Add RONAVI scripts", help="Commit message for GitHub updates")
    args = parser.parse_args()

    to_create = []
    if args.type in ("server", "both"):
        to_create.append(("server", "ronavi_server.lua"))
    if args.type in ("local", "both"):
        to_create.append(("local", "ronavi_local.lua"))

    # Generate and save locally
    for stype, fname in to_create:
        if args.mode == "local":
            contents = generate_local_script(stype)
        else:
            # Minimal AI support: sends prompt to OpenAI if configured
            if openai is None:
                raise RuntimeError("openai package not installed. Install with: pip install openai")
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set for AI mode.")
            openai.api_key = api_key
            prompt = f"Write a {stype} Lua script for RONAVI STUDIO. Return only Lua code."
            messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            resp = openai.ChatCompletion.create(model="gpt-4", messages=messages, temperature=0.2, max_tokens=1200)
            contents = resp.choices[0].message.content

        local_path = save_file(contents, args.outdir, fname)
        print(f"Saved {local_path}")

        # Update local index
        idx_path = update_local_index(args.outdir, fname, source=args.mode, blob_sha=None)
        print(f"Updated local index at {idx_path}")

        # If repo push requested, attempt to push file and then update index blob_sha
        if args.repo and args.github_token:
            # push script file to repo path same as filename at repo root
            try:
                existing = gh_get_file(args.repo, fname, args.branch, args.github_token)
                sha = existing["sha"] if existing else None
                result = gh_put_file(args.repo, fname, contents.encode("utf-8"), args.branch, args.github_token, args.commit_message, sha)
                blob_sha = result["content"]["sha"]
                print(f"Pushed {fname} to {args.repo}@{args.branch} (sha: {blob_sha})")
                # Update local index with blob sha
                update_local_index(args.outdir, fname, source=args.mode, blob_sha=blob_sha)
            except Exception as e:
                print("Failed to push file to GitHub:", e)

    # After all files, optionally push index file to repo too
    local_index_path = os.path.join(args.outdir, INDEX_FILENAME)
    if args.repo and args.github_token and os.path.exists(local_index_path):
        with open(local_index_path, "rb") as f:
            idx_bytes = f.read()
        try:
            existing_idx = gh_get_file(args.repo, INDEX_FILENAME, args.branch, args.github_token)
            idx_sha = existing_idx["sha"] if existing_idx else None
            res = gh_put_file(args.repo, INDEX_FILENAME, idx_bytes, args.branch, args.github_token, args.commit_message + " (update rgeres index)", idx_sha)
            print(f"Pushed index {INDEX_FILENAME} to {args.repo}@{args.branch} (sha: {res['content']['sha']})")
        except Exception as e:
            print("Failed to push index to GitHub:", e)

    print("Done.")


if __name__ == "__main__":
    main()