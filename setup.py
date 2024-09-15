from setuptools import setup, find_packages

setup(
    name="easy-aso",
    version="0.1.0",
    description="Automated Supervisory Optimization (ASO) for BACnet systems",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/bbartling/easy-aso",
    author="Your Name",
    author_email="ben.bartling@gmail.com",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "bacpypes3", "iffaddr"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
