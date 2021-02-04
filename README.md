# Trinity 
Powerfull discord bot for handeling economy for discord servers

# Installation

**Clone repo:**
```git clone https://github.com/Stax124/Trinity```

**Change directory to repo:**
```cd Trinity```

**Install python dependencies:**
```pip3 install -r requirements.txt```

**Set environment variables:**
Use ```export TRINITY="YOUR DISCORD API KEY"``` in your shell or append it to shell configuration (```~/.bashrc``` or ```~/.zshrc```)
On Windows, use ```setx TRINITY APIKEY```

**Start ```main.py```:**
```python3 main.py``` or ```sudo python3 main.py```

Application should create configuration file called ```.economy``` in your home directory (```~/.economy```), if running as root, its changed to ```/root/.economy```

**Usage in AWS cloud**
Tested on Ubuntu 20.04 LTS
Repeat all installation commands except start command and install **pm2**
```curl -sL https://deb.nodesource.com/setup_15.x | sudo -E bash -```
```sudo apt-get install -y nodejs```

```npm install pm2@latest -g```

**Start ```main.py``` with pm2 as background process:**
```pm2 start main.py -l ./log --interpreter=python3```

**Optional: Create restart script:**
```touch restart.sh```
```nano restart.sh```
Copypaste this script
```
#! /bin/sh
pm2 kill
pm2 start main.py -l ./log --interpreter=python3
```
Control+S to save and Control+X to exit

<h3>Usage</h3>

**Create role named Admin (with capital A)**
Without it, you cannot modify settings

All commans below will be with default prefix, modify them with yours

**Save, load configuration or reload bot:**
```
-config-save
-config-load
-reload
```

**Change prefix:**
Discord: ```-prefix <new prefix>```
Config: ```"prefix": "-"```

**Set currency symbol:**
Discord: ```-set currency_symbol = $```
Config: ```"currency_symbol": "$"```

**Set default time between -work (in seconds):**
Discord: ```-set deltatime = $```
Config: ```"deltatime": 10800```

# Discord commands
<h3>Config</h3>
```
config                  Output config directory: config <path> [path]...
config-load             Load configuration file: config-load
config-save             Save configuration file: config-save
config-stats            Config stats: config-stats
set                     Change values in config. You rather know what ya doin!: set <path> [path]... = <value>
```

<h3>Development</h3>
```
execute                 Execute python code: execute <command>
json-encode             Encode string to yaml format: json-encode <value: string>
python3                 Execute python code: python3 <command>
reload                  Reload members and roles: reload
```

<h3>Essentials</h3>
```
members                 Show all members: members
role                    Your roles: role
roles                   Show all roles: roles
roll                    Roll the dice of x sides: roll <maximal-value: integer>
shop                    Show shop: shop
time                    Shows formated time: time
```

<h3>Income</h3>
```
add-income              Add income: add-income <role: discord.Role> <value: integer>
income                  Shows your income: income
income-calc             Calculate income: income <populace>
income-lb               Show da income leaderboard: l, lb, leaderboard
remove-income           Remove income: remove-income <role: discord.Role> <value: integer>
```

<h3>Money</h3>
```
add-money               Add money to target: add-money <user: discord.Member> <value: integer>
balance                 Show your balance or more likely, empty pocket: b, bal, balance, money
buy                     Spend money to make more money bruh: buy <type: string> <value: integer>
leaderboard             Show da leaderboard: l, lb, leaderboard
pay                     Send money to target: pay <user: discord.Member> <value: int>
remove-money            Remove money from target: remove-money <user: discord.Member> <value: integer>
reset-money             Reset balance of target: reset-money <user: discord.Member>
work                    What are you doing, make some money!: work
```

<h3>PlayerShop</h3>
```
add-player-item         Add new item to players inventory: add-player-item [--income INCOME] [--income_percent INCOME_PERCENT] [--discount DISCOUNT] [--discount_percent DISCOUNT_PERCENT] [--description DESCRIPTION] name rarity
inventory               Shows your 'realy usefull' items in your inventory: inventory
player-buy              Sell items: player-buy <user: discord.Member> <item: str> <count: int>
player-sell             Sell items: player-sell <item: str> <price: int>
player-shop             Show player shop: player-shop <player: discord.Member>
remove-player-item      Remove item from players inventory: remove-player-item <user: discord.Member> <item: str>
```

<h3>Settings</h3>
```
add-item                Add item to database: add-item <name: string> <cost: integer> <max: integer> [income: integer]
bravo-six-going-dark    Deletes messages: bravo-six-going-dark <messages: integer>
prefix                  Change prefix of da bot: prefix <prefix: string>
remove-item             Remove item from database: remove-item <name: string>
shutdown                Show the bot, whos da boss: shutdown
```

# License
```
MIT License

Copyright (c) 2021 Tomáš Novák

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```