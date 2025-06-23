from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kicad-netlist-tool",
    version="0.1.0",
    author="Your Name",
    description="Extract component and netlist information from KiCad files for LLM documentation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/kicad-netlist-tool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "sexpdata>=1.0.0",
        "watchdog>=3.0.0",
        "click>=8.0.0",
        "pystray>=0.19.0",
        "Pillow>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "kicad-netlist-tool=kicad_netlist_tool.gui.tray_app:main",
        ],
    },
)