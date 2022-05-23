from setuptools import setup

setup(
    name="download_tools",
    version="0.0.0",
    packages=["download_tools", "download_tools.plugins"],
    url="",
    license="",
    author="Rationality Enhancement Group",
    author_email="",
    description="",
    setup_requires=['wheel']
    install_requires=[
        "numpy",
        "pandas",
        "sqlalchemy",
        "python-dotenv",
        "psycopg2",
        "dill",
    ],
)
