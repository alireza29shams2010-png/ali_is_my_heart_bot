import os
import bot

names = sorted(k for k in os.environ if "TOKEN" in k.upper() or "TELEGRAM" in k.upper())
print("DIAG env names:", [repr(k) for k in names], flush=True)
for k in names:
    print("DIAG", repr(k), "length", len(os.environ[k]), flush=True)

bot.main()
