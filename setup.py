from setuptools import setup

# https://python-packaging.readthedocs.io/en/latest/minimal.html
setup(
    author="Radon Rosborough",
    author_email="radon.neon@gmail.com",
    description="Bare-bones command-line accounting.",
    license="MIT",
    install_requires=[],
    name="acc",
    scripts=["scripts/acc", "scripts/acc-import-elevations-csv"],
    url="https://github.com/raxod502/acc",
    version="1.0",
    zip_safe=True,
)
