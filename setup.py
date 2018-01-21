from setuptools import setup

# https://python-packaging.readthedocs.io/en/latest/minimal.html
setup(
    author="Radon Rosborough",
    author_email="radon.neon@gmail.com",
    description="Command-line accounting tool.",
    license="MIT",
    install_requires=[
        "certifi",
        "python-dateutil",
        "urllib3",
    ],
    name="acc",
    # scripts=["acc"],
    url="https://github.com/raxod502/acc",
    version="1.0",
    zip_safe=True,
)
