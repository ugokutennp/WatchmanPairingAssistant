from typing import Optional, Generator

import libusb_package
import usb


class UsbTreeItem:
    def __init__(self, device: usb.core.Device, children: dict[int, usb.core.Device], parent=None, level=0):
        self.children = {
            num: UsbTreeItem(data["device"], data["children"], self, level + 1) for num, data in children.items()
        }
        self.parent = parent
        self.address = device.address
        self.bus = device.bus
        self.port = device.port_number
        self.product = ""
        try:
            if device.product is not None:
                self.product = device.product
        except:
            pass

        self.vendor = ""
        try:
            if device.manufacturer is not None:
                self.vendor = device.manufacturer
        except:
            pass

        self.serial = "No Serial Number"
        try:
            if device.serial_number is not None:
                self.serial = device.serial_number
        except:
            pass

        self.ports = device.port_numbers
        self.device = device
        self.class_pretty = self.pp_class()

    def is_hub(self) -> bool:
        return self.device.bDeviceClass == usb.CLASS_HUB

    def is_vive_dongle(self) -> bool:
        return self.device.idVendor == 0x28DE and self.device.idProduct in [0x2101, 0x2102]

    def is_dongle(self) -> bool:
        return self.is_vive_dongle()

    def pp_class(self):
        cls = self.device.bDeviceClass
        if cls == usb.CLASS_HUB:
            return "USB-Hub"
        else:
            return f"Device"

    @property
    def children_flat_list(self) -> list['UsbTreeItem']:
        for child in self.children.values():
            yield child
            if child.is_hub():
                yield from child.children_flat_list

    def render_children(self, indent=0) -> str:
        data = ""
        for port, child in self.children.items():
            data += " " * indent
            data += "\n" + child.render(indent + 2)
        return data

    def render(self, indent=0) -> str:
        data = " " * indent
        data += f"[Port{self.port}]: {self.class_pretty} (VID:{self.device.idVendor:X} PID:{self.device.idProduct:X}), {self.vendor}, {self.product}"
        if len(self.children.items()) > 0:
            data += f"{self.render_children(indent)}"
        return data

    # This function only works if the USB device is a HMD. It will return the required depth
    def get_hmd_root_depth(self) -> Optional[int]:
        if self.device.idVendor == 0x0BB4 and self.device.idProduct == 0x0309:
            return 3
        if self.product in ["Beyond", "Index HMD"]:
            return 2

    def find_hmd(self) -> Optional['ViveHMD']:
        if len(self.children.items()) > 0:
            for child in self.children.values():
                device = child.find_hmd()
                if device is not None:
                    assert isinstance(device, ViveHMD)
                    return device
        required_depth = self.get_hmd_root_depth()
        if required_depth is not None:
            device = self
            for _ in range(0, required_depth):
                device = device.parent
            return ViveHMD(device, self)

    def __repr__(self):
        return self.render()


class ViveHMD:
    def __init__(self, device: UsbTreeItem, idDevice: UsbTreeItem):
        self.idDevice = idDevice
        self.device = device

    def get_attached_dongles(self) -> list[UsbTreeItem]:
        return [child for child in self.device.children_flat_list if child.is_dongle()]

    def get_dongle_serials(self) -> list[str]:
        return [device.serial for device in self.get_attached_dongles()]

    def get_display_name(self):
        return f"{self.idDevice.vendor} {self.idDevice.product}"


def __create_device_tree(devices: list[usb.core.Device]) -> dict:
    root = {}
    for device in devices:
        current_node = root
        ports = device.port_numbers
        if ports is None:
            last_port = device.port_number
        else:
            for port in ports[:-1]:  # Iterate through all but the last port
                if int(port) not in current_node:
                    current_node[int(port)] = {"device": None, "children": {}}
                current_node = current_node[int(port)]["children"]
            # Now current_node is the parent of the node this device should be placed in
            last_port = int(ports[-1])
        if last_port not in current_node:
            current_node[last_port] = {"device": device, "children": {}}
        else:
            current_node[last_port]["device"] = device
    return root


def __sort_device_tree(to_sort):
    # Use the sorted function with int casting to sort keys by integer value.
    sorted_keys = sorted(to_sort.keys(), key=int)
    output = {}
    for key in sorted_keys:
        output[key] = to_sort[key]
        # Now sort the children of this node in the same way
        output[key]['children'] = __sort_device_tree(to_sort[key]['children'])
    return output


def __convert_tree(to_convert) -> list[UsbTreeItem]:
    for hub in to_convert.values():
        yield UsbTreeItem(hub["device"], hub["children"])


def find_hmd() -> Generator[ViveHMD, None, None]:
    for bus in usb.busses():
        bus: usb.legacy.Bus
        # for dev in bus.devices:
        #     dev: usb.legacy.Device
        #     devices.append(UsbTreeItem(dev))
        # print(" " + str(dev))
        # print(" class: " + str(dev.deviceClass))
        # print(f" address: {bus.location}." + str(dev.dev.address) + " - " + str(dev.dev.port_numbers))
        # print()
        # if dev.deviceClass == usb.CLASS_PER_INTERFACE and dev.idVendor == 0x28DE:
        #     print(" " + str(util.get_string(dev.dev, dev.iProduct, 0x0409)))
        #     print(" " + str(util.get_string(dev.dev, dev.iSerialNumber, 0x0409)))
        # print(" " + util.get_string(dev.dev, 2, 0x0409))

        device_tree = __create_device_tree([device.dev for device in bus.devices])
        sorted_tree = __sort_device_tree(device_tree)
        converted = list(__convert_tree(sorted_tree))
        for dev in converted:
            hmd = dev.find_hmd()
            if hmd is not None:
                yield hmd


libusb_package.get_libusb1_backend()
