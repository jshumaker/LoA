from grid import *
import time

count = int(input("How many times to use item: "))

input("Place mouse over center of inventory item to use and press enter.")

x, y = Mouse.get_position()

for i in range(count):
    Mouse.click(x, y)
    time.sleep(0.100)
    Mouse.click(x + 50, y + 15)
    time.sleep(0.100)

