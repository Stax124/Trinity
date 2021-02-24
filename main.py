import argparse
import asyncio
import datetime
import json
import logging
import os
import platform
import random
import re
import shlex
import sys
import time
import traceback
from typing import Union

import discord
import DiscordUtils
import pytz
from discord import NotFound
from discord.ext import commands, tasks
from discord.ext.commands import CommandNotFound
from discord.ext.commands.errors import MissingRequiredArgument
from discord.ext.commands.context import Context
from discord.member import Member
from discord.utils import get
from pretty_help import PrettyHelp

# region Parser
parser = argparse.ArgumentParser(
    prog="Trinity", description="Economy discord bot made in python")
parser.add_argument("-l", "--logging",  default="INFO",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Choose level of logging")
parser.add_argument("-f", "--file", default="bot.log",
                    type=str, help="Filename for logging")
parser.add_argument("-m", "--mode", default="w",
                    choices=["w", "a"], help="Write or append to file")
parser.add_argument("--token", default=os.environ["TRINITY"], type=str,
                    help="Discord API token: https://discord.com/developers/applications")
args = parser.parse_args()
# endregion

loglevels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL:": logging.CRITICAL
}

logging.basicConfig(
    level=loglevels[args.logging], handlers=[logging.FileHandler(args.file, args.mode, 'utf-8'), logging.StreamHandler(sys.stdout)])


class rarity(object):
    common = 0xABABAB
    uncommon = 0x12CC00
    rare = 0x009DE3
    epic = 0x8C25FF
    legendary = 0xFF8F00
    event = 0xFF0000


def jsonKeys2int(x):
    if isinstance(x, dict):
        try:
            return {int(k): v for k, v in x.items()}
        except:
            pass
    return x


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


async def levelup_check(ctx: Context):
    logging.debug(f"Triggering levelup_check for {ctx.author.display_name}")
    player = ctx.author
    xp = config["players"][player.id]["xp"]
    level = config["players"][player.id]["level"]

    xp_for_level = config["xp_for_level"]
    for _ in range(level):
        xp_for_level *= config["level_multiplier"]

    xp_for_level = int(xp_for_level)

    if xp >= xp_for_level:
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(255, 255, 0),
            description=f'You are now level `{config["players"][player.id]["level"] + 1}`'
        )
        embed.set_author(name="Level up", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)
        config["players"][player.id]["xp"] -= xp_for_level
        config["players"][player.id]["level"] += 1
        config["players"][player.id]["skillpoints"] += 1
        logging.debug(
            f"{ctx.author.display_name} is now level {config['players'][player.id]['level']}")
        await levelup_check(ctx)


class Configuration():
    "Class for maintaining configuration information and files"

    def load(self):
        logging.info(f"Loading config...")
        try:
            logging.info(
                f"Loading: {self.CONFIG}")
            self.config = json.load(
                open(self.CONFIG), object_hook=jsonKeys2int)
            type(self.config.keys())
        except:
            logging.info(traceback.format_exc())
            logging.info(
                f"Config is unavailable or protected. Loading fallback...")
            self.config = self.fallback
            logging.info(f"Fallback loaded")
            try:
                logging.info(
                    f"Creating new config file: {self.CONFIG}")
                self.save()
            except:
                logging.info(traceback.format_exc())
                logging.info(
                    f"Error writing config file, please check if you have permission to write in this location: {self.CONFIG}")
                return
        logging.info(f"Config loaded")

    def __init__(self):
        if platform.system() == "Windows":
            self.CONFIG = os.environ["userprofile"] + \
                "\\.economy"  # Rename this
        else:
            # Rename this ... alternative for linux or Unix based systems
            self.CONFIG = os.path.expanduser("~")+r"/.economy"
        self.config = {}
        self.fallback = {
            "income": {},
            "prefix": "-",
            "players": {},
            "currency_symbol": "$",
            "upgrade": {},
            "maxupgrade": {},
            "disabled_roles": ["@everyone"],
            "deltatime": 7200,
            "default_role": "",
            "backup_time": 43200,
            "backups": 5,
            "work_range": 0,
            "join_dm": "",
            "default_balance": 0,
            "level_multiplier": 1.2,
            "xp_for_level": 1000,
            "maximum_attack_time": 48,
            "allow_attack_income": True,
            "max_player_items": 30,
            "block_asyncs": False,
            "diplomacy_rate": 0.025,
            "warlord_rate": 0.025,
            "intrique_rate": 0.025,
            "stewardship_rate": 0.025,
            "trading_rate": 0.025,
            "bartering_rate": 0.025,
            "learning_rate": 0.25,
        }

    def save(self):
        try:
            with open(self.CONFIG, "w") as f:
                json.dump(self.config, f, indent=4)
            logging.debug("Config saved")
        except:
            logging.info(traceback.format_exc())
            logging.info(f"Unable to save data to {self.CONFIG}")

    def json_str(self):
        return json.dumps(self.config)

    def __repr__(self):
        return self.config

    def __getitem__(self, name: str):
        logging.debug(f"Grabbing {name} from config")
        try:
            return self.config[name]
        except:
            logging.info(
                f"{name} not found in config, trying to get from fallback")
            self.config[name] = self.fallback[name]
            self.save()
            return self.fallback[name]

    def __setitem__(self, key: str, val):
        logging.debug(f"Setting {key} to {val}")
        self.config[key] = val

    def __delitem__(self, key: str):
        logging.debug(f"Deleting {key} from config")
        self.config.pop(key)


# region Initialize
config = Configuration()
config.load()

bot = commands.Bot(command_prefix=commands.when_mentioned_or(config["prefix"]), help_command=PrettyHelp(
    color=discord.Colour.from_rgb(255, 255, 0), show_index=True, sort_commands=True))

members = list(config["players"].keys())
roles = list(config["income"].keys())

btime = config["backup_time"]
asyncs_on_hold = []


@tasks.loop(seconds=btime)
async def backup():
    logging.debug("Starting backup")
    if not os.path.exists("./backups"):
        os.mkdir("./backups")

    files = os.listdir("./backups")
    logging.debug(f"Backup files: {files}")

    if not files == []:
        files = [int(x) for x in files]
        files.sort(reverse=True)
        if len(files) >= config["backups"]:
            logging.info(f"Deleting {files[-1]}")
            os.remove("./backups/"+str(files[-1]))
            try:
                logging.info("Saving backup")
                with open("./backups/"+str(int(time.time())), "w") as f:
                    json.dump(config.config, f, indent=4)
            except:
                logging.info(traceback.format_exc())
                logging.info(f"Unable to save data to {config.CONFIG}")
        else:
            try:
                logging.info("Saving backup")
                with open("./backups/"+str(int(time.time())), "w") as f:
                    json.dump(config.config, f, indent=4)
            except:
                logging.info(traceback.format_exc())
                logging.info(f"Unable to save data to {config.CONFIG}")
    else:
        try:
            logging.info("Saving backup")
            with open("./backups/"+str(int(time.time())), "w") as f:
                json.dump(config.config, f, indent=4)
        except:
            logging.info(traceback.format_exc())
            logging.info(f"Unable to save data to {config.CONFIG}")

backup.start()
# endregion


# region Events
@bot.event
async def on_ready():
    logging.info(
        f'Initialized:{bot.user} - {bot.user.id}')

    try:
        config["loot-table"]
    except:
        config["loot-table"] = {}
        logging.info(f"Config: loot-table => config")

    for member in bot.guilds[0].members:
        if not member.id in config["players"]:
            members.append(member.id)
            logging.info(
                f"Added {member.display_name} as {member.id}")
            logging.debug(
                f"Initializing config files for {member.display_name}")
            config["players"][member.id] = {}
            config["players"][member.id]["balance"] = config["default_balance"]
            config["players"][member.id]["last-work"] = 0
            config["players"][member.id]["xp"] = 0
            config["players"][member.id]["level"] = 1
            config["players"][member.id]["manpower"] = 0
            config["players"][member.id]["upgrade"] = {}
            config["players"][member.id]["maxupgrade"] = {}
            config["players"][member.id]["player_shop"] = {}
            config["players"][member.id]["stats"] = {
                "diplomacy": 0,
                "warlord": 0,
                "intrique": 0,
                "stewardship": 0,
                "trading": 0,
                "bartering": 0,
                "learning": 0
            }
            logging.debug(
                f"Config files for {member.display_name} initialized")

            for item in list(config["upgrade"].keys()):
                logging.info(
                    f"Added {item} to {member.display_name}")
                config["players"][member.id]["upgrade"][item] = 0
                config["players"][member.id]["maxupgrade"][item] = config["maxupgrade"][item]

        try:
            config["players"][member.id]["balance"]
        except:
            config["players"][member.id]["balance"] = config["default_balance"]
            logging.info(f"Config: balance => {member.name}({member.id})")

        try:
            config["missions"]
        except:
            config["missions"] = {}
            logging.info(f"Config: missions => config")

        try:
            config["players"][member.id]["last-work"]
        except:
            config["players"][member.id]["last-work"] = 0
            logging.info(f"Config: last-work => {member.name}({member.id})")

        try:
            config["players"][member.id]["manpower"]
        except:
            config["players"][member.id]["manpower"] = 0
            logging.info(f"Config: manpower => {member.name}({member.id})")

        try:
            config["players"][member.id]["xp"]
        except:
            config["players"][member.id]["xp"] = 0
            logging.info(f"Config: xp => {member.name}({member.id})")

        try:
            config["players"][member.id]["skillpoints"]
        except:
            config["players"][member.id]["skillpoints"] = 0
            logging.info(
                f"Config: skillpoints => {member.name}({member.id})")

        try:
            config["players"][member.id]["level"]
        except:
            config["players"][member.id]["level"] = 1
            logging.info(f"Config: level => {member.name}({member.id})")

        try:
            config["players"][member.id]["upgrade"]
        except:
            config["players"][member.id]["upgrade"] = {}
            logging.info(f"Config: upgrade => {member.name}({member.id})")

        try:
            config["players"][member.id]["maxupgrade"]
        except:
            config["players"][member.id]["maxupgrade"] = {}
            logging.info(
                f"Config: maxupgrade => {member.name}({member.id})")

        try:
            config["players"][member.id]["player_shop"]
        except:
            config["players"][member.id]["player_shop"] = {}
            logging.info(
                f"Config: player_shop => {member.name}({member.id})")

        try:
            config["players"][member.id]["inventory"]
        except:
            config["players"][member.id]["inventory"] = {}
            logging.info(f"Config: inventory => {member.name}({member.id})")

        try:
            config["players"][member.id]["equiped"]
        except:
            config["players"][member.id]["equiped"] = {}
            logging.info(f"Config: equiped => {member.name}({member.id})")

        try:
            config["players"][member.id]["stats"]
        except:
            config["players"][member.id]["stats"] = {
                "diplomacy": 0,
                "warlord": 0,
                "intrique": 0,
                "stewardship": 0,
                "trading": 0,
                "bartering": 0,
                "learning": 0
            }
            logging.info(f"Config: stats => {member.name}({member.id})")

    for role in bot.guilds[0].roles:
        if not (role.id in roles):
            logging.info(f"{role} added to config")
            config["income"][role.id] = 0

    config.save()
    logging.info(f"Members: {members}")
    logging.info(
        f"Roles: {list(config['income'].keys())}")
    logging.info(
        f"Upgrades: {list(config['upgrade'].keys())}")
    print(f"\n{'-'*100}\n")

    await bot.change_presence(activity=discord.Game(name=f"Try: {config['prefix']}"))


@bot.event
async def on_message(message):
    if not message.author == bot.user:
        logging.info(
            f"{message.author.display_name} ■ {message.author.id}: {message.content}")
        await bot.process_commands(message)


@bot.event
async def on_guild_role_create(role):
    config["income"][role.id] = 0
    logging.info(f"New role added: {role.name}")
    config.save()


@bot.event
async def on_guild_role_delete(role):
    del config["income"][role.id]
    logging.info(f"Role removed: {role.name}")
    config.save()


@bot.event
async def on_command_error(ctx, error):
    logging.debug(f"Error occured: {error}")
    if isinstance(error, CommandNotFound):
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(255, 255, 0),
            description=f'❌ Command not found'
        )
        embed.set_author(name="Status", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)
    elif isinstance(error, NotFound):
        logging.debug("Error 404, passing")
        pass
    elif isinstance(error, MissingRequiredArgument):
        logging.info(error)
        pass
    else:
        logging.debug("Error not catched, raising")
        raise error


@bot.event
async def on_member_join(member: discord.Member):
    if not member.id in config.config["players"]:
        members.append(member.id)
        logging.info(
            f"Added {member.display_name} as {member.id}")
        config["players"][member.id] = {}
        config["players"][member.id]["balance"] = config["default_balance"]
        config["players"][member.id]["last-work"] = 0
        config["players"][member.id]["manpower"] = 0
        config["players"][member.id]["skillpoints"] = 0
        config["players"][member.id]["level"] = 1
        config["players"][member.id]["xp"] = 0
        config["players"][member.id]["upgrade"] = {}
        config["players"][member.id]["maxupgrade"] = {}
        config["players"][member.id]["player_shop"] = {}
        config["players"][member.id]["inventory"] = {}
        config["players"][member.id]["equiped"] = {}
        config["players"][member.id]["stats"] = {
            "diplomacy": 0,
            "warlord": 0,
            "intrique": 0,
            "stewardship": 0,
            "trading": 0,
            "bartering": 0,
            "learning": 0
        }

        for item in config["upgrade"].keys():
            logging.info(
                f"Added {item} to {member.display_name}")
            config.config["players"][member.id]["upgrade"][item] = 0
            config.config["players"][member.id]["maxupgrade"][item] = config["maxupgrade"][item]
    logging.info(
        f"{member.display_name} ■ {member.id} joined")

    if config["join_dm"] != "":
        channel = await member.create_dm()
        await channel.send(config["join_dm"])
        logging.info(f"Welcome message sent to {member}")

    config.save()
# endregion


class Money(commands.Cog):
    """Whatya dooooing, make money !!!"""

    @commands.command(name="leaderboard", help="Show da leaderboard: l, lb, leaderboard", aliases=["lb", "l"])
    async def leaderboard(self, ctx: Context):
        logging.debug("Displaying leaderboard")
        try:
            players = {}
            for player in config["players"]:
                players[player] = config["players"][player]["balance"]
            _sorted = {k: v for k, v in sorted(
                players.items(), key=lambda item: item[1], reverse=True)}

            e_list = []
            msg = ""
            index = 1
            for name in _sorted:
                try:
                    username = get(bot.guilds[0].members, id=name).mention
                except:
                    continue
                msg += f"{index}. {username} `{_sorted[name]:,}{config['currency_symbol']}`\n".replace(
                    ",", " ")
                if index == 30:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=msg
                    )
                    embed.set_author(name="Leaderboard",
                                     icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=msg
            )
            embed.set_author(name="Leaderboard", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="work", help="What are you doing, make some money!: work")
    async def user_work(self, ctx: Context):
        logging.debug(f"{ctx.author.display_name} executing work")
        try:
            if time.time() >= config["players"][ctx.author.id]["last-work"] + config["deltatime"]:
                income = 0
                for role in ctx.author.roles:
                    if config.config["income"][role.id] != 0:
                        income += config.config["income"][role.id]
                if income <= 0:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f"❌ You do not have income set, please ask admin to do so"
                    )
                    embed.set_author(name="Work", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                else:
                    income_multiplier = 1
                    for item in config["players"][ctx.author.id]["equiped"]:
                        item = config["players"][ctx.author.id]["equiped"][item]
                        income_multiplier = income_multiplier * \
                            (item["income_percent"] / 100)

                    income_boost = 0
                    for item in config["players"][ctx.author.id]["equiped"]:
                        item = config["players"][ctx.author.id]["equiped"][item]
                        income_boost += item["income"]

                    income = (income*income_multiplier)+income_boost+(
                        round(config['players'][ctx.author.id]['stats']['stewardship']*income*config['stewardship_rate'], 5))

                    rate = random.randrange(
                        100-config["work_range"]*100, 100+config["work_range"]*100) / 100 if config["work_range"] != 0 else 1
                    if config["players"][ctx.author.id]["last-work"] != 0:
                        timedelta = (
                            time.time() - config["players"][ctx.author.id]["last-work"]) / config["deltatime"]
                        config["players"][ctx.author.id]["balance"] += int(
                            income * timedelta * rate)
                        config["players"][ctx.author.id]["last-work"] = time.time()
                    else:
                        timedelta = 1
                        config["players"][ctx.author.id]["balance"] += income
                        config["players"][ctx.author.id]["last-work"] = time.time()

                    logging.info(
                        f"{ctx.author.display_name} ■ {ctx.author.id} is working [timedelta={timedelta}, rate={rate}]")
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f"✅ <@{ctx.author.id}> worked and got `{int(timedelta*income*rate):,} {config['currency_symbol']}`\nNext available at {datetime.datetime.fromtimestamp(int(config['players'][ctx.author.id]['last-work'] + config['deltatime']),tz=pytz.timezone('Europe/Prague')).time()}\nIncome boosted: `{income_boost:,}{config['currency_symbol']}`\nIncome multiplier `{income_multiplier}`\nStewardship bonus: `{config['players'][ctx.author.id]['stats']['stewardship']*config['stewardship_rate']*100}%`".replace(",", " ")
                    )
                    embed.set_author(name="Work", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                    logging.debug(
                        f"{ctx.author.display_name} ■ {ctx.author.id} is working [timedelta={timedelta}, rate={rate}], symbol={config['currency_symbol']}, next={datetime.datetime.fromtimestamp(int(config['players'][ctx.author.id]['last-work'] + config['deltatime']),tz=pytz.timezone('Europe/Prague')).time()}, boost={income_boost}, multiplier={income_multiplier}, stewardship={config['players'][ctx.author.id]['stats']['stewardship']*config['stewardship_rate']*100}%")
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ You can work at {datetime.datetime.fromtimestamp(int(config['players'][ctx.author.id]['last-work']+config['deltatime']),tz=pytz.timezone('Europe/Prague')).time()}"
                )
                embed.set_author(name="Work", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="reset-money", help="Reset balance of target: reset-money <user: discord.Member>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def reset_money(self, ctx: Context, member: discord.Member):
        logging.debug(f"Resetting balance of {member.display_name}")
        try:
            if member.id in members:
                config["players"][member.id]["balance"] = 0
                logging.info(f"Resetting {member}'s balance")
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Resetting {member.mention}'s balance"
                )
                embed.set_author(name="Reset money",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="Member not found"
                )
                embed.set_author(name="Reset money",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                logging.info("Member not found")
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="remove-money", help="Remove money from target: remove-money <user: discord.Member> <value: integer>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def remove_money(self, ctx: Context, member: discord.Member, balance: int):
        logging.debug(f"Removing {balance} from {member.display_name}")
        try:
            if member.id in members:
                config["players"][member.id]["balance"] -= abs(int(balance))
                logging.info(
                    f"Removing {balance:,}{config['currency_symbol']} from {member}".replace(",", " "))
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Removing {balance}{config['currency_symbol']} from <@{member.id}>"
                )
                embed.set_author(name="Remove money",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="Member not found"
                )
                embed.set_author(name="Remove money",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                logging.info("Member not found")
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="add-money", help="Add money to target: add-money <user: discord.Member> <value: integer>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def add_money(self, ctx: Context, *message):
        try:
            if message[0] == "everyone":
                money = message[1]
                for _member in config["players"]:
                    config["players"][_member]["balance"] += int(money)
                config.save()
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Adding {int(money):,}{config['currency_symbol']} to @everyone".replace(
                        ",", " ")
                )
                embed.set_author(name="Add money",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            pattern = re.compile(r'[0-9]+')
            _users = bot.guilds[0].members
            _id = int(re.findall(pattern, message[0])[0])
            for _user in _users:
                if _user.id == _id:
                    member = _user.id
            balance = float(message[1])

            logging.debug(f"Adding {balance} to {member}")

            if member in members:
                config["players"][member]["balance"] += abs(int(balance))
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Adding {balance:,}{config['currency_symbol']} to <@{_id}>".replace(
                        ",", " ")
                )
                embed.set_author(name="Add money",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                logging.info(f"Adding {balance} to {member}")
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="Member not found"
                )
                embed.set_author(name="Add money",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                logging.info("Member not found")
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="buy", help="Spend money to make more money bruh: buy <type: string> <value: integer>")
    async def buy_upgrade(self, ctx: Context, type: str, value: int = 1):
        logging.debug(f"{ctx.author.display_name} is buying {type} * {value}")
        try:
            if type in config["upgrade"].keys():
                if config["upgrade"][type]["require"] != None:
                    required = config["upgrade"][type]["require"]
                    player_own_required = True if config["players"][
                        ctx.author.id]["upgrade"][required] > 0 else False
                else:
                    required = None

                if required == None or player_own_required:
                    try:
                        call = config["players"][ctx.author.id]["upgrade"][type] + \
                            int(value) <= config["players"][ctx.author.id]["maxupgrade"][type]
                    except:
                        call = True
                    if config["upgrade"][type] == None or call:
                        discount = 0
                        for item in config["players"][ctx.author.id]["equiped"]:
                            item = config["players"][ctx.author.id]["equiped"][item]
                            if item["discount"] != None:
                                if type == item["discount"]:
                                    discount += item["discount_percent"]

                        if discount > 100:
                            discount = 100

                        discount = round(
                            (discount * 0.01) + (config['players'][ctx.author.id]['stats']['bartering']*config['bartering_rate']), 5)

                        cost = (config["upgrade"][type]["cost"] -
                                config["upgrade"][type]["cost"] * discount) * int(value)
                        if config.config["players"][ctx.author.id]["balance"] >= cost:
                            role_list = []
                            for role in ctx.author.roles:
                                if not role.name in config["disabled_roles"] or not "spokojenost" in role.name.lower():
                                    try:
                                        if config["income"][role.id] != 0:
                                            role_list.append(role.id)
                                    except:
                                        embed = discord.Embed(
                                            colour=discord.Colour.from_rgb(
                                                255, 255, 0),
                                            description=f"ERROR: {role.name} not found in config"
                                        )
                                        embed.set_author(
                                            name="Buy", icon_url=bot.user.avatar_url)
                                        await ctx.send(embed=embed)
                                        return
                            if len(role_list) > 1:
                                embed = discord.Embed(
                                    colour=discord.Colour.from_rgb(
                                        255, 255, 0),
                                    description=f"ERROR: Multiple roles to add income to: `{role_list}`"
                                )
                                embed.set_author(
                                    name="Buy", icon_url=bot.user.avatar_url)
                                await ctx.send(embed=embed)
                                return
                            elif len(role_list) == 0 and config["upgrade"][type]["income"] != 0:
                                embed = discord.Embed(
                                    colour=discord.Colour.from_rgb(
                                        255, 255, 0),
                                    description="❌ No role to add income to"
                                )
                                embed.set_author(
                                    name="Buy", icon_url=bot.user.avatar_url)
                                await ctx.send(embed=embed)
                                config.save()
                            else:
                                if config["upgrade"][type]["income"] != 0:
                                    config["income"][role_list[0]
                                                     ] += config["upgrade"][type]["income"] * int(value)

                                config["players"][ctx.author.id]["upgrade"][type] += int(
                                    value)

                                config["players"][ctx.author.id]["balance"] -= cost
                                config.config["players"][ctx.author.id]["manpower"] += int(value) * (
                                    config["upgrade"][type]["manpower"] if "manpower" in config["upgrade"][type] else 0)
                                if config["upgrade"][type]["income"] != 0:
                                    embed = discord.Embed(
                                        colour=discord.Colour.from_rgb(
                                            255, 255, 0),
                                        description=f"✅ Bought {value}x {type} for {cost:,}{config['currency_symbol']} and your income is now {config.config['income'][role_list[0]]:,}{config['currency_symbol']}\nDiscount: `{discount*100}%`\nBartering discount included in discount: `{config['players'][ctx.author.id]['stats']['bartering']*config['bartering_rate']*100}%`".replace(
                                            ",", " ")
                                    )
                                    embed.set_author(
                                        name="Buy", icon_url=bot.user.avatar_url)
                                    await ctx.send(embed=embed)
                                else:
                                    embed = discord.Embed(
                                        colour=discord.Colour.from_rgb(
                                            255, 255, 0),
                                        description=f"✅ Bought {value}x {type} for `{cost:,}{config['currency_symbol']}`\nDiscount: `{discount*100}%`\nBartering discount included in discount: `{config['players'][ctx.author.id]['stats']['bartering']*config['bartering_rate']*100}%`".replace(
                                            ",", " ")
                                    )
                                    embed.set_author(
                                        name="Buy", icon_url=bot.user.avatar_url)
                                    await ctx.send(embed=embed)
                                config.save()
                        else:
                            embed = discord.Embed(
                                colour=discord.Colour.from_rgb(255, 255, 0),
                                description="❌ Not enought money"
                            )
                            embed.set_author(
                                name="Buy", icon_url=bot.user.avatar_url)
                            await ctx.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            colour=discord.Colour.from_rgb(255, 255, 0),
                            description="❌ You cannot purchase more items of this type"
                        )
                        embed.set_author(
                            name="Buy", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f"❌ Required item not bought: {required}"
                    )
                    embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
            else:
                logging.info(f"Invalid type or value")
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="❌ Invalid type or value"
                )
                embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="pay", help="Send money to target: pay <user: discord.Member> <value: int>")
    async def user_pay(self, ctx: Context, member: discord.Member, balance: int):
        logging.debug(
            f"Transfering {balance} from {ctx.author.display_name} to {member.display_name}")
        try:
            if balance < 1:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ Invalid value"
                )
                embed.set_author(name="Pay", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                if config["players"][ctx.author.id]["balance"] >= balance:
                    if member.id in members:
                        config["players"][ctx.author.id]["balance"] -= int(
                            balance)
                        config.config["players"][member.id]["balance"] += int(
                            balance)
                        logging.info(f"Paid {balance} to {member}")
                        embed = discord.Embed(
                            colour=discord.Colour.from_rgb(255, 255, 0),
                            description=f"✅ Paid {balance:,}{config['currency_symbol']} to <@{member.id}>".replace(
                                ",", " ")
                        )
                        embed.set_author(
                            name="Pay", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            colour=discord.Colour.from_rgb(255, 255, 0),
                            description="❌ Member not found"
                        )
                        embed.set_author(
                            name="Pay", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                        logging.info("Member not found")
                else:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description="❌ You don't have enough money"
                    )
                    embed.set_author(name="Pay", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)

            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="balance", help="Show your balance or more likely, empty pocket: b, bal, balance, money", aliases=["bal", "b", "money"])
    async def bal(self, ctx: Context):
        logging.debug(f"Displaying balance of {ctx.author.display_name}")
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"<@{ctx.author.id}> has {config['players'][ctx.author.id]['balance']:,}{config['currency_symbol']}".replace(
                    ",", " ")
            )
            embed.set_author(name="Balance", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())


class Income(commands.Cog):
    """Everything about income"""

    @commands.command(name="income-calc", help="Calculate income: income <populace>")
    async def income_calc(self, ctx: Context, population: int = 0):
        logging.debug(
            f"{ctx.author.display_name} requested income calc of {population}")
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"Income: {int((int(population) * 0.01 * 0.4 / 6)):,}{config['currency_symbol']}".replace(
                    ",", " ")
            )
            embed.set_author(name="Income calculator",
                             icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="income", help="Shows your income: income")
    async def income(self, ctx: Context):
        logging.debug(f"Displaying income of {ctx.author.display_name}")
        try:
            income = 0
            for role in ctx.author.roles:
                try:
                    if config["income"][role.id] != 0:
                        income += config.config["income"][role.id]
                    else:
                        logging.debug(f"Excluding: {role.name}")
                except:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f"ERROR: {role.name} not found in config"
                    )
                    embed.set_author(
                        name="Income", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)

            income_multiplier = 1
            for item in config["players"][ctx.author.id]["equiped"]:
                item = config["players"][ctx.author.id]["equiped"][item]
                income_multiplier = income_multiplier * \
                    (item["income_percent"] / 100)

            income_boost = 0
            for item in config["players"][ctx.author.id]["equiped"]:
                item = config["players"][ctx.author.id]["equiped"][item]
                income_boost += item["income"]

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"Income: `{(income*income_multiplier)+income_boost:,}{config['currency_symbol']}`\nIncome boosted: `{income_boost:,}{config['currency_symbol']}`\nIncome multiplier `{income_multiplier}`".replace(
                    ",", " ")
            )
            embed.set_author(name="Income", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="add-income", pass_context=True, help="Add income: add-income <role: discord.Role> <value: integer>")
    @commands.has_permissions(administrator=True)
    async def add_income(self, ctx: Context, role: discord.Role, value: int):
        logging.debug(f"Adding {value} to income of {role}")
        try:
            if value > 0:
                config.config["income"][role.id] += value

                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Added: `{value:,}{config['currency_symbol']}` to income of {role.mention}".replace(
                        ",", " ")
                )
                embed.set_author(name="Add income",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Add income"
                )
                embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)

            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="remove-income", pass_context=True, help="Remove income: remove-income <role: discord.Role> <value: integer>")
    @commands.has_permissions(administrator=True)
    async def remove_income(self, ctx: Context, role: discord.Role, value: int):
        logging.debug(f"Removing {value} from income of {role}")
        try:
            if value > 0:
                config.config["income"][role.id] -= value

                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Removed: `{value:,}{config['currency_symbol']}` from income of {role.mention}".replace(
                        ",", " ")
                )
                embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Invalid value"
                )
                embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="income-lb", help="Show da income leaderboard: l, lb, leaderboard")
    async def income_lb(self, ctx: Context):
        logging.debug("Displaying income leaderboard")
        try:
            roles = config["income"]
            _sorted = {k: v for k, v in sorted(
                roles.items(), key=lambda item: item[1], reverse=True)}

            e_list = []
            msg = ""
            index = 1
            for _id in _sorted:
                try:
                    role = get(bot.guilds[0].roles, id=_id).mention
                except:
                    pass
                msg += f"{index}. {role} `{_sorted[_id]:,}{config['currency_symbol']}`\n".replace(
                    ",", " ")
                if index == 30:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=msg
                    )
                    embed.set_author(name="Income Leaderboard",
                                     icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=msg
            )
            embed.set_author(name="Leaderboard", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())


class Config(commands.Cog):
    """Modify configuration file"""

    @commands.command(name="config-save", help="Save configuration file: config-save", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def config_save(self, ctx: Context):
        try:
            config.save()
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="✅ Config saved"
            )
            embed.set_author(name="Config", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="config-load", help="Load configuration file: config-load", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def config_load(self, ctx: Context):
        try:
            config.load()
            config.save()
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="✅ Config loaded"
            )
            embed.set_author(name="Config", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="config", help="Output config directory: config <path> [path]...", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def config_(self, ctx: Context, *message):
        logging.debug(f"{ctx.author.display_name} requested config")
        try:
            message = list(message)
            for i in range(len(message)):
                if re.findall(re.compile(r"[<][@][!][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _roles = bot.guilds[0].roles
                    _id = int(re.findall(pattern, message[i])[0])
                    for _role in _roles:
                        if _role.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_role.id}")
                            message[i] = _role.id
                    break

            msg = ""
            if message == []:
                for item in config.config:
                    msg += f"`{item}`\n"
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=msg
                )
                embed.set_author(name="Config", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                current = config.config
                if type(message) == str:
                    last = message
                else:
                    last = message[-1]
                for word in message:
                    if word == last:
                        try:
                            current = current[last]
                        except KeyError:
                            embed = discord.Embed(
                                colour=discord.Colour.from_rgb(255, 255, 0),
                                description="Not found"
                            )
                            embed.set_author(
                                name="Config", icon_url=bot.user.avatar_url)
                            await ctx.send(embed=embed)
                            break
                        try:
                            for name in current:
                                msg += f"`{name}`\n"
                        except:
                            msg += f"`{current}`"
                        embed = discord.Embed(
                            colour=discord.Colour.from_rgb(255, 255, 0),
                            description=msg
                        )
                        embed.set_author(
                            name="Config", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                        break
                    else:
                        current = current[word]
            config.save()

        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="set", help="Change values in config. You rather know what ya doin!: set <path> [path]... { = | < | > } <value>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def set(self, ctx: Context, *message):
        logging.debug(
            f"{ctx.author.display_name} is setting something in config: {message}")
        try:
            message = list(message)
            for i in range(len(message)):
                if re.findall(re.compile(r"[<][@][!][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _roles = bot.guilds[0].roles
                    _id = int(re.findall(pattern, message[i])[0])
                    for _role in _roles:
                        if _role.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_role.id}")
                            message[i] = _role.id
                    break

            current = config.config
            mode = None
            try:
                last = message[message.index("=") - 1]
                mode = "set"
            except:
                try:
                    last = message[message.index(">") - 1]
                    mode = "add"
                except:
                    last = message[message.index("<") - 1]
                    mode = "remove"
            for word in message:
                if word == last:
                    try:
                        if mode == "set":
                            current[last] = int(message[-1])
                        elif mode == "add":
                            current[last] += int(message[-1])
                        else:
                            current[last] -= int(message[-1])
                    except:
                        try:
                            if mode == "set":
                                current[last] = float(message[-1])
                            elif mode == "add":
                                current[last] += float(message[-1])
                            else:
                                current[last] -= float(message[-1])
                        except:
                            current[last] = message[-1]
                        finally:
                            mode = None
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description="Success"
                    )
                    embed.set_author(name="Set", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                    break
                else:
                    current = current[word]
            await levelup_check(ctx)
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="config-stats", help="Config stats: config-stats", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def config_stats(self, ctx: Context):
        logging.debug("Displaying config stats")
        size = os.path.getsize(config.CONFIG)
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(255, 255, 0),
            description=f"Size: {sizeof_fmt(size)}\nPath: {config.CONFIG}\nLines: {sum(1 for line in open(config.CONFIG))}"
        )
        embed.set_author(name="Config-stats", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="next-backup", help="Outputs time of next backup: next-backup", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def next_backup(self, ctx: Context):
        logging.debug("Sending next backup time")
        message = backup.next_iteration.astimezone(
            pytz.timezone('Europe/Prague')).strftime(r"%H:%M:%S, %d/%m/%Y")
        await ctx.send(message)


class Development(commands.Cog):
    """Only for developers, who know how to operate this bot"""

    @commands.command(name="json-encode", help="Encode string to yaml format: json-encode <value: string>", pass_context=True)
    async def yaml_encode(self, ctx: Context, *message):
        logging.debug(f"Encoding: {' '.join(message)}")
        try:
            message = " ".join(message)
            await ctx.send(json.dumps(message))
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="reload", help="Reload members and roles: reload")
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx: Context):
        logging.debug("Reloading config")
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="Reloading members..."
            )
            embed.set_author(name="Reload", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)

            for member in bot.guilds[0].members:
                if not member.id in members:
                    members.append(member.id)
                    config.config["players"][member.id] = {}
                    config.config["players"][member.id]["balance"] = 0
                    config.config["players"][member.id]["last-work"] = 0
                    config.config["players"][member.id]["upgrade"] = {}
                    config.config["players"][member.id]["maxupgrade"] = {}

                    for item in list(config.fallback["upgrade"].keys()):
                        logging.info(
                            f"Added {item} to {member.display_name}")
                        config.config["players"][member.id]["upgrade"][item] = 0
                        config.config["players"][member.id]["maxupgrade"][item] = config["maxupgrade"][item]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="✅ Members reloaded"
            )
            embed.set_author(name="Reload", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="Reloading roles..."
            )
            embed.set_author(name="Reload", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)

            for role in bot.guilds[0].roles:
                if not (role.id in roles):
                    logging.info(f"{role} added to config")
                    config.config["income"][role.id] = 0

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="✅ Roles reloaded"
            )
            embed.set_author(name="Reload", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="python3", help="Execute python code: python3 <command>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def python3(self, ctx: Context, *message):
        logging.debug(f"Executing python command: {' '.join(message)}")
        try:
            message = list(message)
            for i in range(len(message)):
                if re.findall(re.compile(r"[<][@][!][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _roles = bot.guilds[0].roles
                    _id = int(re.findall(pattern, message[i])[0])
                    for _role in _roles:
                        if _role.id == _id:
                            logging.info(
                                f"{message[i]} was replaced by {_role.id}")
                            message[i] = _role.id
                    break

            result = eval(" ".join(message))
            await ctx.send(result)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="execute", help="Execute python code: execute <command>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def config_save(self, ctx: Context, *message):
        logging.debug(f"Executing command: {' '.join(message)}")
        try:
            message = list(message)
            result = exec(" ".join(message))
            if result != None:
                await ctx.send(result)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="dm", help="Send dm to member: dm <member: discord.Member> <content: str>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def send_dm(self, ctx: Context, member: discord.Member, *, content):
        logging.debug(f"Sending {content} to {member.display_name}")
        if content == "join-dm":
            if config["join_dm"] != "":
                content = config["join_dm"]

        channel = await member.create_dm()
        await channel.send(content)

    @commands.command(name="asyncs-on-hold", help="Number of async events on hold: asyncs-on-hold", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def asyncs_on_hold_(self, ctx: Context):
        logging.debug("Sending queued async commands")
        await ctx.send(asyncs_on_hold)


class Settings(commands.Cog):
    """Modify settings"""

    @commands.command(name="shutdown", help="Show the bot, whos da boss: shutdown", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def shutdown(self, ctx: Context):
        logging.warning("Shutting down bot")
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(255, 255, 0),
            description="✅ Shutting down..."
        )
        embed.set_author(name="Shutdown", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)
        logging.info("Shutting down...")
        sys.exit()

    @commands.command(name="add-item", pass_context=True, help="Add item to database: add-item [--maxupgrade MAXUPGRADE] [--income INCOME] [--manpower MANPOWER] [--require REQUIRE] name cost")
    @commands.has_permissions(administrator=True)
    async def add_item(self, ctx: Context, *querry):
        fparser = argparse.ArgumentParser()
        fparser.add_argument("name", type=str)
        fparser.add_argument("cost", type=int)
        fparser.add_argument("--maxupgrade", type=int, default=None)
        fparser.add_argument("--income", type=int, default=0)
        fparser.add_argument("--manpower", type=int, default=0)
        fparser.add_argument("--require", type=str, default=None)

        querry = shlex.split(" ".join(querry))

        try:
            fargs = fparser.parse_args(querry)
        except SystemExit:
            return

        for member in config.config["players"]:
            config["players"][member]["maxupgrade"] = {
                **config["players"][member]["maxupgrade"], **{fargs.name: fargs.maxupgrade}}
            config["players"][member]["upgrade"] = {
                **config["players"][member]["upgrade"], **{fargs.name: 0}}

        config["upgrade"] = {**config["upgrade"], **{fargs.name: {
            "cost": fargs.cost, "income": fargs.income, "manpower": fargs.manpower, "require": fargs.require}}}
        config["maxupgrade"] = {**config["maxupgrade"],
                                **{fargs.name: fargs.maxupgrade}}

        embed = discord.Embed(title=fargs.name, color=0xffff00)
        embed.set_author(name="Succesfully added to inventory",
                         icon_url=bot.user.avatar_url)
        embed.add_field(name="Cost", value=fargs.cost, inline=True)
        embed.add_field(name="Maximum", value=fargs.maxupgrade,
                        inline=True) if fargs.maxupgrade != None else None
        embed.add_field(name="Income", value=fargs.income,
                        inline=True) if fargs.income != 0 else None
        embed.add_field(name="Manpower", value=fargs.manpower,
                        inline=True) if fargs.manpower != 0 or fargs.manpower != None else None
        await ctx.send(embed=embed)

        config.save()

    @commands.command(name="remove-item", pass_context=True, help="Remove item from database: remove-item <name: string>")
    @commands.has_permissions(administrator=True)
    async def remove_item(self, ctx: Context, item: str):
        try:
            try:
                item
            except:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ No name specified"
                )
                embed.set_author(name="Remove item",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            for member in config.config["players"]:
                config["players"][member]["maxupgrade"].pop(item)
                config["players"][member]["upgrade"].pop(item)

            config["upgrade"].pop(item)
            config["maxupgrade"].pop(item)

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"✅ Sucessfully removed `{item}`"
            )
            embed.set_author(name="Remove item", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            return
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="prefix", help="Change prefix of da bot: prefix <prefix: string>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def command_prefix(self, ctx: Context, prefix: str):
        try:
            config.config["prefix"] = prefix
            config.save()
            bot.command_prefix = prefix
            logging.info(f"Prefix changed to {config['prefix']}")
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"✅ Prefix changed to {prefix}"
            )
            embed.set_author(name="Prefix", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        await bot.change_presence(activity=discord.Game(name=f"Try: {config['prefix']}"))

    @commands.command(name="deltatime", help="Sets time between allowed !work commands: deltatime <value: integer>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def deltatime(self, ctx: Context, value: int = config["deltatime"]):
        try:
            config["deltatime"] = int(value)
            config.save()
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"✅ Deltatime changed to {int(value)} seconds"
            )
            embed.set_author(name="Config", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="bravo-six-going-dark", help="Deletes messages: bravo-six-going-dark <messages: integer>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def bravo_six_going_dark(self, ctx: Context, messages: int):
        await ctx.channel.purge(limit=messages)

    @commands.command(name="on-join-dm", help="Set message to be send when player joins: on-join-dm <message: str>", pass_context=True)
    @commands.has_permissions(administrator=True)
    async def on_join_dm(self, ctx: Context, *, message):
        try:
            config["join_dm"] = message
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"Sucessfully set"
            )
            embed.set_author(name="Join dm", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)

            config.save()
        except:
            print(traceback.format_exc())
            ctx.send(traceback.format_exc())


class Essentials(commands.Cog):
    """Other usefull commands"""

    @commands.command(name="members", help="Show all members: members")
    async def members(self, ctx: Context):
        try:
            e_list = []
            msg = ""
            index = 1
            for user in bot.guilds[0].members:
                msg += f"{index}. {user.mention} `{user.id}`\n"
                if index == 30:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=msg
                    )
                    embed.set_author(
                        name="Members", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=msg
            )
            embed.set_author(name="Members", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="roles", help="Show all roles: roles")
    async def roles(self, ctx: Context):
        try:
            e_list = []
            msg = ""
            index = 1
            for role in bot.guilds[0].roles:
                msg += f"{index}. {role.mention}\n"
                if index == 30:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=msg
                    )
                    embed.set_author(
                        name="Roles", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=msg
            )
            embed.set_author(name="Roles", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="roll", help="Roll the dice of x sides: roll <maximal-value: integer>")
    async def roll(self, ctx: Context, value: int):
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="✅ " + str(random.randint(0, int(value)))
            )
            embed.set_author(name="Roll", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="time", help="Shows formated time: time")
    async def time(self, ctx: Context):
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="✅ " +
                datetime.datetime.now(tz=pytz.timezone(
                    'Europe/Prague')).strftime(r"%H:%M:%S, %d/%m/%Y")
            )
            embed.set_author(name="Time", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="limits", help="Shows upgrade limits for your account: limits")
    async def limits(self, ctx: Context):
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"Limits is deprecated, use {config['prefix']}shop instead"
            )
            embed.set_author(name="Limits", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="upgrades", help="Shows the current number of upgrades bought: upgrades")
    async def upgrades(self, ctx: Context):
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"Upgrades is deprecated, use {config['prefix']}shop instead"
            )
            embed.set_author(name="Upgrades", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="role", help="Your roles: role")
    async def role(self, ctx: Context):
        try:
            msg = ""
            index = 1
            for name in ctx.author.roles:
                msg += f"{name.mention} `{name.id}`\n"
                index += 1
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=msg
            )
            embed.set_author(name="Role", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="shop", help="Show shop")
    async def shop(self, ctx: Context):
        try:
            e_list = []
            index = 1
            msg = ""
            _sorted_keys = list(config["upgrade"].keys())
            _sorted_keys.sort(key=str.lower)

            _sorted = {}

            for item in _sorted_keys:
                _sorted[item] = config["upgrade"][item]

            for item in _sorted:
                if "manpower" in config["upgrade"][item]:
                    if config["upgrade"][item]["manpower"] != 0:
                        manpower = f'`Manpower:` {config["upgrade"][item]["manpower"]}'
                    else:
                        manpower = ""
                else:
                    manpower = ""
                stock = f'{config["players"][ctx.author.id]["upgrade"][item]}/{config["players"][ctx.author.id]["maxupgrade"][item]}' if config[
                    "players"][ctx.author.id]["maxupgrade"][item] != None else f'{config["players"][ctx.author.id]["upgrade"][item]}/Not limited'
                msg += f'`{item}` {stock} `Cost:` {config["upgrade"][item]["cost"]:,}{config["currency_symbol"]} {manpower}\n'.replace(
                    ",", " ")
                if index == 30:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=msg
                    )
                    embed.set_author(name="Shop", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=msg
            )
            embed.set_author(name="Shop", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())


class PlayerShop(commands.Cog):
    "Sell stuff, buy stuff or do whatever your heart desires"

    @commands.command(name="player-shop", help="Show player shop: player-shop <player: discord.Member>")
    async def player_shop(self, ctx: Context, user: discord.Member = None):
        try:
            if user == None:
                user = ctx.author

            e_list = []
            index = 1
            last = len(config["players"][user.id]["player_shop"])
            for name in config["players"][user.id]["player_shop"]:
                item = config["players"][user.id]["inventory"][name]
                embed = discord.Embed(
                    title=name, description=item["description"], color=rarity.__dict__[item["rarity"]])
                embed.set_author(
                    name="Player shop" + f" ({index}/{last})", icon_url=bot.user.avatar_url)
                embed.add_field(
                    name="Price", value=config["players"][user.id]["player_shop"][name], inline=False)
                embed.add_field(
                    name="Rarity", value=item["rarity"], inline=True)
                embed.add_field(
                    name="Income", value=item["income"], inline=True) if item["income"] != 0 else None
                embed.add_field(
                    name="Income %", value=item["income_percent"], inline=True) if item["income_percent"] != 0 else None
                embed.add_field(
                    name="Discount", value=item["discount"], inline=True) if item["discount"] != 0 else None
                embed.add_field(
                    name="Discount %", value=item["discount_percent"], inline=True) if item["discount_percent"] != 0 else None
                e_list.append(embed)
                index += 1

            if e_list == []:
                embed = discord.Embed(title="Empty")
                embed.set_author(
                    name="Player shop" + f" ({index}/{last})", icon_url=bot.user.avatar_url)
                e_list.append(embed)
            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="player-sell", help="Sell items: player-sell <price: int> <item: str>")
    async def player_sell(self, ctx: Context, *, message):
        try:
            querry = shlex.split(message)

            try:
                price = int(querry[0])
                item = " ".join(querry[1:])

            except IndexError:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ Bad arguments"
                )
                embed.set_author(name="Sell", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)

            if not item in config["players"][ctx.author.id]["inventory"]:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"{item} not found in your inventory"
                )
                embed.set_author(name="Sell", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            config["players"][ctx.author.id]["player_shop"] = {
                **config["players"][ctx.author.id]["player_shop"], **{item: price}}

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"✅ Name: `{item}`\nPrice: {price}"
            )
            embed.set_author(name="Sell", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="player-buy", help="Sell items: player-buy <user: discord.Member> <item: str>")
    async def player_buy(self, ctx: Context, user: discord.Member, *, item: str):
        try:
            if ctx.author == user:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="❌ Can't buy item from yourself"
                )
                embed.set_author(name="Player buy",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            try:
                cost = config["players"][user.id]["player_shop"][item]
            except KeyError:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="❌ Item not found"
                )
                embed.set_author(name="Player buy",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            if config["players"][ctx.author.id]["balance"] >= cost - (cost * config['players'][ctx.author.id]['stats']['trading']*config['trading_rate']):
                config["players"][ctx.author.id]["inventory"][item] = config["players"][user.id]["inventory"][item]
                config["players"][ctx.author.id]["balance"] -= cost - \
                    (cost * config['players'][ctx.author.id]
                     ['stats']['trading']*config['trading_rate'])
                config["players"][user.id]["balance"] += cost
                del config["players"][user.id]["player_shop"][item]
                del config["players"][user.id]["inventory"][item]

                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"✅ Bought {item} for {cost:,}{config['currency_symbol']} and item was added to your inventory\nTrading discount: `{config['players'][ctx.author.id]['stats']['trading']*config['trading_rate']*100}%`".replace(
                        ",", " ")
                )
                embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="❌ Not enought money"
                )
                embed.set_author(name="Player buy",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="player-retrieve", help="Cancel shop listing of item: player-retrieve  <item: str>")
    async def player_retrieve(self, ctx: Context, *, item: str):
        try:
            try:
                config["players"][ctx.author.id]["player_shop"][item]
            except KeyError:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description="❌ Item not found"
                )
                embed.set_author(name="Player retrieve",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            del config["players"][ctx.author.id]["player_shop"][item]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description="✅ Item removed from shop"
            )
            embed.set_author(name="Player retrieve",
                             icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)

        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())


class Inventory(commands.Cog):
    "Inventory"

    @commands.command(name="inventory", help="Shows your 'realy usefull' items in your inventory: inventory", aliases=["inv", "backpack", "loot"])
    async def inventory(self, ctx: Context):
        try:
            e_list = []
            index = 1
            last = len(config["players"][ctx.author.id]["inventory"])
            for name in config["players"][ctx.author.id]["inventory"]:
                item = config["players"][ctx.author.id]["inventory"][name]
                embed = discord.Embed(
                    title=name, description=item["description"] if item["description"] != None else "", color=rarity.__dict__[item["rarity"]])
                embed.set_author(
                    name="Inventory" + f" ({index}/{last})", icon_url=bot.user.avatar_url)
                embed.add_field(name="Type", value=item["type"], inline=True)
                embed.add_field(
                    name="Income", value=item["income"], inline=True) if item["income"] != 0 else None
                embed.add_field(
                    name="Income %", value=item["income_percent"], inline=True) if item["income_percent"] != 0 else None
                embed.add_field(
                    name="Discount", value=item["discount"], inline=True) if item["discount"] != 0 else None
                embed.add_field(
                    name="Discount %", value=item["discount_percent"], inline=True) if item["discount_percent"] != 0 else None
                embed.add_field(
                    name="Rarity", value=item["rarity"], inline=True)
                e_list.append(embed)
                index += 1

            if e_list == []:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ Nothing in inventory"
                )
                embed.set_author(name="Inventory",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="equiped", help="Shows your equiped items: equiped")
    async def equiped(self, ctx: Context):
        try:
            e_list = []
            index = 1
            last = len(config["players"][ctx.author.id]["equiped"])
            for name in config["players"][ctx.author.id]["equiped"]:
                item = config["players"][ctx.author.id]["equiped"][name]
                embed = discord.Embed(
                    title=name, description=item["description"], color=rarity.__dict__[item["rarity"]])
                embed.set_author(
                    name="Inventory" + f" ({index}/{last})", icon_url=bot.user.avatar_url)
                embed.add_field(name="Type", value=item["type"], inline=True)
                embed.add_field(
                    name="Income", value=item["income"], inline=True) if item["income"] != 0 else None
                embed.add_field(
                    name="Income %", value=item["income_percent"], inline=True) if item["income_percent"] != 0 else None
                embed.add_field(
                    name="Discount", value=item["discount"], inline=True) if item["discount"] != 0 else None
                embed.add_field(
                    name="Discount %", value=item["discount_percent"], inline=True) if item["discount_percent"] != 0 else None
                embed.add_field(
                    name="Rarity", value=item["rarity"], inline=True)
                e_list.append(embed)
                index += 1

            if e_list == []:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ Nothing in inventory"
                )
                embed.set_author(name="Inventory",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="equip", help="Equip item: equip <*item: str>")
    async def equip(self, ctx: Context, *, item: str):
        try:
            try:
                types = []
                for equiped in config["players"][ctx.author.id]["equiped"]:
                    equiped = config["players"][ctx.author.id]["equiped"][equiped]
                    types.append(equiped["type"])

                if config["players"][ctx.author.id]["inventory"][item]["type"] in types:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f"❌ Slot already occupied"
                    )
                    embed.set_author(
                        name="Equip", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                    return

                config["players"][ctx.author.id]["equiped"][item] = config["players"][ctx.author.id]["inventory"][item]
                del config["players"][ctx.author.id]["inventory"][item]
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"✅ {item} equiped"
                )
                embed.set_author(name="Equip", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                config.save()
            except KeyError:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ {item} not found in your inventory"
                )
                embed.set_author(name="Equip", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="unequip", help="Unequip item: unequip <*item: str>")
    async def unequip(self, ctx: Context, *, item: str):
        try:
            try:
                config["players"][ctx.author.id]["inventory"][item] = config["players"][ctx.author.id]["equiped"][item]
                del config["players"][ctx.author.id]["equiped"][item]
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"✅ {item} unequiped"
                )
                embed.set_author(name="Unequip", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                config.save()
            except KeyError:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ {item} not found in your inventory"
                )
                embed.set_author(name="Unequip", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="recycle", help="Recycle item: recycle <*item: str>")
    async def recycle(self, ctx: Context, *, item: str):
        try:
            if item in config["players"][ctx.author.id]["inventory"]:
                del config["players"][ctx.author.id]["inventory"][item]

                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"✅ Recycled"
                )
                embed.set_author(
                    name="Recycle", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                config.save()
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ {item} not found"
                )
                embed.set_author(
                    name="Recycle", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="add-player-item", help="Add new item to players inventory: add-player-item UNION[str, discord.Member] [--income INCOME] [--income_percent INCOME_PERCENT] [--discount DISCOUNT] [--discount_percent DISCOUNT_PERCENT] [--description DESCRIPTION] name {common,uncommon,rare,epic,legendary,event} {helmet,weapon,armor,leggins,boots,artefact}")
    @commands.has_permissions(administrator=True)
    async def add_player_item(self, ctx: Context, user: Union[discord.Member, str], *querry):
        fparser = argparse.ArgumentParser()
        fparser.add_argument("name", type=str)
        fparser.add_argument("rarity", choices=[
                             "common", "uncommon", "rare", "epic", "legendary", "event"], type=str)
        fparser.add_argument(
            "type", choices=["helmet", "weapon", "armor", "leggins", "boots", "artefact"])
        fparser.add_argument("--income", type=int, default=0)
        fparser.add_argument("--income_percent", type=int, default=100)
        fparser.add_argument("--discount", type=str, default=None)
        fparser.add_argument("--discount_percent", type=int, default=0)
        fparser.add_argument("--description", type=str, default=None)

        querry = shlex.split(" ".join(querry))

        try:
            fargs = fparser.parse_args(querry)
        except SystemExit:
            return

        if user == "loot-table":
            config["loot-table"][fargs.name] = {
                "description": fargs.description,
                "type": fargs.type,
                "rarity": fargs.rarity,
                "income": fargs.income,
                "income_percent": fargs.income_percent,
                "discount": fargs.discount,
                "discount_percent": fargs.discount_percent,
                "equiped": False
            }
        else:
            config["players"][user.id]["inventory"][fargs.name] = {
                "description": fargs.description,
                "type": fargs.type,
                "rarity": fargs.rarity,
                "income": fargs.income,
                "income_percent": fargs.income_percent,
                "discount": fargs.discount,
                "discount_percent": fargs.discount_percent,
                "equiped": False
            }

        embed = discord.Embed(
            title=fargs.name, description=fargs.description, color=rarity.__dict__[fargs.rarity])
        embed.set_author(name="Succesfully added to inventory",
                         icon_url=bot.user.avatar_url)
        embed.add_field(name="Type", value=fargs.type, inline=True)
        embed.add_field(name="Income", value=fargs.income, inline=True)
        embed.add_field(name="Income %",
                        value=fargs.income_percent, inline=True)
        embed.add_field(name="Discount", value=fargs.discount, inline=True)
        embed.add_field(name="Discount %",
                        value=fargs.discount_percent, inline=True)
        embed.add_field(name="Rarity", value=fargs.rarity, inline=True)
        await ctx.send(embed=embed)

        config.save()

    @commands.command(name="remove-player-item", help="Remove item from players inventory: remove-player-item <user: discord.Member> <item: str>")
    @commands.has_permissions(administrator=True)
    async def remove_player_item(self, ctx: Context, user: Union[str, discord.Member], *, item: str):
        if user == "loot-table":
            del config["loot-table"][item]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"✅ Removed {item} from loot-table"
            )
            embed.set_author(name="Remove player item",
                             icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        elif item in config["players"][user.id]["inventory"]:
            del config["players"][user.id]["inventory"][item]

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"✅ Removed {item} from <@{user.id}>´s inventory"
            )
            embed.set_author(name="Remove player item",
                             icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"❌ {item} not found in <@{user.id}>´s inventory"
            )
            embed.set_author(name="Remove player item",
                             icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        config.save()


class Player(commands.Cog):
    "Leveling up, upgrading stats"
    @commands.command(name="talents", help="Show list of skills: talents", aliases=["stats"])
    async def stats(self, ctx: Context):
        try:
            player = config["players"][ctx.author.id]["stats"]

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"""
                    Diplomacy: {player["diplomacy"]}
                    Warlord: {player["warlord"]}
                    Intrique: {player["intrique"]}
                    Stewardship: {player["stewardship"]}
                    Trading: {player["trading"]}
                    Bartering: {player["bartering"]}
                    Learning: {player["learning"]}""")
            embed.set_author(name="Stats", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="level", help="Show level, Xp and progress to another level")
    async def level(self, ctx: Context):
        try:
            await levelup_check(ctx)
            level = config["players"][ctx.author.id]["level"]

            xp_for_level = config["xp_for_level"]
            for _ in range(level):
                xp_for_level *= config["level_multiplier"]

            xp_for_level = int(xp_for_level)
            xp = config["players"][ctx.author.id]["xp"]

            if xp == 0:
                progress = 0
            else:
                progress = int((xp / xp_for_level) * 100)

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f'Level: {level}\nXp: {xp} / {xp_for_level}\n[{"#"*int(progress/2)+"-"*(50-int(progress/2))}] {progress}%'
            )
            embed.set_author(name="Level", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="levelup", help="Spend skillpoints for talents: levelup <skill> [value=1]")
    async def skill_add(self, ctx: Context, skill: str, value: int = 1):
        try:
            if skill.lower() in config["players"][ctx.author.id]["stats"]:
                if config["players"][ctx.author.id]["skillpoints"] >= value:
                    config["players"][ctx.author.id]["stats"][skill.lower()
                                                              ] += value
                    config["players"][ctx.author.id]["skillpoints"] -= value

                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f'Skill point used: {skill} = {config["players"][ctx.author.id]["stats"][skill.lower()]}'
                    )
                    embed.set_author(name="Add skill",
                                     icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                    config.save()
                else:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f'Not enought skillpoints'
                    )
                    embed.set_author(name="Add skill",
                                     icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f'No skill named {skill} found'
                )
                embed.set_author(name="Add skill",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="skillpoints", help="Number of your skillpoints: skillpoints")
    async def skillpoints(self, ctx: Context):
        try:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f'Your skillpoints: {config["players"][ctx.author.id]["skillpoints"]}'
            )
            embed.set_author(name="Skillpoints", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())


class Expeditions(commands.Cog):
    "Mission based game mechanics"

    @commands.command(name="add-expedition", help="Add new expedition: add-expedition [-h] [--manpower MANPOWER] [--level LEVEL] [--chance CHANCE] [--common COMMON] [--uncommon UNCOMMON] [--rare RARE] [--epic EPIC] [--legendary LEGENDARY] [--xp XP] [--description DESCRIPTION] name cost hours")
    @commands.has_permissions(administrator=True)
    async def add_mission(self, ctx: Context, *querry):
        fparser = argparse.ArgumentParser()
        fparser.add_argument("name", type=str)
        fparser.add_argument("cost", type=int)
        fparser.add_argument("hours", type=int)
        fparser.add_argument("--manpower", type=int, default=0)
        fparser.add_argument("--level", type=int, default=0)
        fparser.add_argument("--chance", type=int, default=100)
        fparser.add_argument("--common", type=float, default=1)
        fparser.add_argument("--uncommon", type=float, default=0)
        fparser.add_argument("--rare", type=float, default=0)
        fparser.add_argument("--epic", type=float, default=0)
        fparser.add_argument("--legendary", type=float, default=0)
        fparser.add_argument("--xp", type=int, default=0)
        fparser.add_argument("--description", default=None)

        querry = shlex.split(" ".join(querry))

        try:
            fargs = fparser.parse_args(querry)
        except SystemExit:
            return

        try:
            config["missions"][fargs.name] = {
                "cost": fargs.cost,
                "hours": fargs.hours,
                "manpower": fargs.manpower,
                "level": fargs.level,
                "chance": fargs.chance,
                "xp": fargs.xp,
                "description": fargs.description,
                "loot-table": {
                    "common": fargs.common,
                    "uncommon": fargs.uncommon,
                    "rare": fargs.rare,
                    "epic": fargs.epic,
                    "legendary": fargs.legendary,
                }
            }

            embed = discord.Embed(title=fargs.name, description=fargs.description,
                                  color=discord.Colour.from_rgb(255, 255, 0))
            embed.set_author(name="Succesfully added to missions",
                             icon_url=bot.user.avatar_url)
            embed.add_field(name="Cost", value=f"{fargs.cost:,}".replace(
                ",", " "), inline=True)
            embed.add_field(name="Hours", value=f"{fargs.hours:,}".replace(
                ",", " "), inline=True)
            embed.add_field(name="Required manpower", value=f"{fargs.manpower:,}".replace(
                ",", " "), inline=True)
            embed.add_field(name="Required Level",
                            value=fargs.level, inline=True)
            embed.add_field(name="Chance", value=str(
                fargs.chance) + "%", inline=True)
            embed.add_field(name="Xp", value=f"{fargs.xp:,}".replace(
                ",", " "), inline=True)
            embed.add_field(name="Common", value=str(
                fargs.common*100) + "%", inline=False)
            embed.add_field(name="Uncommon", value=str(
                fargs.uncommon*100) + "%", inline=False)
            embed.add_field(name="Rare", value=str(
                fargs.rare*100) + "%", inline=False)
            embed.add_field(name="Epic", value=str(
                fargs.epic*100) + "%", inline=False)
            embed.add_field(name="Legendary", value=str(
                fargs.legendary*100) + "%", inline=False)
            await ctx.send(embed=embed)

            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="remove-expedition", help="Remove expedition: remove-mission <mission: str>")
    @commands.has_permissions(administrator=True)
    async def remove_mission(self, ctx: Context, mission: str):
        try:
            try:
                del config["missions"][mission]
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"✅ Expedition removed"
                )
                embed.set_author(name="Remove expedition",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            except KeyError:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ Expedition not found"
                )
                embed.set_author(name="Remove expedition",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return
        except:
            print(traceback.format_exc())
            ctx.send(traceback.format_exc())

    @commands.command(name="expeditions", help="List of expeditions: expeditions")
    async def missions(self, ctx: Context):
        try:
            e_list = []
            index = 1
            for _mission in config["missions"]:
                mission = config["missions"][_mission]
                embed = discord.Embed(
                    title=_mission, description=mission["description"], color=discord.Colour.from_rgb(255, 255, 0))
                embed.set_author(name="Missions", icon_url=bot.user.avatar_url)
                embed.add_field(
                    name="Cost", value=mission["cost"], inline=True)
                embed.add_field(name="Manpower",
                                value=mission["manpower"], inline=True)
                embed.add_field(
                    name="Level", value=mission["level"], inline=True)
                embed.add_field(name="Chance", value=str(
                    mission["chance"]) + "%", inline=True)
                embed.add_field(name="Time to complete", value=str(
                    mission["hours"]) + "h", inline=True)
                embed.add_field(name="Xp", value=mission["xp"], inline=True)
                embed.add_field(name="Common", value=str(
                    mission["loot-table"]["common"]*100) + "%", inline=False)
                embed.add_field(name="Uncommon", value=str(
                    mission["loot-table"]["uncommon"]*100) + "%", inline=False)
                embed.add_field(name="Rare", value=str(
                    mission["loot-table"]["rare"]*100) + "%", inline=False)
                embed.add_field(name="Epic", value=str(
                    mission["loot-table"]["epic"]*100) + "%", inline=False)
                embed.add_field(name="Legendary", value=str(
                    mission["loot-table"]["legendary"]*100) + "%", inline=False)
                e_list.append(embed)
                index += 1

            if e_list == []:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ No expeditions yet"
                )
                embed.set_author(name="Expeditions",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="expedition", help="Start an expedition: expedition <name: str>", aliases=["mission-start"])
    async def mission_start(self, ctx: Context, mission_name: str):
        global time
        global asyncs_on_hold

        if config["block_asyncs"]:
            await ctx.send("Function blocked by 'hold-asyncs'")
            return

        user = ctx.author
        mission = config["missions"][mission_name]

        if not config["players"][user.id]["level"] >= mission["level"]:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"❌ Your level is too low"
            )
            embed.set_author(name="Expedition", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            return

        if not config["players"][user.id]["balance"] >= mission["cost"]:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"❌ Not enought money"
            )
            embed.set_author(name="Expedition", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            return

        if not config["players"][user.id]["manpower"] >= mission["manpower"]:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"❌ Not enought manpower"
            )
            embed.set_author(name="Expedition", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            return

        config["players"][user.id]["balance"] -= mission["cost"]
        config["players"][user.id]["manpower"] -= mission["manpower"]

        random.seed(time.time())

        _time = datetime.datetime.now(tz=pytz.timezone(
            'Europe/Prague')).strftime(r'%H:%M:%S')
        a_time = (datetime.datetime.now(tz=pytz.timezone('Europe/Prague')) +
                  datetime.timedelta(hours=mission["hours"])).strftime(r'%H:%M:%S')
        asyncs_on_hold.append(a_time)
        seconds = mission["hours"] * 3600

        embed = discord.Embed(title=mission_name, description=mission["description"]
                              if mission["description"] != None else "", color=discord.Colour.from_rgb(255, 255, 0))
        embed.set_author(name="Succesfully added to queue",
                         icon_url=bot.user.avatar_url)
        embed.add_field(name="Time", value=(datetime.datetime.now(tz=pytz.timezone(
            'Europe/Prague')) + datetime.timedelta(hours=mission["hours"])).strftime(r'%H:%M:%S'), inline=False)
        embed.add_field(name="Manpower on hold",
                        value=mission["manpower"], inline=False)
        embed.add_field(name="Required level",
                        value=mission["level"], inline=False)
        embed.add_field(name="Chance", value=mission["chance"], inline=False)
        embed.add_field(name="XP", value=mission["xp"], inline=False)
        await ctx.send(embed=embed)

        await asyncio.sleep(delay=seconds)
        await ctx.send("Mission started")

        if random.randint(0, 100) < mission["chance"]:
            msg = "✅ Successs"
            config["players"][user.id]["xp"] += mission["xp"] + mission["xp"] * \
                config["players"][ctx.author.id]["skills"]["learning"] * \
                config["learning_rate"]
            await levelup_check(ctx)

            if len(config["players"][ctx.author.id]["inventory"]) < config["max_player_items"]:

                rarities = mission["loot-table"]
                items = config["loot-table"]

                weighted_list = ['common'] * int(rarities["common"]*100) + ['uncommon'] * int(rarities["uncommon"]*100) + \
                    ['rare'] * int(rarities["rare"]*100) + ['epic'] * \
                    int(rarities["epic"]*100) + \
                    ['legendary'] * int(rarities["legendary"]*100)

                logging.debug(weighted_list)

                selected_rarity = random.choice(weighted_list)

                item_list = []

                for item in items:
                    if items[item]["rarity"] == selected_rarity:
                        item_list.append(item)

                if item_list != []:
                    chosen_item = random.choice(item_list)
                else:
                    chosen_item = None

                if chosen_item == None:
                    embed = discord.Embed(
                        colour=discord.Colour.from_rgb(255, 255, 0),
                        description=f"No item found"
                    )
                    embed.set_author(name="Expedition",
                                     icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                else:
                    name = chosen_item
                    item = config["loot-table"][chosen_item]
                    embed = discord.Embed(
                        title=name, description=item["description"] if item["description"] != None else "", color=rarity.__dict__[item["rarity"]])
                    embed.set_author(
                        name="Item found", icon_url=bot.user.avatar_url)
                    embed.add_field(
                        name="Type", value=item["type"], inline=True)
                    embed.add_field(
                        name="Income", value=item["income"], inline=True) if item["income"] != 0 else None
                    embed.add_field(
                        name="Income %", value=item["income_percent"], inline=True) if item["income_percent"] != 0 else None
                    embed.add_field(
                        name="Discount", value=item["discount"], inline=True) if item["discount"] != 0 else None
                    embed.add_field(
                        name="Discount %", value=item["discount_percent"], inline=True) if item["discount_percent"] != 0 else None
                    embed.add_field(
                        name="Rarity", value=item["rarity"], inline=True)
                    await ctx.send(embed=embed)

                    index = 1
                    while name in config["players"][ctx.author.id]["inventory"]:
                        name = name + f" ({index})"
                        index += 1
                        logging.debug(
                            f"Item found in inventory! Trying suffix ({index})")
                    config["players"][ctx.author.id]["inventory"][name] = item
            else:
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"Maximum item limit reached"
                )
                embed.set_author(name="Expedition",
                                 icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)

        else:
            msg = "❌ Failed"

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(255, 255, 0),
            description=f"<@{user.id}>´s mission from {_time}\n\n{msg}".replace(
                ",", " ")
        )
        embed.set_author(name="Expedition", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)

        config["players"][user.id]["manpower"] += mission["manpower"]

        asyncs_on_hold.remove(a_time)
        config.save()


class Battle(commands.Cog):
    "Combat system"

    @commands.command(name="manpower", help="Show manpower of user", aliases=["mp", "power"])
    async def manpower(self, ctx: Context, user: discord.Member = None):
        try:
            if user == None:
                user = ctx.author

            manpower = int(config['players'][user.id]['manpower'] + (config['players'][user.id]
                                                                     ['manpower']*config['players'][ctx.author.id]['stats']['warlord']*config['warlord_rate']))

            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"Manpower of <@{user.id}> is {manpower:,}\nWarlord boost: `{config['players'][ctx.author.id]['stats']['warlord']*config['warlord_rate']*100}%`".replace(
                    ",", " ")
            )
            embed.set_author(name="Manpower", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="attack", help="Automatized battle system")
    async def attack(self, ctx: Context, player_manpower: int, enemy_manpower: int, hours: float, player_support: int = 0, enemy_support: int = 0, skip_colonization: str = "false", income: int = 0, income_role: discord.Role = None):
        global time
        global asyncs_on_hold

        if config["block_asyncs"]:
            await ctx.send("Function blocked by 'hold-asyncs'")
            return

        random.seed(time.time())

        _time = datetime.datetime.now(tz=pytz.timezone(
            'Europe/Prague')).strftime(r'%H:%M:%S')
        a_time = (datetime.datetime.now(tz=pytz.timezone('Europe/Prague')
                                        ) + datetime.timedelta(hours=hours)).strftime(r'%H:%M:%S')
        asyncs_on_hold.append(a_time)
        pstart, estart = player_manpower, enemy_manpower
        seconds = hours * 3600

        if hours > config["maximum_attack_time"]:
            logging.debug(f"Reached max attack time limit")
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"❌ Attack can be postponed for maximum of {config['maximum_attack_time']}h"
            )
            await ctx.send(embed=embed)
            return

        if skip_colonization == "false":
            if config["players"][ctx.author.id]["balance"] < estart:
                logging.debug(f"Not enought money for colonization")
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(255, 255, 0),
                    description=f"❌ Not enought money for colonization"
                )
                await ctx.send(embed=embed)
                return
            else:
                config["players"][ctx.author.id]["balance"] -= estart

        if config["players"][ctx.author.id]["manpower"] >= pstart:
            config["players"][ctx.author.id]["manpower"] -= pstart
        else:
            logging.debug(f"Not enought forces")
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(255, 255, 0),
                description=f"❌ Not enought manpower"
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="Attack", description=f"<@{ctx.author.id}>", color=discord.Colour.from_rgb(255, 255, 0))
        embed.set_author(name="Succesfully added to queue",
                         icon_url=bot.user.avatar_url)
        embed.add_field(name="Time", value=(datetime.datetime.now(tz=pytz.timezone(
            'Europe/Prague')) + datetime.timedelta(hours=hours)).strftime(r'%H:%M:%S'), inline=False)
        embed.add_field(name="Your manpower",
                        value=player_manpower, inline=False)
        embed.add_field(name="Enemy manpower",
                        value=enemy_manpower, inline=False)
        embed.add_field(name="Your support",
                        value=player_support, inline=False)
        embed.add_field(name="Enemy support",
                        value=enemy_support, inline=False)
        embed.add_field(name="Role getting income",
                        value=f"@{income_role}" if income_role != None else "None", inline=False)
        embed.add_field(name="Income", value=income, inline=False)
        await ctx.send(embed=embed)

        await asyncio.sleep(delay=seconds)
        await ctx.send("Battle started")

        if player_support > 0:
            player_support_roll = random.randint(0, player_support)
            enemy_manpower -= player_support_roll

        enemy_manpower = max(enemy_manpower, 0)

        if enemy_support > 0:
            enemy_support_roll = random.randint(0, enemy_support)
            player_manpower -= enemy_support_roll

        player_manpower = max(player_manpower, 0)

        iteration = 1

        while iteration <= 3:
            if enemy_manpower > 0 and player_manpower > 0:
                print(
                    f"Rolling: {player_manpower} | {enemy_manpower}: roll - {iteration}")
                e_before_roll = enemy_manpower
                player_roll = random.randint(0, player_manpower)
                enemy_manpower -= player_roll
                enemy_manpower = max(enemy_manpower, 0)

                if enemy_manpower > 0:
                    enemy_roll = random.randint(0, enemy_manpower)
                    player_manpower -= enemy_roll
                if enemy_manpower == 0:
                    enemy_roll = random.randint(0, e_before_roll)
                    player_manpower -= enemy_roll

                player_manpower = max(player_manpower, 0)

            iteration += 1

        if iteration == 4 and player_manpower > 0 and enemy_manpower > 0:
            msg = "❌ Out of rolls"
            if skip_colonization == "false":
                config["players"][ctx.author.id]["balance"] += estart
        elif player_manpower > 0 and enemy_manpower == 0:
            msg = "✅ You won"

            if config["allow_attack_income"]:
                if income_role != None:
                    if income >= 200000:
                        ctx.send("Income too high, ask admin to add it")
                    else:
                        config["income"][income_role.id] += income
        elif player_manpower == 0 and enemy_manpower > 0:
            msg = "❌ You lost"
            if skip_colonization == "false":
                config["players"][ctx.author.id]["balance"] += estart
        else:
            msg = "❓ Tie ❓"
            if skip_colonization == "false":
                config["players"][ctx.author.id]["balance"] += estart

        config["players"][ctx.author.id]["manpower"] += player_manpower

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(255, 255, 0),
            description=f"<@{ctx.author.id}>´s attack from {_time}\n\n{msg}\n\n`Before battle:`\n    Your army: {pstart:,}\n    Enemy army: {estart:,}\n\n`After battle:`\n    Your army: {player_manpower:,}\n    Enemy army: {enemy_manpower:,}\n\n`Casualties:`\n    Your army: {pstart-player_manpower:,}\n    Enemy army: {estart-enemy_manpower}".replace(
                ",", " ")
        )
        embed.set_author(name="Attack", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)

        asyncs_on_hold.remove(a_time)
        config.save()


bot.add_cog(Money())
bot.add_cog(Income())
bot.add_cog(Essentials())
bot.add_cog(Config())
bot.add_cog(Development())
bot.add_cog(Settings())
bot.add_cog(PlayerShop())
bot.add_cog(Inventory())
bot.add_cog(Player())
bot.add_cog(Expeditions())
bot.add_cog(Battle())

bot.run(args.token)
