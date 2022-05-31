from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='counselor',
    version='0.3.3',
    description='Package to interact with HashiCorp Consul',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Joerg Eschmann',
    author_email='joerg.eschmann@gmail.com',
    url='https://github.com/joergeschmann/counselor',
    keywords=['consul'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
    ],
    license='MIT',
    install_requires=['requests==2.26.0'],
    packages=find_packages(),
)
