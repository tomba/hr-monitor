#!/usr/bin/env python3

# Bluetooth LE scanner
# Prints the name and address of every nearby Bluetooth LE device

import asyncio
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover()

    for device in devices:
        print(device)

asyncio.run(main())
