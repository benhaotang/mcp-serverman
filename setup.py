from setuptools import setup, find_packages

setup(
    name="mcp-serverman",
    version="0.2.2",
    packages=find_packages(),
    package_data={
        'mcp_serverman': ['data/servers/*']
    },
    install_requires=[
        "click",
        "rich",
        "mcp>=1.3.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-serverman=mcp_serverman.cli:cli",
        ],
    },
    author="Benhao Tang",
    author_email="benhaotang@outlook.com",
    description="A tool to manage Claude MCP servers configuration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/benhaotang/mcp-serverman",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)