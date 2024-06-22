# -*- coding=utf-8 -*-
from dataclasses import dataclass
from datetime import datetime
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap

logger = logging.getLogger(__name__)

EXTRA_COMMANDS = [
]
SKIP_NO_BINARY = {
    "aiohttp-rpc",  # PIP starts downloading `poetry` and other unrelated packages (and fails) if `--no-binary` is used
    "pydantic",
    "pydantic-core",  # Debian bookworm has rustc 1.63.0 while this package requires 1.69 (via toml v0.8.10)
}
PIP_TO_DEBIAN_MAPPING = {
    "attrs": "python3-attr",
    "beautifulsoup4": "python3-bs4",
    "google-api-python-client": "python3-googleapi",
    "pyopenssl": "python3-openssl",
    "pynacl": "python3-nacl",
    "python-dateutil": "python3-dateutil",
    "python-digitalocean": "python3-digitalocean",
    "pytz": "python3-tz",
    "pyyaml": "python3-yaml",
    "typing_extensions": "python3-typing-extensions",
    "websocket-client": "python3-websocket",
}
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"


def pip_to_debian(name):
    return PIP_TO_DEBIAN_MAPPING.get(name.lower(), f"python3-{name}").lower()


def generate_build():
    extra = "\n".join(EXTRA_COMMANDS)
    with open("build.sh", "w") as f:
        f.write(textwrap.dedent(f"""\
            #!/bin/sh -ex
            virtualenv --python=python{PYTHON_VERSION} v
            {extra}
            v/bin/pip install -r requirements.txt
        """))


def generate_changelog():
    with open("debian/changelog") as f:
        changelog = f.read()

    try:
        version = int(re.match(r"python3-truenas-requirements \(0\.0\.0-([0-9]+)\)", changelog).group(1)) + 1
    except AttributeError:
        version = 1

    with open("debian/changelog", "w") as f:
        f.write(textwrap.dedent(f"""\
            python3-truenas-requirements (0.0.0-{version}) unstable; urgency=medium
            
              * Initial release (Closes: #1)
            
             -- Vladimir Vinogradenko <vladimirv@ixsystems.com>  {datetime.utcnow().strftime('%a,  %d %b %Y %H:%M:%S')} +0000
        """))


@dataclass
class Requirement:
    requirement: str
    package: str
    version: str
    distinfo: str


def list_requirements():
    with open("requirements.txt") as f:
        requirements = f.read().strip().split()

    for requirement in requirements:
        package, version = requirement.split("#egg=")[-1].split("==")

        distinfo = f"{package.replace('-', '_')}-{version}.dist-info"

        if requirement.startswith("git+"):
            version = f"{version.split('.')[0]}.99.99"

        yield Requirement(requirement, package, version, distinfo)


def generate_control():
    control = textwrap.dedent("""\
        Source: python3-truenas-requirements
        Section: admin
        Priority: optional
        Maintainer: Vladimir Vinogradenko <vladimirv@ixsystems.com>
        Build-Depends: debhelper-compat (= 12), libffi-dev, python3-virtualenv
        Standards-Version: 4.4.0
        Homepage: https://truenas.com
    """)

    for requirement in list_requirements():
        package_name = pip_to_debian(requirement.package)

        depends = []
        if requirement.package in SKIP_NO_BINARY:
            binary = ""
        else:
            binary = "--no-binary :all:"
        output = subprocess.run(f"v/bin/pip download {requirement.requirement} -c constraints.txt -c requirements.txt "
                                f"-d /tmp {binary} -v",
                                check=True, stdout=subprocess.PIPE, shell=True, text=True).stdout
        for dependency in re.findall(r"Collecting (.+)", output):
            expressions = dependency.split(",")
            if m := re.match("([0-9A-Za-z_-]+)([^0-9A-Za-z_-].+)$", expressions[0]):
                dependency = m.group(1)
                expressions[0] = m.group(2)
            else:
                dependency = expressions[0]
                expressions = []

            expressions = list(map(
                lambda e: (re.sub(r"([^0-9])([0-9])", "\\1 \\2", e, 1).replace("< ", "<< ").replace("> ", ">>").
                           replace("~=", ">=").replace("==", "=")),
                filter(lambda e: not e.startswith("!="), expressions),
            ))

            dependency = pip_to_debian(dependency)
            if dependency != package_name:
                if expressions:
                    depends.extend([f"{dependency} ({expression})" for expression in expressions])
                else:
                    depends.append(dependency)

        depends.sort()

        control += "\n" + textwrap.dedent(f"""\
            Package: {package_name}
            Architecture: amd64
            Depends: {', '.join(depends)}
            Description: {requirement.package.title()} for Python
             {requirement.package.title()} is a {requirement.package} library for Python.
        """)

    with open("debian/control", "w") as f:
        f.write(control)


def generate_rules():
    rules = textwrap.dedent("""\
        #!/usr/bin/make -f
        export DH_VERBOSE = 1
        
        %:
        	dh $@
        
        override_dh_auto_build:
        	./build.sh

        override_dh_gencontrol:
        	dh_gencontrol
    """)

    for requirement in list_requirements():
        package_name = pip_to_debian(requirement.package)

        rules += f"\tdh_gencontrol -p{package_name} -- -v{requirement.version}\n"

    with open("debian/rules", "w") as f:
        f.write(rules)


def generate_install():
    subprocess.run("v/bin/pip install -r requirements.txt", check=True, shell=True)

    for requirement in list_requirements():
        package_name = pip_to_debian(requirement.package)

        files = []
        with open(f"v/lib/python{PYTHON_VERSION}/site-packages/{requirement.distinfo}/RECORD") as f:
            for line in f.read().strip().splitlines():
                file = line.split(",")[0]

                if file.endswith(".dist-info/REQUESTED"):
                    continue

                files.append(file)

        with open(f"debian/{package_name}.install", "w") as f:
            f.write("\n".join([
                " ".join([os.path.normpath(f"v/lib/python{PYTHON_VERSION}/site-packages/{file}"),
                          os.path.normpath(f"usr/lib/python3/dist-packages/{os.path.dirname(file)}")])
                for file in files
            ]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    if os.path.exists("v"):
        shutil.rmtree("v")

    subprocess.run(f"virtualenv --python=python{PYTHON_VERSION} v", check=True, shell=True)
    for cmd in EXTRA_COMMANDS:
        subprocess.run(cmd, check=True, shell=True)

    generate_build()
    generate_changelog()
    generate_control()
    generate_rules()
    generate_install()
