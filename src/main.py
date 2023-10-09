import asyncio
from importlib.abc import InspectLoader
from metagpt.actions.clone_function import CloneFunction
from importlib.abc import InspectLoader

class MyLoader(InspectLoader):
    def get_source(self, fullname):
        # provide an implementation for this method
        pass

inspect_loader = MyLoader()

# Original function 
source_code = """
def original_function(x, y):
    return x + y
"""

# Function template
template_func = "def new_function(a, b):\\n    # New implementation here\\n"

# Clone into new function 
async def clone_function():
    cf = CloneFunction()
    # print(inspect_loader.get_code(original_function.__module__))
    new_function_code = await cf.run(template_func=template_func, source_code=source_code)
    print(inspect_loader.get_code(CloneFunction.__module__))
    print(new_function_code)

# Run the asynchronous function
# asyncio.run(clone_function())
import inspect

# Get the module object from the module name
module = inspect.importlib.import_module(CloneFunction.__module__)

# Get the source file path of the module
source_path = inspect.getsourcefile(module)

# Read the source code from the file
with open(source_path, "r") as f:
    source_code = f.read()

# Print the source code
print(source_code)
