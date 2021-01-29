import discord
import sys
import re
import os
import json
import datetime
import pytz
import random
import time
import platform
import traceback
from discord.ext import commands
from discord.ext.commands.context import Context
from discord.utils import get
from pretty_help import PrettyHelp
import DiscordUtils

class c:
    header = '\033[95m'
    okblue = '\033[94m'
    okgreen = '\033[92m'
    warning = '\033[93m'
    fail = '\033[91m'
    end = '\033[0m'
    bold = '\033[1m'
    underline = '\033[4m'

members = []

def jsonKeys2int(x):
    if isinstance(x, dict):
        try: return {int(k):v for k,v in x.items()}
        except: pass
    return x

def print_timestamp(*_str):
    print(f"{c.bold}[{c.end}{c.warning}{datetime.datetime.now(tz=pytz.timezone('Europe/Prague')).strftime(r'%H:%M:%S')}{c.end}{c.bold}]{c.end}", *_str)

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

class Config():
    "Class for maintaining configuration information and files"
    def print_timestamp(self,*_str):
        print(f"{c.bold}[{c.end}{c.warning}{datetime.datetime.now(tz=pytz.timezone('Europe/Prague')).strftime('%H:%M:%S')}{c.end}{c.bold}]{c.end}", *_str)

    def load(self):
        self.print_timestamp(f"{c.bold}Loading config...{c.end}")
        try:
            self.print_timestamp(f"{c.bold}Loading:{c.end} {c.okgreen}{self.CONFIG}{c.end}")
            self.config = json.load(open(self.CONFIG), object_hook=jsonKeys2int)
            type(self.config.keys())
        except Exception as e:
            self.print_timestamp(traceback.format_exc())
            self.print_timestamp(f"{c.warning}Config is unavailable or protected.{c.end} {c.bold}Loading fallback...{c.end}")
            self.config = self.fallback
            self.print_timestamp(f"{c.bold}Fallback loaded{c.end}")
            try:
                self.print_timestamp(f"{c.bold}Creating new config file:{c.end} {c.okgreen}{self.CONFIG}{c.end}")
                self.save()
            except Exception as e:
                self.print_timestamp(traceback.format_exc())
                self.print_timestamp(f"{c.fail}Error writing config file, please check if you have permission to write in this location:{c.end} {c.bold}{self.CONFIG}{c.end}")
                return
        self.print_timestamp(f"{c.bold}Config loaded{c.end}")

    def __init__(self):
        if platform.system() == "Windows":
            self.CONFIG = os.environ["userprofile"] + "\\.economy" # Rename this
        else:
            self.CONFIG = os.path.expanduser("~")+r"/.economy" # Rename this ... alternative for linux or Unix based systems
        self.config = {}
        self.fallback = {
            "income":{},
            "prefix": "-",
            "players": {},
            "currency_symbol":"$",
            "admin_role_name":["Admin", "Programátor"],
            "upgrade": {},
            "maxupgrade": {
                "doly-na-železo": 0,
                "doly-na-uhlí": 0,
                "ropná-plošina": 0,
                "rafinérie": 5,
                "továrna": 25,
                "doly-na-uran": 0,
                "reaktor": 1
            },
            "disabled_roles": ["@everyone"],
            "deltatime": 7200,
            "default_role":"",
            "work_range": 0,
            "default_balance": 0
        }

    def save(self):
        try:
            with open(self.CONFIG, "w") as f:
                json.dump(self.config, f, indent=4)
        except:
            self.print_timestamp(traceback.format_exc())
            self.print_timestamp(f"Unable to save data to {self.CONFIG}")

    def json_str(self):
        return json.dumps(self.config)

    def __repr__(self):
        return self.config

    def __getitem__(self, name: str):
        try:
            return self.config[name]
        except:
            self.print_timestamp(f"{c.warning}Not found in config, trying to get from fallback{c.end}")
            self.config[name] = self.fallback[name]
            return self.fallback[name]

    def __setitem__(self, key: str, val):
        self.config[key] = val

    def __delitem__(self, key: str):
        self.config.pop(key)


#region Initialize
config = Config()
config.load()

ADMIN = config["admin_role_name"]

bot = commands.Bot(command_prefix=config["prefix"], help_command=PrettyHelp(color=discord.Colour.from_rgb(255,255,0), show_index=True, sort_commands=True))

members = list(config["players"].keys())
roles = list(config["income"].keys())
#endregion


#region Events
@bot.event
async def on_ready():
    print_timestamp(f'{c.bold}Initialized:{c.end} {c.okgreen}{bot.user}{c.end} - {c.okblue}{bot.user.id}{c.end}')
    for member in bot.guilds[0].members:
        if not member.id in config.config["players"]:
            members.append(member.id)
            print_timestamp(f"Added {c.okgreen}{member.display_name}{c.end} as {c.bold}{member.id}{c.end}")
            config.config["players"][member.id] = {}
            config.config["players"][member.id]["balance"] = config["default_balance"]
            config.config["players"][member.id]["last-work"] = 0
            config.config["players"][member.id]["upgrade"] = {}
            config.config["players"][member.id]["maxupgrade"] = {}
            
            for item in list(config["upgrade"].keys()):
                print_timestamp(f"Added {c.okgreen}{item}{c.end} to {c.bold}{member.display_name}{c.end}")
                config.config["players"][member.id]["upgrade"][item] = 0
                config.config["players"][member.id]["maxupgrade"][item] = config["maxupgrade"][item]

    for role in bot.guilds[0].roles:
        if not (role.id in roles):
            print_timestamp(f"{c.bold}{role}{c.end} added to config")
            config["income"][role.id] = 0
    
    config.save()
    print_timestamp(f"{c.bold}Members:{c.end} {c.okgreen}{members}{c.end}")
    print_timestamp(f"{c.bold}Roles:{c.end} {c.okgreen}{list(config['income'].keys())}{c.end}")
    print_timestamp(f"{c.bold}Upgrades:{c.end} {c.okgreen}{list(config['upgrade'].keys())}{c.end}")
    print(f"\n{c.bold}{'-'*100}{c.end}\n")

    await bot.change_presence(activity=discord.Game(name=f"Try: {config['prefix']}"))
    print_timestamp()

@bot.event
async def on_message(message):
    if not message.author == bot.user:
        print_timestamp(f"{c.bold}{message.author.display_name} ■ {message.author.id}:{c.end} {c.okgreen}{message.content}{c.end}")
        await bot.process_commands(message)

@bot.event
async def on_member_join(member: discord.Member):
    if not member.id in config.config["players"]:
        members.append(member.id)
        print_timestamp(f"Added {c.okgreen}{member.display_name}{c.end} as {c.bold}{member.id}{c.end}")
        config.config["players"][member.id] = {}
        config.config["players"][member.id]["balance"] = config["default_balance"]
        config.config["players"][member.id]["last-work"] = 0
        config.config["players"][member.id]["upgrade"] = {}
        config.config["players"][member.id]["maxupgrade"] = {}
        config.config["players"][member.id]["custom_shop"] = {}
        config.config["players"][member.id]["custom_shop"]["inventory"] = {}
        config.config["players"][member.id]["custom_shop"]["shop"] = {}

        for item in config["upgrade"].keys():
            print_timestamp(f"Added {c.okgreen}{item}{c.end} to {c.bold}{member.display_name}{c.end}")
            config.config["players"][member.id]["upgrade"][item] = 0
            config.config["players"][member.id]["maxupgrade"][item] = config["maxupgrade"][item]
    print_timestamp(f"{c.bold}{member.display_name} ■ {member.id}{c.end} joined")

    config.save()
#endregion



class Money(commands.Cog):
    """Whatya dooooing, make money !!!"""

    @commands.command(name="leaderboard", help="Show da leaderboard: l, lb, leaderboard", aliases=["lb", "l"])
    async def leaderboard(self, ctx: Context):
        try:
            players = {}
            for player in config["players"]:
                players[player] = config["players"][player]["balance"]
            _sorted = {k: v for k, v in sorted(players.items(), key=lambda item: item[1], reverse=True)}

            e_list = []
            msg = ""
            index = 1
            for name in _sorted:
                try:
                    username = get(bot.guilds[0].members, id=name).display_name
                except:
                    continue
                msg += f"{index}. {username} `{_sorted[name]:,}{config['currency_symbol']}`\n".replace(",", " ")
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Leaderboard", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
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
        try:
            if time.time() >= config["players"][ctx.author.id]["last-work"] + config["deltatime"]:
                money = 0
                for role in ctx.author.roles:
                    if config.config["income"][role.id] != 0:
                        money += config.config["income"][role.id]
                if money <= 0:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = f"❌ You do not have income set, please ask admin to do so"
                    )
                    embed.set_author(name="Work", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                else:
                    rate = random.randrange(100-config["work_range"]*100,100+config["work_range"]*100) / 100 if config["work_range"] != 0 else 1
                    if config["players"][ctx.author.id]["last-work"] != 0:
                        timedelta = (time.time() - config["players"][ctx.author.id]["last-work"]) / config["deltatime"]
                        config["players"][ctx.author.id]["balance"] += int(money * timedelta * rate)
                        config["players"][ctx.author.id]["last-work"] = time.time()
                    else:
                        timedelta = 1
                        config["players"][ctx.author.id]["balance"] += money
                        config["players"][ctx.author.id]["last-work"] = time.time()

                    print_timestamp(f"{c.bold}{ctx.author.display_name} ■ {ctx.author.id}{c.end} is working {c.warning}[timedelta={timedelta}, rate={rate}]{c.end}")
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = f"✅ <@{ctx.author.id}> worked and got `{int(timedelta*money*rate):,} {config['currency_symbol']}`. Next available at {datetime.datetime.fromtimestamp(int(config['players'][ctx.author.id]['last-work'] + config['deltatime']),tz=pytz.timezone('Europe/Prague')).time()}".replace(",", " ")
                    )
                    embed.set_author(name="Work", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"❌ You can work at {datetime.datetime.fromtimestamp(int(config['players'][ctx.author.id]['last-work']+config['deltatime']),tz=pytz.timezone('Europe/Prague')).time()}"
                )
                embed.set_author(name="Work", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="reset-money", help="Reset balance of target: reset-money <user: discord.Member>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def reset_money(self, ctx: Context, member: discord.Member):
        try:
            if member.id in members:
                config["players"][member]["balance"] = 0
                print_timestamp(f"Resetting {member}'s balance")
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Resetting <@{member.id}>'s balance"
                )
                embed.set_author(name="Reset money", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else: 
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "Member not found"
                )
                embed.set_author(name="Reset money", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                print_timestamp("Member not found")
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="remove-money", help="Remove money from target: remove-money <user: discord.Member> <value: integer>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def remove_money(self, ctx: Context, member: discord.Member, balance: int):
        try:
            if member.id in members:
                config["players"][member.id]["balance"] -= abs(int(balance))
                print_timestamp(f"Removing {balance:,}{config['currency_symbol']} from {member}".replace(",", " "))
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Removing {balance}{config['currency_symbol']} from <@{member.id}>"
                )
                embed.set_author(name="Remove money", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "Member not found"
                )
                embed.set_author(name="Remove money", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                print_timestamp("Member not found")
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="add-money", help="Add money to target: add-money <user: discord.Member> <value: integer>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def add_money(self, ctx: Context, *message):
        try:
            if message[0] == "everyone":
                money = message[1]
                for _member in config["players"]:
                    config["players"][_member]["balance"] += int(money)
                config.save()
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Adding {int(money):,}{config['currency_symbol']} to @everyone".replace(",", " ")
                )
                embed.set_author(name="Add money", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            pattern = re.compile(r'[0-9]+')
            _users = bot.guilds[0].members
            _id = int(re.findall(pattern, message[0])[0])
            for _user in _users:
                if _user.id == _id:
                    member = _user.id
            balance = float(message[1])
            if member in members:
                config["players"][member]["balance"] += abs(int(balance))
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Adding {balance:,}{config['currency_symbol']} to <@{_id}>".replace(",", " ")
                )
                embed.set_author(name="Add money", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                print_timestamp(f"Adding {balance} to {member}")
            else:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "Member not found"
                )
                embed.set_author(name="Add money", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                print_timestamp("Member not found")
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="buy", help="Spend money to make more money bruh: buy <type: string> <value: integer>")
    async def buy_upgrade(self, ctx: Context, type: str, value: int):
        try:
            if type in config["upgrade"].keys():
                if config["players"][ctx.author.id]["upgrade"][type] + int(value) <= config["players"][ctx.author.id]["maxupgrade"][type]:
                    cost = config["upgrade"][type]["cost"] * int(value)
                    if config.config["players"][ctx.author.id]["balance"] >= cost:
                        role_list = []
                        for role in ctx.author.roles:
                            if not role.name in config["disabled_roles"] or not "spokojenost" in role.name.lower():
                                try:
                                    if config["income"][role.id] != 0:
                                        role_list.append(role.id)
                                except:
                                    embed = discord.Embed(
                                        colour = discord.Colour.from_rgb(255,255,0),
                                        description = f"ERROR: {role.name} not found in config"
                                    )
                                    embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                                    await ctx.send(embed=embed)
                                    return
                        if len(role_list) > 1:
                            embed = discord.Embed(
                                colour = discord.Colour.from_rgb(255,255,0),
                                description = f"ERROR: Multiple roles to add income to: `{role_list}`"
                            )
                            embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                            await ctx.send(embed=embed)
                            return
                        elif len(role_list) == 0 and config["upgrade"][type]["income"] != 0:
                            embed = discord.Embed(
                                colour = discord.Colour.from_rgb(255,255,0),
                                description = "❌ No role to add income to"
                            )
                            embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                            await ctx.send(embed=embed)
                            config.save()
                        else:
                            config.config["income"][role_list[0]] += config["upgrade"][type]["income"] * int(value)
                            config["players"][ctx.author.id]["upgrade"][type] += int(value)
                            config.config["players"][ctx.author.id]["balance"] -= config["upgrade"][type]["cost"] * int(value)
                            if config["upgrade"][type]["income"] != 0:
                                embed = discord.Embed(
                                    colour = discord.Colour.from_rgb(255,255,0),
                                    description = f"✅ Bought {value}x {type} for {cost:,}{config['currency_symbol']} and your income is now {config.config['income'][role_list[0]]:,}{config['currency_symbol']}".replace(",", " ")
                                )
                                embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                                await ctx.send(embed=embed)
                            else:
                                embed = discord.Embed(
                                    colour = discord.Colour.from_rgb(255,255,0),
                                    description = f"✅ Bought {value}x {type} for {cost:,}{config['currency_symbol']}".replace(",", " ")
                                )
                                embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                                await ctx.send(embed=embed)
                            config.save()
                    else:
                        embed = discord.Embed(
                            colour = discord.Colour.from_rgb(255,255,0),
                            description = "❌ Not enought money"
                        )
                        embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = "❌ You cannot purchase more items of this type"
                    )
                    embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
            else:
                print_timestamp(f"{c.fail}Invalid type or value{c.end}")
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "❌ Invalid type or value"
                )
                embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="pay", help="Send money to target: pay <user: discord.Member> <value: int>")
    async def user_pay(self, ctx: Context, member: discord.Member, balance: int):
        try:
            if balance < 1:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"❌ Invalid value"
                )
                embed.set_author(name="Pay", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                if config["players"][ctx.author.id]["balance"] >= balance:
                    if member.id in members:
                        config["players"][ctx.author.id]["balance"] -= int(balance)
                        config.config["players"][member.id]["balance"] += int(balance)
                        print_timestamp(f"Paid {balance} to {member}")
                        embed = discord.Embed(
                            colour = discord.Colour.from_rgb(255,255,0),
                            description = f"✅ Paid {balance:,}{config['currency_symbol']} to <@{member.id}>".replace(",", " ")
                        )
                        embed.set_author(name="Pay", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            colour = discord.Colour.from_rgb(255,255,0),
                            description = "❌ Member not found"
                        )
                        embed.set_author(name="Pay", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                        print_timestamp("Member not found")
                else:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = "❌ You don't have enough money"
                    )
                    embed.set_author(name="Pay", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)

            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="balance", help="Show your balance or more likely, empty pocket: b, bal, balance, money", aliases=["bal","b","money"])
    async def bal(self, ctx: Context):
        try:
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"<@{ctx.author.id}> has {config['players'][ctx.author.id]['balance']:,}{config['currency_symbol']}".replace(",", " ")
            )
            embed.set_author(name="Balance", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())



class Income(commands.Cog):
    """Everything about income"""

    @commands.command(name="income-calc", help="Calculate income: income <populace>")
    async def income_calc(self, ctx: Context, *message):
        try:
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"Income: {(int(message[0]) * 0.01 * 0.4 / 6):,}{config['currency_symbol']}".replace(",", " ")
            )
            embed.set_author(name="Role", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="income", help="Shows your income: income")
    async def income(self, ctx: Context):
        try:
            money = 0
            for role in ctx.author.roles:
                try:
                    if config.config["income"][role.id] != 0:
                        money += config.config["income"][role.id]
                    else:
                        print_timestamp(f"Excluding: {role.name}")
                except:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = f"ERROR: {role.name} not found in config"
                    )
                    embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"Income: `{money:,}{config['currency_symbol']}`".replace(",", " ")
            )
            embed.set_author(name="Income", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="add-income", pass_context=True, help="Add income: add-income <role: discord.Role> <value: integer>")
    @commands.has_any_role(*config["admin_role_name"])
    async def add_income(self, ctx: Context, role, value: int):
        try:
            if value > 0:
                defrole = role
                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), role) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].roles
                    _id = int(re.findall(pattern, role)[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{role} was replaced by {_user.id}")
                            role = _user.id
                
                config.config["income"][role] += value

                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Added: `{value:,}{config['currency_symbol']}` to income of {defrole}".replace(",", " ")
                )
                embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Invalid value"
                )
                embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="remove-income", pass_context=True, help="Remove income: remove-income <role: discord.Role> <value: integer>")
    @commands.has_any_role(*config["admin_role_name"])
    async def remove_income(self, ctx: Context, role, value: int):
        try:
            if value > 0:
                defrole = role
                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), role) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].roles
                    _id = int(re.findall(pattern, role)[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{role} was replaced by {_user.id}")
                            role = _user.id
                
                config.config["income"][role] -= value

                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Removed: `{value:,}{config['currency_symbol']}` from income of {defrole}".replace(",", " ")
                )
                embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"Invalid value"
                )
                embed.set_author(name="Income", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="income-lb", help="Show da income leaderboard: l, lb, leaderboard")
    async def income_lb(self, ctx: Context):
        try:
            roles = config["income"]
            _sorted = {k: v for k, v in sorted(roles.items(), key=lambda item: item[1], reverse=True)}

            e_list = []
            msg = ""
            index = 1
            for _id in _sorted:
                try:
                    role = get(bot.guilds[0].roles, id=_id).name
                except:
                    pass
                msg += f"{index}. {role} `{_sorted[_id]:,}{config['currency_symbol']}`\n".replace(",", " ")
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Income Leaderboard", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
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
    @commands.has_any_role(*config["admin_role_name"])
    async def config_save(self, ctx: Context):
        try:
            config.save()
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = "✅ Config saved"
            )
            embed.set_author(name="Config", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="config-load", help="Load configuration file: config-load", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def config_load(self, ctx: Context):
        try:
            config.load()
            config.save()
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = "✅ Config loaded"
            )
            embed.set_author(name="Config", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="config", help="Output config directory: config <path> [path]...", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def _config(self, ctx: Context, *message):
        try:
            message = list(message)
            for i in range(len(message)):
                if re.findall(re.compile(r"[<][@][!][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break
                
                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _roles = bot.guilds[0].roles
                    _id = int(re.findall(pattern, message[i])[0])
                    for _role in _roles:
                        if _role.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_role.id}")
                            message[i] = _role.id
                    break

            msg = ""
            if message == []:
                for item in config.config:
                    msg += f"`{item}`\n"
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = msg
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
                                colour = discord.Colour.from_rgb(255,255,0),
                                description = "Not found"
                            )
                            embed.set_author(name="Config", icon_url=bot.user.avatar_url)
                            await ctx.send(embed=embed)
                            break
                        try:
                            for name in current:
                                msg += f"`{name}`\n"
                        except:
                            msg += f"`{current}`"
                        embed = discord.Embed(
                            colour = discord.Colour.from_rgb(255,255,0),
                            description = msg
                        )
                        embed.set_author(name="Config", icon_url=bot.user.avatar_url)
                        await ctx.send(embed=embed)
                        break
                    else:
                        current = current[word]
            config.save()

        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="set", help="Change values in config. You rather know what ya doin!: set <path> [path]... = <value>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def set(self, ctx: Context, *message):
        try:
            message = list(message)
            for i in range(len(message)):
                if re.findall(re.compile(r"[<][@][!][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break
                
                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _roles = bot.guilds[0].roles
                    _id = int(re.findall(pattern, message[i])[0])
                    for _role in _roles:
                        if _role.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_role.id}")
                            message[i] = _role.id
                    break

            current = config.config
            last = message[message.index("=") - 1]
            for word in message:
                if word == last:
                    try:
                        current[last] = int(message[-1])
                    except:
                        try:
                            current[last] = float(message[-1])
                        except:
                            current[last] = message[-1]
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = "Success"
                    )
                    embed.set_author(name="Set", icon_url=bot.user.avatar_url)
                    await ctx.send(embed=embed)
                    break
                else:
                    current = current[word]
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="config-stats", help="Config stats: config-stats", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def config_stats(self, ctx: Context):
        size = os.path.getsize(config.CONFIG)
        embed = discord.Embed(
            colour = discord.Colour.from_rgb(255,255,0),
            description = f"Size: {sizeof_fmt(size)}\nPath: {config.CONFIG}\nLines: {sum(1 for line in open(config.CONFIG))}"
        )
        embed.set_author(name="Config-stats", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)



class Development(commands.Cog):
    """Only for developers, who know how to operate this bot"""

    @commands.command(name="json-encode", help="Encode string to yaml format: json-encode <value: string>", pass_context=True)
    async def yaml_encode(self, ctx: Context, *message):
        try:
            message = " ".join(message)
            await ctx.send(json.dumps(message))
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="reload", help="Reload members and roles: reload")
    @commands.has_any_role(*config["admin_role_name"])
    async def reload(self, ctx: Context):
            try:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "Reloading members..."
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
                            print_timestamp(f"Added {c.okgreen}{item}{c.end} to {c.bold}{member.display_name}{c.end}")
                            config.config["players"][member.id]["upgrade"][item] = 0
                            config.config["players"][member.id]["maxupgrade"][item] = config["maxupgrade"][item]
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "✅ Members reloaded"
                )
                embed.set_author(name="Reload", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)

                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "Reloading roles..."
                )
                embed.set_author(name="Reload", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)

                for role in bot.guilds[0].roles:
                    if not (role.id in roles):
                        print_timestamp(f"{c.bold}{role}{c.end} added to config")
                        config.config["income"][role.id] = 0

                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "✅ Roles reloaded"
                )
                embed.set_author(name="Reload", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                config.save()
            except:
                print(traceback.format_exc())
                await ctx.send(traceback.format_exc())

    @commands.command(name="python3", help="Execute python code: python3 <command>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def python3(self, ctx: Context, *message):
        try:
            message = list(message)
            for i in range(len(message)):
                if re.findall(re.compile(r"[<][@][!][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break

                if re.findall(re.compile(r"[<][@][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _users = bot.guilds[0].members
                    _id = int(re.findall(pattern, message[i])[0])
                    for _user in _users:
                        if _user.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_user.id}")
                            message[i] = _user.id
                    break
                
                if re.findall(re.compile(r"[<][@][&][0-9]+[>]"), message[i]) != []:
                    pattern = re.compile(r'[0-9]+')
                    _roles = bot.guilds[0].roles
                    _id = int(re.findall(pattern, message[i])[0])
                    for _role in _roles:
                        if _role.id == _id:
                            print_timestamp(f"{message[i]} was replaced by {_role.id}")
                            message[i] = _role.id
                    break
            
            result = eval(" ".join(message))
            await ctx.send(result)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="execute", help="Execute python code: execute <command>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def config_save(self, ctx: Context, *message):
        try:
            message = list(message)
            result = exec(" ".join(message))
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())



class Settings(commands.Cog):
    """Modify settings"""

    @commands.command(name="shutdown", help="Show the bot, whos da boss: shutdown", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def shutdown(self, ctx: Context):
        embed = discord.Embed(
            colour = discord.Colour.from_rgb(255,255,0),
            description = "✅ Shutting down..."
        )
        embed.set_author(name="Shutdown", icon_url=bot.user.avatar_url)
        await ctx.send(embed=embed)
        print_timestamp("Shutting down...")
        sys.exit()

    @commands.command(name="add-item", pass_context=True, help="Add item to database: add-item <name: string> <cost: integer> <max: integer> [income: integer]")
    @commands.has_any_role(*config["admin_role_name"])
    async def add_item(self, ctx: Context, *message):
        try:
            try: item = message[0]
            except:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"No name specified"
                )
                embed.set_author(name="Add item", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            try: cost = int(message[1])
            except:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"No cost specified"
                )
                embed.set_author(name="Add item", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            try: maximum = int(message[2])
            except: maximum = 0

            try: income = int(message[3])
            except: income = 0

            for member in config.config["players"]:
                config["players"][member]["maxupgrade"] = {**config["players"][member]["maxupgrade"], **{item: maximum}}
                config["players"][member]["upgrade"] = {**config["players"][member]["upgrade"], **{item: 0}}
            
            config["upgrade"] = {**config["upgrade"], **{item: {"cost": cost,"income": income}}}
            config["maxupgrade"] = {**config["maxupgrade"], **{item: maximum}}

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"Added: `{item}`\nMaximum: {maximum}\nIncome: {income}\nCost: {cost}"
            )
            embed.set_author(name="Add item", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            
            config.save()

        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="remove-item", pass_context=True, help="Remove item from database: remove-item <name: string>")
    @commands.has_any_role(*config["admin_role_name"])
    async def remove_item(self, ctx: Context, item: str):
        try:
            try: item
            except:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"No name specified"
                )
                embed.set_author(name="Remove item", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
                return

            for member in config.config["players"]:
                config["players"][member]["maxupgrade"].pop(item)
                config["players"][member]["upgrade"].pop(item)
            
            config["upgrade"].pop(item)
            config["maxupgrade"].pop(item)

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"Sucessfully removed `{item}`"
            )
            embed.set_author(name="Remove item", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            return
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="prefix", help="Change prefix of da bot: prefix <prefix: string>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def command_prefix(self, ctx: Context, prefix: str):
        try:
            config.config["prefix"] = prefix
            config.save()
            commands.command_prefix = prefix
            print_timestamp(f"Prefix changed to {config['prefix']}")
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"✅ Prefix changed to {prefix}"
            )
            embed.set_author(name="Prefix", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="deltatime", help="Sets time between allowed !work commands: deltatime <value: integer>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def deltatime(self, ctx: Context, value: int):
        try:
            config["deltatime"] = int(value)
            config.save()
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"✅ Deltatime changed to {int(value)} seconds"
            )
            embed.set_author(name="Config", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
            config.save()
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="bravo-six-going-dark", help="Deletes messages: bravo-six-going-dark <messages: integer>", pass_context=True)
    @commands.has_any_role(*config["admin_role_name"])
    async def deltatime(self, ctx: Context, messages: int):
        await ctx.channel.purge(limit=messages)



class Essentials(commands.Cog):
    """Other usefull commands"""

    @commands.command(name="members", help="Show all members: members")
    async def members(self, ctx: Context):
        try:
            e_list = []
            msg = ""
            index = 1
            for user in bot.guilds[0].members:
                msg += f"{index}. {user.display_name} `{user.id}`\n"
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Members", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
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
                msg += f"{index}. {role.name}\n"
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Roles", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
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
                colour = discord.Colour.from_rgb(255,255,0),
                description = "✅ " + str(random.randint(0, int(value)))
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
                colour = discord.Colour.from_rgb(255,255,0),
                description = "✅ " + datetime.datetime.now(tz=pytz.timezone('Europe/Prague')).strftime(r"%H:%M:%S, %d/%m/%Y")
            )
            embed.set_author(name="Time", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="limits", help="Shows upgrade limits for your account: limits")
    async def limits(self, ctx: Context):
        try:
            l = config["players"][ctx.author.id]["maxupgrade"]

            e_list = []
            msg = ""
            index = 1
            for name in l:
                msg += f"{index}. {name} `{l[name]}`\n"
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Limits", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
            )
            embed.set_author(name="Limits", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="upgrades", help="Shows the current number of upgrades bought: upgrades")
    async def upgrades(self, ctx: Context):
        try:
            l = config["players"][ctx.author.id]["upgrade"]
            msg = ""
            index = 1
            for name in l:
                msg += f"{index}. {name} `{l[name]}`\n"
                index += 1
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
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
                msg += f"{name} `{name.id}`\n"
                index += 1
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
            )
            embed.set_author(name="Role", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="shop", help="Show shop")
    async def shop(self, ctx: Context, *message):
        try:
            e_list = []
            index = 1
            msg = ""
            for item in config["upgrade"]:
                msg += f'`{item}` {config["players"][ctx.author.id]["upgrade"][item]}/{config["players"][ctx.author.id]["maxupgrade"][item]} `Cost:` {config["upgrade"][item]["cost"]:,}{config["currency_symbol"]}\n'.replace(",", " ")
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Shop", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1
            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
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
    async def player_shop(self, ctx: Context, player: discord.Member = None):
        try:
            e_list = []
            index = 1
            msg = ""
            if player == None:
                player = ctx.author
            for item in config["players"][player.id]["custom_shop"]["shop"]:
                msg += f'`{item}` | `Cost:` {config["players"][player.id]["custom_shop"]["shop"][item]:,}{config["currency_symbol"]}\n'.replace(",", " ")
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Custom shop", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
            )
            embed.set_author(name="Custom shop", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

    @commands.command(name="player-sell", help="Sell items: player-sell <item: str> <price: int>")
    async def player_sell(self, ctx: Context, item: str, price: int):
        try:
            config["players"][ctx.author.id]["custom_shop"]["shop"] = {**config["players"][ctx.author.id]["custom_shop"]["shop"], **{item: price}}

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = f"Added: `{item}`\nPrice: {price}"
            )
            embed.set_author(name="Sell", icon_url=bot.user.avatar_url)
            await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="player-buy", help="Sell items: player-buy <user: discord.Member> <item: str> <count: int>")
    async def sell(self, ctx: Context, user: discord.Member, item: str, count: int):
        try:
            cost = config["players"][user.id]["custom_shop"]["shop"][item] * count
            if config["players"][ctx.author.id]["balance"] >= cost:
                try:
                    config["players"][ctx.author.id]["custom_shop"]["inventory"][item] += count
                except KeyError:
                    config["players"][ctx.author.id]["custom_shop"]["inventory"][item] = count

                config["players"][ctx.author.id]["balance"] -= cost
                config["players"][user.id]["balance"] += cost

                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = f"✅ Bought {count}x {item} for {cost:,}{config['currency_symbol']} and item was added to your inventory".replace(",", " ")
                )
                embed.set_author(name="Buy", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    colour = discord.Colour.from_rgb(255,255,0),
                    description = "❌ Not enought money"
                )
                embed.set_author(name="Player buy", icon_url=bot.user.avatar_url)
                await ctx.send(embed=embed)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())

        config.save()

    @commands.command(name="inventory", help="Shows your 'realy usefull' items in your inventory: inventory")
    async def inventory(self, ctx: Context):
        try:
            l = config["players"][ctx.author.id]["custom_shop"]["inventory"]
            l = {k: v for k, v in sorted(l.items(), key=lambda item: item[1], reverse=True)}

            e_list = []
            msg = ""
            index = 1
            for name in l:
                msg += f"`{name}` | {l[name]}\n"
                if index == 30:
                    embed = discord.Embed(
                        colour = discord.Colour.from_rgb(255,255,0),
                        description = msg
                    )
                    embed.set_author(name="Inventory", icon_url=bot.user.avatar_url)
                    e_list.append(embed)
                    msg = ""
                    index = 1
                else:
                    index += 1

            embed = discord.Embed(
                colour = discord.Colour.from_rgb(255,255,0),
                description = msg
            )
            embed.set_author(name="Inventory", icon_url=bot.user.avatar_url)
            e_list.append(embed)

            paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
            paginator.remove_reactions = True
            await paginator.run(e_list)
        except:
            print(traceback.format_exc())
            await ctx.send(traceback.format_exc())



bot.add_cog(Money())
bot.add_cog(Income())
bot.add_cog(Essentials())
bot.add_cog(Config())
bot.add_cog(Development())
bot.add_cog(Settings())
bot.add_cog(PlayerShop())

bot.run(os.environ["TRINITY"])
