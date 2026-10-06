from setuptools import find_packages, setup

package_name = 'mower_status'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jamie',
    maintainer_email='jamie-gastrich@users.noreply.github.com',
    description='Reports the status of the mower',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'status_node = mower_status.status_node:main',
        ],
    },
)
