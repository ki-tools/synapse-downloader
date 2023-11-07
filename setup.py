import setuptools
from src.synapse_downloader._version import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="synapse-downloader",
    version=__version__,
    license="Apache2",
    description="Utility for downloading large datasets from Synapse.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ki-tools/synapse-downloader",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    classifiers=(
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': [
            "synapse-downloader = synapse_downloader.cli:main"
        ]
    },
    install_requires=[
        "synapseclient>=2.3.1,<3.0.0",
        "synapsis>=0.0.7"
    ]
)
