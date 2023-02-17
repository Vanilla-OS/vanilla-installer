import subprocess

class Systeminfo:
    uefi = None

    @staticmethod
    def is_uefi() -> bool:
        if not Systeminfo.uefi:
            proc = subprocess.Popen(["test", "-d", "/sys/firmware/efi"])
            proc.wait()
            Systeminfo.uefi = proc.returncode == 0

        return Systeminfo.uefi
