import setuptools

setuptools.setup(
    name="pisek",
    version="0.1",
    description="Nástroj na kontrolování úloh",
    packages=setuptools.find_packages(),
    install_requires=["tqdm>=4.50", "termcolor>=1.1", "types-termcolor"],
    extras_require={"dev": ["black", "mypy"]},
    entry_points={"console_scripts": ["pisek=pisek.__main__:main_wrapped"]},
)
