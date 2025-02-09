import json
import os
import subprocess


class Diskutils:
    @staticmethod
    def pretty_size(size: int) -> str:
        if size > 1024**3:
            return f"{round(size / 1024 ** 3, 2)} GB"
        elif size > 1024**2:
            return f"{round(size / 1024 ** 2, 2)} MB"
        elif size > 1024:
            return f"{round(size / 1024, 2)} KB"
        else:
            return f"{size} B"

    @staticmethod
    def separate_device_and_partn(part_dev: str) -> tuple[str, str | None]:
        info_json = subprocess.check_output(
            "lsblk --json -o NAME,PKNAME,PARTN " + part_dev, shell=True
        ).decode("utf-8")
        info_multiple = json.loads(info_json)["blockdevices"]

        if len(info_multiple) > 1:
            raise ValueError(f"{part_dev} returned more than one device")
        info = info_multiple[0]

        if info["partn"] is None:
            # part_dev is actually a device, not a partition
            return "/dev/" + info["name"], None

        return "/dev/" + info["pkname"], str(info["partn"])

    @staticmethod
    def fetch_lvm_pvs() -> list[list[str]]:
        output_json = subprocess.check_output("sudo pvs --reportformat=json", shell=True).decode(
            "utf-8"
        )
        output_pvs = json.loads(output_json)["report"][0]["pv"]
        pv_with_vgs = []
        for pv_output in output_pvs:
            pv_name = pv_output["pv_name"]
            vg_name = pv_output["vg_name"] if pv_output["vg_name"] != "" else None
            pv_with_vgs.append([pv_name, vg_name])
        return pv_with_vgs


class Disk:
    def __init__(self, disk: str):
        self.__disk = disk
        self.__partitions = self.__get_partitions()
        self.__size = self.__get_size()

    def __get_partitions(self):
        partitions = []
        for partition in os.listdir(self.block):
            if partition.startswith(self.__disk):
                partitions.append(Partition(self.__disk, partition))
        return partitions

    def __get_size(self):
        with open(f"{self.block}/size", "r") as f:
            return int(f.read().strip()) * 512

    @property
    def partitions(self):
        return self.__partitions

    def get_partition(self, mountpoint: str):
        for partition in self.partitions:
            if partition.mountpoint == mountpoint:
                return partition

    def update_partitions(self):
        self.__partitions = self.__get_partitions()

    @property
    def disk(self):
        return f"/dev/{self.__disk}"

    @property
    def name(self):
        return self.__disk

    @property
    def block(self):
        return f"/sys/block/{self.__disk}"

    @property
    def size(self):
        return self.__size

    @property
    def pretty_size(self):
        size = self.size
        if size > 1024**3:
            return f"{round(size / 1024 ** 3, 2)} GB"
        elif size > 1024**2:
            return f"{round(size / 1024 ** 2, 2)} MB"
        elif size > 1024:
            return f"{round(size / 1024, 2)} KB"
        else:
            return f"{size} B"

    @property
    def is_removable(self):
        if os.path.isfile("/sys/block/" + self.__disk + "/removable"):
            with open("/sys/block/" + self.__disk + "/removable") as f:
                removable = int(f.readlines()[0].strip())
                if removable == 1:
                    return True
    
        return False


class Partition:
    def __init__(self, disk: str, partition: str):
        self.__disk = disk
        self.__partition = partition
        self.__mountpoint = self.__get_mountpoint()
        self.__size = self.__get_size()
        self.__fs_type = self.__get_fs_type()
        self.__uuid = self.__get_uuid()
        self.__label = self.__get_label()

    def __get_mountpoint(self):
        try:
            return (
                subprocess.check_output(f"findmnt -n -o TARGET {self.partition}", shell=True)
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            return None

    def __get_size(self):
        return int(open(f"{self.block}/size").read().strip()) * 512

    def __get_fs_type(self):
        try:
            return (
                subprocess.check_output(f"lsblk -d -n -o FSTYPE {self.partition}", shell=True)
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            return None

    def __get_uuid(self):
        try:
            return (
                subprocess.check_output(f"lsblk -d -n -o UUID {self.partition}", shell=True)
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            return None

    def __get_label(self):
        try:
            return (
                subprocess.check_output(f"findmnt -n -o LABEL {self.partition}", shell=True)
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            return None

    @property
    def partition(self):
        return f"/dev/{self.__partition}"

    @property
    def block(self):
        return f"/sys/block/{self.__disk}/{self.__partition}"

    @property
    def mountpoint(self):
        return self.__mountpoint

    @property
    def size(self):
        return self.__size

    @property
    def pretty_size(self):
        size = self.size
        if size > 1024**3:
            return f"{round(size / 1024 ** 3, 2)} GB"
        elif size > 1024**2:
            return f"{round(size / 1024 ** 2, 2)} MB"
        elif size > 1024:
            return f"{round(size / 1024, 2)} KB"
        else:
            return f"{size} B"

    @property
    def fs_type(self):
        return self.__fs_type

    @property
    def uuid(self):
        return self.__uuid

    @property
    def label(self):
        return self.__label

    def __lt__(self, other):
        return self.partition < other.partition

    def __eq__(self, other):
        if not other:
            return False
        return self.uuid == other.uuid and self.fs_type == other.fs_type


class DisksManager:
    def __init__(self):
        self.__disks = self.__get_disks()

    def __get_disks(self):
        disks = []

        for disk in os.listdir("/sys/block"):
            if disk.startswith(("loop", "ram", "sr", "zram", "dm-")):
                continue


            disks.append(Disk(disk))

        return disks

    def all_disks(self, include_removable: bool = True):
        selected_disks = []
        if include_removable:
            selected_disks = self.__disks
        else:
            for disk in self.__disks:
                if not disk.is_removable:
                    selected_disks.append(disk)

        return selected_disks

    def get_disk(self, disk: str):
        for disk in self.all_disks():
            if disk.disk == disk:
                return disk


# testing snippet:
# if __name__ == "__main__":
#     disks_manager = DisksManager()
#     for disk in disks_manager.all_disks:
#         print(f"Disk: {disk.disk}")
#         print(f"Size: {disk.size}")
#         for partition in disk.partitions:
#             print(f"Partition: {partition.partition}")
#             print(f"Mountpoint: {partition.mountpoint}")
#             print(f"Size: {partition.size}")
#             print(f"FS Type: {partition.fs_type}")
#             print(f"UUID: {partition.uuid}")
#             print(f"Label: {partition.label}")
#             print()

#         print()

#     print("Done!")
