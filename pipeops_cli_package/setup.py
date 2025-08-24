from setuptools import setup, find_packages

setup(
    name="pipeops-cli",
    version="1.3.0",
    description="GitLab Pipeline Automation Tool for DevOps Teams",
    long_description="Simple CLI tool for automating GitLab CI/CD pipeline creation and monitoring",
    author="DevOps Team",
    author_email="devops@company.internal",

    packages=find_packages(),
    include_package_data=True,

    install_requires=[
        "click>=8.0.0",
        "PyYAML>=6.0.0",
        "requests>=2.25.0"
    ],

    python_requires=">=3.7",

    entry_points={
        "console_scripts": [
            "pipeops-cli=cli:cli",
        ],
    },

    package_data={
        "": ["Config/*.yml", "Templates/**/*"],
    },
)