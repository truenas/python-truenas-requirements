import re
import subprocess

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

result = []
for req in requirements:
    if req.startswith("git+"):
        result.append(req)
        continue

    package = req.split("==")[0]
    new_version = re.search(
        fr"{package} \((.+)\)\n",
        subprocess.check_output(f"pip index versions {package}".split(), stderr=subprocess.DEVNULL).decode()
    ).group(1)
    result.append(f"{package}=={new_version}")

with open("requirements.txt", "w") as f:
    f.write("\n".join(result) + "\n")
