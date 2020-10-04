import setuptools

setuptools.setup(
    name="pisek",
    version="0.1",
    description="Nástroj na kontrolování úloh",
    packages=setuptools.find_packages(),
    install_requires=["tqdm>=4.50"],
    entry_points={"console_scripts": ["pisek=pisek.__main__:main"]},
)
