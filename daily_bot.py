import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, time
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))  # ID канала для заданий

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DAILIES_FILE = 'dailies.json'

def load_dailies():
    if os.path.exists(DAILIES_FILE):
        with open(DAILIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"tasks": []}

def save_dailies(data):
    with open(DAILIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_today_task():
    dailies = load_dailies()
    tasks_list = dailies.get("tasks", [])
    if not tasks_list:
        return "📝 Задание на сегодня: отдохни и наберись сил!"
    
    today = datetime.now().strftime("%Y-%m-%d")
    if "last_index" not in dailies:
        dailies["last_index"] = 0
        dailies["last_date"] = None
    
    if dailies["last_date"] != today:
        dailies["last_index"] = (dailies.get("last_index", 0) + 1) % len(tasks_list)
        dailies["last_date"] = today
        save_dailies(dailies)
    
    task = tasks_list[dailies["last_index"]]
    return f"📅 **Задание на {today}**\n\n{task}"

@tasks.loop(time=time(9, 0))  # Каждый день в 9:00
async def daily_task():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(get_today_task())

@daily_task.before_loop
async def before_daily():
    await bot.wait_until_ready()
    print("Бот готов, ожидаю времени отправки...")

@bot.event
async def on_ready():
    print(f'{bot.user} подключился к Discord!')
    try:
        synced = await bot.tree.sync()
        print(f'Синхронизировано {len(synced)} команд')
    except Exception as e:
        print(e)
    if CHANNEL_ID:
        daily_task.start()

# Команда для принудительного запуска задания
@bot.tree.command(name="daily", description="Показать сегодняшнее задание")
async def daily(interaction: discord.Interaction):
    await interaction.response.send_message(get_today_task())

# Команда для админов: добавить задание
@bot.tree.command(name="add_task", description="Добавить новое задание (только для админов)")
@app_commands.default_permissions(administrator=True)
async def add_task(interaction: discord.Interaction, task: str):
    dailies = load_dailies()
    dailies.setdefault("tasks", []).append(task)
    save_dailies(dailies)
    await interaction.response.send_message(f"✅ Задание добавлено! Всего заданий: {len(dailies['tasks'])}", ephemeral=True)

# Команда для админов: список заданий
@bot.tree.command(name="list_tasks", description="Показать список всех заданий (только для админов)")
@app_commands.default_permissions(administrator=True)
async def list_tasks(interaction: discord.Interaction):
    dailies = load_dailies()
    tasks_list = dailies.get("tasks", [])
    if not tasks_list:
        await interaction.response.send_message("📭 Список заданий пуст.", ephemeral=True)
        return
    
    tasks_text = "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks_list)])
    embed = discord.Embed(title="📋 Список заданий", description=tasks_text, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
