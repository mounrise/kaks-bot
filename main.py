import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import random
from datetime import datetime
import os

# === KONFIGURASI ===
TOKEN = os.getenv("DISCORD_TOKEN", "MTQzMTMyNjc5NTI4MTQ2NTQzNA.G3LeAp.x0h1GbF2feeZQC7bTWQOLl_38kuHonrUhObVxw")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1431328424592674866"))
UPDATE_INTERVAL = 120  # detik (2 menit)
USER_IDS = [
    8985787928, 8857840833, 8946425213, 8657104479, 9140616089,
    8894038974, 9459064838, 8686743541, 9429550640
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
status_variasi = [
    lambda c: f"🟢 {c} Member Online",
    lambda c: f"🎮 Memantau {c} pemain aktif",
    lambda c: f"🔥 Komunitas KAKS aktif ({c})"
]


async def get_user_info(user_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
            profile = await resp.json()

        username = profile.get("name", "UnknownUser")
        display_name = profile.get("displayName", username)

        try:
            async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": [user_id]}) as resp:
                data = await resp.json()
        except Exception:
            return {
                "id": user_id,
                "username": username,
                "display_name": display_name,
                "online": False,
                "in_game": False,
                "game": "⚠️ Tidak dapat menghubungi Roblox API"
            }

        presences = data.get("userPresences", [])
        if not presences:
            return {
                "id": user_id,
                "username": username,
                "display_name": display_name,
                "online": False,
                "in_game": False,
                "game": "Offline / Tidak terdeteksi"
            }

        info = presences[0]
        presence_type = info.get("userPresenceType", 0)
        game_name = info.get("lastLocation", "Tidak diketahui")

        is_online = presence_type in [1, 2]
        in_game = presence_type == 2

        return {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "online": is_online,
            "in_game": in_game,
            "game": game_name
        }


async def generate_embed():
    online_users = []
    all_users = []

    for uid in USER_IDS:
        info = await get_user_info(uid)
        all_users.append(info)
        if info["online"]:
            online_users.append(info)

    count_online = len(online_users)
    total_users = len(USER_IDS)

    embed = discord.Embed(
        title=f"👥 Status Anggota Komunitas KAKS",
        description=f"Online: **{count_online}/{total_users}**",
        color=discord.Color.from_str("#C41E3A")
    )

    progress = "█" * count_online + "░" * (total_users - count_online)
    embed.add_field(name="📊 Aktivitas", value=f"`{progress}`", inline=False)

    for info in all_users:
        emoji = "🎮" if info["in_game"] else ("🟢" if info["online"] else "⚪")
        status_text = (
            f"{emoji} **{info['display_name']}** (@{info['username']})\n"
            f"• {info['game'] if info['online'] else 'Offline'}"
        )
        embed.add_field(name="\u200b", value=status_text, inline=False)

    games = [u['game'] for u in online_users if u['in_game']]
    if games:
        top_game = max(set(games), key=games.count)
        embed.add_field(name="🔥 Game Populer Saat Ini", value=top_game, inline=False)

    embed.set_footer(
        text=f"Update terakhir: {datetime.now().strftime('%H:%M:%S')} | Dibuat oleh Mounrise"
    )

    return embed, count_online


async def update_status():
    embed, count_online = await generate_embed()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ Channel tidak ditemukan!")
        return

    await bot.change_presence(activity=discord.Game(name=random.choice(status_variasi)(count_online)))

    async for msg in channel.history(limit=5):
        if msg.author == bot.user:
            await msg.delete()

    await channel.send(embed=embed)
    print(f"✅ Embed diperbarui ({count_online}/{len(USER_IDS)} online)")


@tasks.loop(seconds=UPDATE_INTERVAL)
async def background_update():
    await update_status()


@bot.event
async def on_ready():
    print(f"✅ {bot.user} telah online!")
    await update_status()
    background_update.start()


bot.run(TOKEN)
