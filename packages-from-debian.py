# Prints python3-* packages that were installed from the official Debian repo rather than built using this script

import re
import subprocess

for line in subprocess.check_output("apt list --installed".split(), stderr=subprocess.DEVNULL).decode().splitlines():
    pkgname = line.split("/")[0]

    if not pkgname.startswith("python3-"):
        continue

    show = subprocess.check_output(f"apt show {pkgname}".split(), stderr=subprocess.DEVNULL).decode()
    if "Source: python3-truenas-requirements" in show:
        continue

    version = re.search(r"Version: (.+)\n", show).group(1)
    print(pkgname, version)
