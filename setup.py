from setuptools import setup, find_packages

description ="""Rapidly turn Python classes into production-ready REST APIs.
Auto-exposes methods as namespaced endpoints, binds JSON payloads to call signatures, and returns uniform JSON responses.
Minimal boilerplate and per-endpoint method control—ideal for fast prototypes and microservices."""

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="restkit-server",
    version="0.1.0",
    author="Politech-tech",
    author_email="ido.shafrir@gmail.com",
    description=description,
    long_description_content_type="text/markdown",
    url="https://github.com/Politech-tech/restkit-server",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Flask",
    ],
    python_requires=">=3.6",
    install_requires=[
        "flask",
        "flask-cors",
        "requests",
    ],
)