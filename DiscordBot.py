import discord
from discord.ext import commands
import asyncio
import yt_dlp
from collections import deque

TOKEN ="YOUR_BOT_TOKEN_HERE"

bot = commands.Bot(command_prefix=".", intents=discord.Intents.all())

yt_dl_options = {"format": "bestaudio/best", "noplaylist": True}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

queues = {}
voice_clients = {}

@bot.event
async def on_ready():
    print(f'{bot.user} çalışıyor.')
    try:
        await bot.tree.sync()
        print("Komutlar senkronize edildi.")
    except Exception as e:
        print(f"Komutlar senkronize edilirken bir hata oluştu: {e}")


@bot.tree.command(name='çal', description="YouTube'dan müzik çalar.")
async def play(interaction: discord.Interaction, search_query: str):
    await interaction.response.send_message("Şarkı yükleniyor...")

    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if interaction.guild.id not in voice_clients or not voice_clients[interaction.guild.id].is_connected():
            voice_client = await channel.connect()
            voice_clients[interaction.guild.id] = voice_client
        else:
            voice_client = voice_clients[interaction.guild.id]

        try:
            search_url = f"ytsearch:{search_query}"
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_url, download=False))
            if 'entries' in data:
                video = data['entries'][0]
                video_id = video['id']
                song_url = f"https://www.youtube.com/watch?v={video_id}"
                player = discord.FFmpegPCMAudio(video['url'], **ffmpeg_options)
                
                if interaction.guild.id not in queues:
                    queues[interaction.guild.id] = deque()
                if voice_client.is_playing():
                    queues[interaction.guild.id].append((player, video['title'], song_url))
                    await interaction.followup.send(f"{video['title']} sıraya eklendi.")
                else:
                    voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction.guild.id), bot.loop))
                    await interaction.followup.send(f"Şu anda {video['title']} çalıyor.\nVideo URL: {song_url}")
            else:
                await interaction.followup.send("Şarkı bulunamadı.")
        except Exception as e:
            await interaction.followup.send(f"Bir hata oluştu: {e}")
    else:
        await interaction.followup.send("Bir ses kanalına bağlı olmalısınız!")


@bot.tree.command(name='bekle', description="Müziği beklemeye alır.")
async def pause(interaction: discord.Interaction):
    await interaction.response.send_message("Müzik beklemeye alınıyor...")
    try:
        if interaction.guild.id in voice_clients:
            voice_clients[interaction.guild.id].pause()
            await interaction.followup.send(f"{interaction.user.mention}, müzik beklemeye alındı.")
    except Exception as e:
        await interaction.followup.send(f"Bir hata oluştu: {e}")

@bot.tree.command(name='devam', description="Müziği devam ettirir.")
async def resume(interaction: discord.Interaction):
    await interaction.response.send_message("Müzik devam ettiriliyor...")
    try:
        if interaction.guild.id in voice_clients:
            voice_clients[interaction.guild.id].resume()
            await interaction.followup.send(f"{interaction.user.mention}, müzik devam ettirildi.")
    except Exception as e:
        await interaction.followup.send(f"Bir hata oluştu: {e}")

@bot.tree.command(name='dur', description="Müziği durdurur ve bağlantıyı keser.")
async def stop(interaction: discord.Interaction):
    await interaction.response.send_message("Müzik durduruluyor ve bağlantı kesiliyor...")
    try:
        if interaction.guild.id in voice_clients:
            voice_clients[interaction.guild.id].stop()
            await voice_clients[interaction.guild.id].disconnect()
            queues[interaction.guild.id].clear()
    except Exception as e:
        await interaction.followup.send(f"Bir hata oluştu: {e}")

@bot.tree.command(name='geç', description="Bir sonraki şarkıya geçer.")
async def skip(interaction: discord.Interaction):
    await interaction.response.send_message("Bir sonraki şarkıya geçiliyor...")
    try:
        if interaction.guild.id in voice_clients:
            voice_clients[interaction.guild.id].stop()
            if queues.get(interaction.guild.id):
                next_song, song_title, song_url = queues[interaction.guild.id].popleft()
                voice_clients[interaction.guild.id].play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction.guild.id), bot.loop))
                await interaction.followup.send(f"Bir sonraki şarkıya geçildi: {song_title}\nVideo URL: {song_url}")
            else:
                await interaction.followup.send(f"Kuyrukta şarkı bulunmuyor.")
    except Exception as e:
        await interaction.followup.send(f"Bir hata oluştu: {e}")

async def play_next(guild_id):
    voice_client = voice_clients.get(guild_id)
    if voice_client and not voice_client.is_playing():
        if queues.get(guild_id):
            next_song, song_title, song_url = queues[guild_id].popleft()
            voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop))
            channel = voice_client.channel
            if channel:
                text_channel = channel.guild.text_channels[0]
                await text_channel.send(f"Şimdi çalıyor: {song_title}\nVideo URL: {song_url}")
        else:
            await voice_client.disconnect()

bot.run(TOKEN)