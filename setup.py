from setuptools import setup, find_packages

setup(
    name="darkloader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    author="Gxldxm",
    author_email="ealmfr@gmail.com",
    description="Download files from various websites",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.6",
)
