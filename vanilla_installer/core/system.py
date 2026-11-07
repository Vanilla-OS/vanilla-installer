import subprocess


class Systeminfo:
    uefi = None
    ram = None
    cpu = None

    @staticmethod
    def is_uefi() -> bool:
        if not Systeminfo.uefi:
            proc = subprocess.Popen(["test", "-d", "/sys/firmware/efi"])
            proc.wait()
            Systeminfo.uefi = proc.returncode == 0

        return Systeminfo.uefi

    @staticmethod
    def is_ram_enough() -> bool:
        if not Systeminfo.ram:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        Systeminfo.ram = int(line.split()[1]) * 1024 >= 3800000000
                        break
        return Systeminfo.ram

    @staticmethod
    def is_cpu_enough() -> bool:
        if not Systeminfo.cpu:
            proc = subprocess.Popen(
                "nproc",
                shell=True,
                stdout=subprocess.PIPE
            ).stdout.read().decode()
            Systeminfo.cpu = int(proc) >= 2

        return Systeminfo.cpu
