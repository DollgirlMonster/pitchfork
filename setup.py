from setuptools import setup, find_packages

setup(
    name="pitchfork",
    version="0.2.1",
    packages=find_packages(),
    package_data={"pitchfork": ["pitchfork.css"]},
    install_requires=[
        "markdown",
        "pymdown-extensions",
        "websockets>=12.0",
        "watchdog>=3.0",
        "tomli>=2.0; python_version<'3.11'",  # tomllib is stdlib in 3.11+
    ],
    entry_points={
        "console_scripts": [
            "pitchfork=pitchfork.cli:main",
        ],
    },
    python_requires=">=3.8",
)
