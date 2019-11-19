from setuptools import setup, find_namespace_packages

setup(name='counselor',
      version='0.1.0',
      description='Package to interact with hashicorp consul',
      author='Joerg Eschmann',
      author_email='joerg.eschmann@gmail.com',
      url='https://github.com/joergeschmann/counselor',
      download_url='',
      keywords=['consul'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Software Development :: Build Tools',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
      ],
      license='MIT',
      install_requires=[],
      package_dir={'': 'src'},
      packages=find_namespace_packages(where='src')
      )
