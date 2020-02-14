import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="synapse-downloader",
    version="0.0.1",
    author="Patrick Stout",
    author_email="pstout@prevagroup.com",
    license="Apache2",
    description="Utility for downloading large datasets from Synapse.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ki-tools/synapse-downloader",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    classifiers=(
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': [
            "synapse-downloader = synapse_downloader.cli:main"
        ]
    },
    install_requires=[
        "synapseclient>=1.9.2,<2.0.0",
        "aiohttp",
        "aiofiles"
    ]
)
