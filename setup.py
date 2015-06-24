from distutils.core import setup
from distutils.command.install_data import install_data


setup (name = "schunk_motion_control", 
        version = "0.5.0",
        description = "control schunk device implementing motino control interface",
        author = "Olivier Roulet-Dubonnet",
        author_email = "olivier.roulet@gmail.com",
        url = '',
        packages = ["pg"],
        provides = ["schunk"],
        license = "GNU General Public License v3",

        classifiers = [
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Operating System :: OS Independent",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ]
        )


