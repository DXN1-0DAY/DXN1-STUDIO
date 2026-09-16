# your first background — code something, watch it appear.
# run:  dxn3 sdk/examples/background.py
from dxn3 import *

background("#0b0e1a")

# a gradient sky floor and a moon — this is all your code:
ground = rect("ground", 0, H - 8, W, 8, "#1c2136")
ground.fill = "gradient"
ground.color2 = "#2a2f4a"

moon = circle("moon", W - 18, 6, 9, 9, "#e9e5ff")
stars = label("stars", 2, 2, "*  *   *    *  *   *  *", "#6b7280")

print("a background, from 6 lines of code")

run()
