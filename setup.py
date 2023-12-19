#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


from sys import version_info
from setuptools import setup
from setuptools.command.install import install as _install


class install(_install):
    def pre_install_script(self):
        pass

    def post_install_script(self):
        pass

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()


def load_requires():
    with open("./MANIFEST.md") as f:
        requires = f.read()
    return requires


def load_version():
    with open("./beehive/VERSION") as f:
        version = f.read()
    return version


if __name__ == "__main__":
    version = load_version()
    setup(
        name="beehive",
        version=version,
        description="Nivola core",
        long_description="Nivola main server package",
        author="CSI Piemonte",
        author_email="nivola.engineering@csi.it",
        license="EUPL-1.2",
        url="",
        scripts=[],
        packages=[
            "beehive",
            "beehive.common",
            "beehive.common.client",
            "beehive.common.controller",
            "beehive.common.model",
            "beehive.common.task",
            "beehive.common.task_v2",
            "beehive.db_script",
            "beehive.module",
            "beehive.module.auth",
            "beehive.module.auth.views",
            "beehive.module.basic",
            "beehive.module.basic.views",
            "beehive.module.catalog",
            "beehive.module.config",
            "beehive.module.event",
            "beehive.module.scheduler",
            "beehive.module.scheduler_v2",
            "beehive.server",
            "beehive.tests",
            "beehive.tests.common",
            "beehive.tests.module",
            "beehive.tests.module.auth",
            "beehive.tests.module.basic",
            "beehive.tests.module.catalog",
            "beehive.tests.module.event",
            "beehive.tests.module.scheduler",
            "beehive.tests.module.scheduler_v2",
        ],
        namespace_packages=[],
        py_modules=["beehive.__init__"],
        classifiers=[
            "Development Status :: %s" % version,
            "Programming Language :: Python",
        ],
        entry_points={},
        data_files=[
            ("share", ["beehive/server/swagger.yml"]),
            (
                "share/config",
                [
                    "config/auth.json",
                    "config/event.json",
                    "config/auth.yml",
                    "config/event.yml",
                ],
            ),
            (
                "bin",
                [
                    "beehive/server/pyenv.sh",
                    "beehive/server/api.py",
                    "beehive/server/scheduler_v2.py",
                    "beehive/server/catalog_v2.py",
                    "beehive/server/event_v2.py",
                    "beehive/server/console.py",
                ],
            ),
            ("share/test", ["config/beehive.yml", "config/beehive.fernet"]),
        ],
        package_dir={"beehive": "beehive"},
        package_data={"beehive": ["VERSION"]},
        install_requires=load_requires(),
        dependency_links=[],
        zip_safe=True,
        cmdclass={"install": install},
        keywords="",
        python_requires="",
        obsoletes=[],
    )
