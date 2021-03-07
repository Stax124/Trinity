from pynput import keyboard
import pyautogui
import sys
import time

print("running")
mention = "<@292312596260978688>"
bot_mention = "<@784059560972779540>"
role = "<@&749188696313561119>"
prefix = "-"


def run(command: str, pause: int = 5):
    pyautogui.write(prefix+command)
    pyautogui.press("enter")
    time.sleep(pause)


def on_press(key):
    if key == keyboard.Key.f2:
        run("attack 1 1 0")
        run("manpower")

        run("next-backup")
        run("config")
        run("config-save")
        run("config-load")
        run("config-stats")
        run("set work_range = 0")

        run("asyncs-on-hold")
        run(f"dm {mention} Hello world")
        run("json-encode voják")
        run("eval 'Hello world'")
        run("reload")

        run("members")
        run("role")
        run("roles")
        run("roll 1000")
        run("shop")
        run("time")

        run(f"add-income {role} 1")
        run("income")
        run("income-calc 250000")
        run("income-lb")
        run(f"remove-income {role} 1")

        run(f"add-money {mention} 1")
        run("balance")
        run("buy Voják 1")
        run("leaderboard")
        run(f"pay {bot_mention} 1")
        run(f"remove-money {mention} 1")
        run(f"reset-money {mention}")
        run("work", 3)

        run(f"add-player-item {mention} test rare weapon")
        run("player-sell 1 test")
        run("player-retrieve test")
        run("inventory")
        run("equip test")
        run("unequip test")
        run(f"recycle test")

        run("add-expedition test 0 0")
        run("expeditions")
        run("expedition test")
        run("remove-expedition test")

        run("level")
        run("levelup Stewardship")
        run("talents")
        run("skillpoints")

        run("add-item test 0")
        run("cleanup 1")
        run("deltatime")
        run("on-join-dm Hello world")
        run(f"prefix {prefix}")
        run("remove-item test")
        run("shutdown")

    if key == keyboard.Key.esc:
        sys.exit(0)


with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
