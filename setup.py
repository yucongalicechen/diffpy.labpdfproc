import os
import sys
from os import path

from setuptools import setup

import versioneer

MYDIR = os.path.dirname(os.path.abspath(__file__))

# NOTE: This file must remain Python 2 compatible for the foreseeable future,
# to ensure that we error out properly for people with outdated setuptools
# and/or pip.
min_version = (
    3,
    9,
)
if sys.version_info < min_version:
    error = """
diffpy.labpdfproc does not support Python {0}.{1}.
Python {2}.{3} and above is required. Check your Python version like so:

python3 --version

This may be due to an out-of-date pip. Make sure you have pip >= 9.0.1.
Upgrade pip like so:

pip install --upgrade pip
""".format(
        *(sys.version_info[:2] + min_version)
    )
    sys.exit(error)

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="utf-8") as readme_file:
    readme = readme_file.read()

with open(path.join(here, "requirements.txt")) as requirements_file:
    # Parse requirements.txt, ignoring any commented-out lines.
    requirements = [line for line in requirements_file.read().splitlines() if not line.startswith("#")]


setup(
    name="diffpy.labpdfproc",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="An app for preprocessing data from laboratory x-ray "
    "diffractometers before using PDFgetX3 to obtain PDFs",
    long_description=readme,
    author="diffpy project",
    author_email="sb2896@columbia.edu",
    url="https://github.com/sbillinge/diffpy.labpdfproc",
    python_requires=">={}".format(".".join(str(n) for n in min_version)),
    # packages=find_packages(os.path.join(MYDIR, "diffpy"), exclude=["docs", "tests"]),
    entry_points={
        "console_scripts": [
            "labpdfproc = diffpy.labpdfproc.labpdfprocapp:main",
        ],
    },
    include_package_data=True,
    package_data={
        "labpdfproc": ["docs/examples/*"]
        # When adding files here, remember to update MANIFEST.in as well,
        # or else they will not be included in the distribution on PyPI!
        # 'path/to/data_file',
    },
    install_requires=requirements,
    license="BSD (3-clause)",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)