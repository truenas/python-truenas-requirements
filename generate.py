# -*- coding=utf-8 -*-
from datetime import datetime
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap

logger = logging.getLogger(__name__)

PIP_TO_DEBIAN_MAPPING = {
    "google-api-python-client": "python3-googleapi",
    "pytz": "python3-tz",
}
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"


def pip_to_debian(name):
    return PIP_TO_DEBIAN_MAPPING.get(name, f"python3-{name}")


def generate_build():
    with open("build.sh", "w") as f:
        f.write(textwrap.dedent(f"""\
            #!/bin/sh -ex
            virtualenv --python=python{PYTHON_VERSION} v
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


def list_requirements():
    with open("requirements.txt") as f:
        requirements = f.read().strip().split()

    for requirement in requirements:
        yield requirement.split("==")


def generate_control():
    control = textwrap.dedent("""\
        Source: python3-truenas-requirements
        Section: admin
        Priority: optional
        Maintainer: Vladimir Vinogradenko <vladimirv@ixsystems.com>
        Build-Depends: debhelper-compat (= 12), python3-virtualenv
        Standards-Version: 4.4.0
        Homepage: https://truenas.com
    """)

    for package, version in list_requirements():
        package_name = pip_to_debian(package)

        depends = []
        output = subprocess.run(f"v/bin/pip download {package} -d /tmp --no-binary :all: -v", check=True,
                                capture_output=True, shell=True, text=True).stdout
        for dependency in re.findall(r"Collecting (.+)", output):
            if dependency != package:
                expressions = dependency.split(",")
                if m := re.match("([0-9A-Za-z_-]+)([^0-9A-Za-z_-].+)$", expressions[0]):
                    dependency = m.group(1)
                    expressions[0] = m.group(2)
                else:
                    dependency = expressions[0]
                    expressions = []

                expressions = list(map(
                    lambda e: re.sub(r"([^0-9])([0-9])", "\\1 \\2", e, 1).replace("< ", "<< ").replace("> ", ">>"),
                    filter(lambda e: not e.startswith("!="), expressions),
                ))

                dependency = pip_to_debian(dependency)
                if expressions:
                    depends.extend([f"{dependency} ({expression})" for expression in expressions])
                else:
                    depends.append(dependency)

        control += "\n" + textwrap.dedent(f"""\
            Package: {package_name}
            Architecture: amd64
            Depends: {', '.join(depends)}
            Description: {package.title()} for Python
             {package.title()} is a {package} library for for Python.
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

    for package, version in list_requirements():
        package_name = pip_to_debian(package)

        rules += f"\tdh_gencontrol -p{package_name} -- -v{version}\n"

    with open("debian/rules", "w") as f:
        f.write(rules)


def generate_install():
    subprocess.run("v/bin/pip install -r requirements.txt", check=True, shell=True)

    for package, version in list_requirements():
        package_name = pip_to_debian(package)

        files = []
        with open(f"v/lib/python{PYTHON_VERSION}/site-packages/{package.replace('-', '_')}-{version}.dist-info/RECORD") as f:
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

    generate_build()
    generate_changelog()
    generate_control()
    generate_rules()
    generate_install()
