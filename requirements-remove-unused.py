import subprocess

from generate import pip_to_debian, list_requirements


if __name__ == "__main__":
    unused_deb_packages = {}
    for requirement in list_requirements():
        unused_deb_packages[pip_to_debian(requirement.package)] = requirement

    for deb_package in subprocess.check_output(["apt", "list", "--installed"],
                                               stderr=subprocess.DEVNULL,
                                               encoding="utf-8").splitlines()[1:]:
        deb_package_name = deb_package.split()[0].split("/")[0]
        deb_package_version = deb_package.split()[1]

        if requirement := unused_deb_packages.get(deb_package_name):
            if requirement.version != deb_package_version:
                print(
                    f"Requirement {requirement.requirement} is ignored since {deb_package_name} {deb_package_version} "
                    "is installed"
                )
                continue

            unused_deb_packages.pop(deb_package_name, None)

    with open("requirements.txt") as f:
        requirements = f.read().strip().split()

    for unused_requirement in unused_deb_packages.values():
        print(f"Requirement {unused_requirement.requirement} is not used")
        requirements.remove(unused_requirement.requirement)

    with open("requirements.txt", "w") as f:
        f.write("\n".join(requirements) + "\n")
