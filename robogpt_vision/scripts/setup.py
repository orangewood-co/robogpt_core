#!/use/bin/python3

from distutils.core import setup
from Cython.Build import cythonize
import rospkg
import os
from setuptools import Extension

rospath = rospkg.RosPack()
package_path = rospath.get_path('robogpt_vision')
print(package_path)
scripts_path = os.path.join(package_path,'scripts','robogpt_perception.pyx')
print(scripts_path)
output_dir = os.path.join(package_path, 'scripts')

if not os.path.exists(output_dir):
    print("no such directory")

setup(
    ext_modules = cythonize(
        Extension(
            name="robogpt_perception",  # The name of the generated C extension (prompts.so)
            sources=[scripts_path],
            language="c",
        ),
        language_level="3"
    ),
    script_args=['build_ext', '--inplace'],  # This tells it to place the .so in the script directory
)