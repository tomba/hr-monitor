#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import pickle
import sys
import time

from bleak import BleakScanner, BleakClient

HRM_SERVICE_UUID = '0000180d-0000-1000-8000-00805f9b34fb'
HRM_CHARACTERISTIC_UUID = '00002a37-0000-1000-8000-00805f9b34fb'

DEVICE_NAME = 'HRMPro+:361837'

HOST = '127.0.0.1'
PORT = 8888

FAKE = False

class HRMonitor:
    def __init__(self, fake: bool) -> None:
        self.fake = fake

        self.client_writers: list[asyncio.StreamWriter] = []

        # (timestamp, data)
        self.DATA = []

        self.hr_file = None

        self.key_event: asyncio.Event


    async def heart_rate_notification_handler(self, sender: int, data: bytearray):
        self.DATA.append((time.time(), data))

        heart_rate = data[1]
        print(f'Heart Rate: {heart_rate} BPM')

        assert self.hr_file
        self.hr_file.write(f'{int(time.time() * 1000)},{heart_rate}\n')

        hr_data = (time.time(), data)

        await self.send_data(hr_data)

    async def fake_periodic_work(self, hr_data_arr):
        idx = 0

        base_ts = 0
        current_ts = time.time()
        last_ts = time.time()

        while True:
            if idx >= len(hr_data_arr):
                idx = 0
                current_ts = last_ts

            hr_data = hr_data_arr[idx]
            idx += 1

            if base_ts == 0:
                base_ts = hr_data[0]

            ts_diff = hr_data[0] - base_ts
            ts = current_ts + ts_diff
            last_ts = ts

            # overwrite the ts
            hr_data = (ts, hr_data[1])

            await self.send_data(hr_data)

            await asyncio.sleep(0.1)

    async def send_data(self, hr_data):
        data_bytes = pickle.dumps(hr_data)
        data_len = len(data_bytes)
        len_bytes = data_len.to_bytes(4, 'big', signed=False)

        for writer in self.client_writers.copy():

            try:
                writer.write(len_bytes)
                writer.write(data_bytes)
                await writer.drain()
            except OSError:
                print('Client disconnected')
                self.client_writers.remove(writer)

    def handle_input(self):
        sys.stdin.readline()
        self.key_event.set()

    async def handle_client(self, reader, writer):
        print('Client connected')
        self.client_writers.append(writer)

    async def run_fake(self):
        with open('hr.data', 'rb') as f:
            hr_data = pickle.load(f)

        task = asyncio.create_task(self.fake_periodic_work(hr_data))

        await self.key_event.wait()

        task.cancel()

    async def run_real(self):
        print('Discovering')

        dev = await BleakScanner.find_device_by_name(DEVICE_NAME,
                                                     service_uuids=[HRM_SERVICE_UUID])

        if not dev:
            print('Not found')
            return

        print(f'Found device {dev}')

        print('Connecting')

        async with BleakClient(dev, services=[HRM_SERVICE_UUID], timeout=120) as client:
            print(f'Connected to {client.address}')

            self.hr_file = open(f'hr-{int(time.time())}.csv', 'w', encoding='utf-8')

            await client.start_notify(HRM_CHARACTERISTIC_UUID,
                                      self.heart_rate_notification_handler)

            print('Listening for heart rate data... Press Enter to stop.')

            await self.key_event.wait()

            print('Exit...')

    async def main(self):
        await asyncio.start_server(self.handle_client, HOST, PORT)

        self.key_event = asyncio.Event()

        loop = asyncio.get_event_loop()
        loop.add_reader(sys.stdin, self.handle_input)

        if self.fake:
            await self.run_fake()
        else:
            await self.run_real()


if __name__ == '__main__':
    monitor = HRMonitor(fake=FAKE)
    asyncio.run(monitor.main())
