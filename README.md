# MetaGPT Project

This project is a Python project that uses the MetaGPT package to perform actions. It includes a virtual environment named `meta_env`, test code to test the action component from MetaGPT, and debug launch tasks.

## Directory Structure

The project has the following directory structure:

```
metagpt_project
├── meta_env
│   ├── bin
│   ├── include
│   ├── lib
│   └── pyvenv.cfg
├── src
│   ├── main.py
│   ├── utils.py
│   └── tests
│       └── test_actions.py
├── .gitignore
├── README.md
├── requirements.txt
├── launch.json
├── tasks.json
└── init_git.sh
```

## Files

- `meta_env/`: This directory contains the virtual environment for the project.
- `src/main.py`: This file is the main entry point of the project. It contains the code to run the MetaGPT package and perform the desired actions.
- `src/utils.py`: This file contains helper functions and classes used by `main.py`.
- `src/tests/test_actions.py`: This file contains test cases for the action component of the MetaGPT package.
- `.gitignore`: This file specifies files and directories that should be ignored by Git.
- `README.md`: This file contains the documentation for the project.
- `requirements.txt`: This file lists the required packages for the project, including the MetaGPT package.
- `launch.json`: This file is used to configure the debugger for running the project.
- `tasks.json`: This file is used to configure tasks for the project, such as building the virtual environment.
- `init_git.sh`: This script initializes the project as a Git repository and sets the remote to `http://150.109.60.238:3000/tbxy09/MetaAgent.git`.

## Usage

To use this project, follow these steps:

1. Clone the repository.
2. Run the `init_git.sh` script to initialize the project as a Git repository and set the remote.
3. Run the `build_venv.sh` script to create the virtual environment.
4. Activate the virtual environment by running `source meta_env/bin/activate`.
5. Install the required packages by running `pip install -r requirements.txt`.
6. Run the project by running `python src/main.py`.
7. Run the tests by running `python -m unittest discover src/tests`.
8. Debug the project by using the `launch.json` configuration in your preferred IDE.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.