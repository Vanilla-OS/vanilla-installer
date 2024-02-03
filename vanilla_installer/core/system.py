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
            proc = subprocess.Popen(
                "free -b | grep Mem | awk '{print $2}'",
                shell=True,
                stdout=subprocess.PIPE
            ).stdout.read().decode()
            Systeminfo.ram = int(proc) >= 3800000000

        return Systeminfo.ram

    @staticmethod
    def is_cpu_enough() -> bool:
        if not Systeminfo.cpu:
            proc1 = subprocess.Popen(
                "lscpu | grep -E 'Core\\(s\\)' | awk '{print $4}'",
                shell=True,
                stdout=subprocess.PIPE
            ).stdout.read().decode()
            proc2 = subprocess.Popen(
                "lscpu | grep -E 'Socket\\(s\\)' | awk '{print $2}'",
                shell=True,
                stdout=subprocess.PIPE
            ).stdout .read().decode()
            Systeminfo.cpu = (int(proc1) * int(proc2)) >= 2

        return Systeminfo.cpu
