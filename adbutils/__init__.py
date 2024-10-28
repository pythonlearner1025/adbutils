# coding: utf-8
#

from __future__ import print_function

import io
import os
import typing

from deprecation import deprecated

from adbutils._adb import AdbConnection
from adbutils._adb import BaseClient as _BaseClient
from adbutils._device import AdbDevice, Sync
from adbutils._proto import *
from adbutils._utils import adb_path, StopEvent
from adbutils._version import __version__
from adbutils.errors import *


class AdbClient(_BaseClient):
    def sync(self, serial: str) -> Sync:
        return Sync(self, serial)

    @deprecated(deprecated_in="0.15.0",
                removed_in="1.0.0",
                current_version=__version__,
                details="use AdbDevice.shell instead")
    def shell(self,
              serial: str,
              command: typing.Union[str, list, tuple],
              stream: bool = False,
              timeout: typing.Optional[float] = None) -> typing.Union[str, AdbConnection]:
        return self.device(serial).shell(command, stream=stream, timeout=timeout)

    def list(self, extended=False) -> typing.List[AdbDeviceInfo]:
        """
        Returns:
            list of device info, including offline
        """
        infos = []
        with self.make_connection() as c:
            if extended:
                c.send_command("host:devices-l")
            else:
                c.send_command("host:devices")
            c.check_okay()
            output = c.read_string_block()
            for line in output.splitlines():
                parts = line.split()
                tags = {}
                num_required_fields = 2 # serial and state
                if len(parts) < num_required_fields:
                    continue
                if extended:
                    tags = {**tags, **{kv[0]: kv[1] for kv in list(map(lambda pair: pair.split(":"), parts[num_required_fields:]))}}
                infos.append(AdbDeviceInfo(serial=parts[0], state=parts[1], tags=tags))
        return infos

    def iter_device(self) -> typing.Iterator[AdbDevice]:
        """
        Returns:
            iter only AdbDevice with state:device
        """
        for info in self.list():
            if info.state != "device":
                continue
            yield AdbDevice(self, serial=info.serial)

    def device_list(self) -> typing.List[AdbDevice]:
        return list(self.iter_device())

    def device(self,
               serial: str = None,
               transport_id: int = None) -> AdbDevice:
        if serial:
            return AdbDevice(self, serial=serial)
        
        if transport_id:
            return AdbDevice(self, transport_id=transport_id)

        serial = os.environ.get("ANDROID_SERIAL")
        if not serial:
            ds = self.device_list()
            if len(ds) == 0:
                raise AdbError("Can't find any android device/emulator")
            if len(ds) > 1:
                raise AdbError(
                    "more than one device/emulator, please specify the serial number"
                )
            return ds[0]
        return AdbDevice(self, serial)


import asyncio
from typing import List, Optional

class AsyncAdbController:
    def __init__(self, host: str = "127.0.0.1", port: int = 5037, socket_timeout: Optional[int] = None):
        # Initialize AdbClient directly since it's a lightweight operation
        self.adb = AdbClient(host=host, port=port, socket_timeout=socket_timeout)
        
    async def device_list(self) -> List[AdbDevice]:
        """Get list of devices asynchronously"""
        return await asyncio.to_thread(self.adb.device_list)
        
    async def connect(self, address: str, timeout: Optional[float] = None) -> str:
        """Connect to a device asynchronously"""
        return await asyncio.to_thread(self.adb.connect, address, timeout)
        
    async def disconnect(self, address: str, raise_error: bool = False) -> str:
        """Disconnect from a device asynchronously"""
        return await asyncio.to_thread(self.adb.disconnect, address, raise_error)

    async def get_device(self, serial: Optional[str] = None) -> AdbDevice:
        """Get a device by serial asynchronously"""
        return await asyncio.to_thread(self.adb.device, serial)
        
    async def screenshot(self, device: AdbDevice):
        """Take a screenshot asynchronously"""
        return await asyncio.to_thread(device.screenshot)
        
    async def shell(self, device: AdbDevice, cmd: str, timeout: Optional[float] = None):
        """Run shell command asynchronously"""
        return await asyncio.to_thread(device.shell, cmd, timeout)

    async def push(self, device: AdbDevice, local: str, remote: str):
        """Push file asynchronously"""
        return await asyncio.to_thread(lambda: device.sync.push(local, remote))

    async def pull(self, device: AdbDevice, remote: str, local: str):
        """Pull file asynchronously"""
        return await asyncio.to_thread(lambda: device.sync.pull(remote, local))

    async def install(self, device: AdbDevice, apk_path: str):
        """Install APK asynchronously"""
        return await asyncio.to_thread(device.install, apk_path)

    async def uninstall(self, device: AdbDevice, package_name: str):
        """Uninstall package asynchronously"""
        return await asyncio.to_thread(device.uninstall, package_name)

    async def get_app_info(self, device: AdbDevice, package_name: str):
        """Get app info asynchronously"""
        return await asyncio.to_thread(device.app_info, package_name)


adb = AdbClient()
device = adb.device


if __name__ == "__main__":
    print("server version:", adb.server_version())
    print("devices:", adb.device_list())
    d = adb.device_list()[0]

    print(d.serial)
    for f in adb.sync(d.serial).iter_directory("/data/local/tmp"):
        print(f)

    finfo = adb.sync(d.serial).stat("/data/local/tmp")
    print(finfo)
    import io
    sync = adb.sync(d.serial)
    filepath = "/data/local/tmp/hi.txt"
    sync.push(io.BytesIO(b"hi5a4de5f4qa6we541fq6w1ef5a61f65ew1rf6we"),
              filepath, 0o644)

    print("FileInfo", sync.stat(filepath))
    for chunk in sync.iter_content(filepath):
        print(chunk)
    # sync.pull(filepath)
