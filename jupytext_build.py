# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import subprocess
import sys

"""
This script is used to execute Jupytext on a notebook file.
It is intended to be used as a pre-commit hook to ensure that notebooks
execute successfully without errors
"""

def execute_jupytext(file_path):
    try:
        result = subprocess.run(['jupytext', '--to', 'notebook', '--execute', '--pre-commit-mode', file_path],
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True)
        print(f"Successfully executed notebook: {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute notebook: {file_path}")
        print("Error details:")
        print(e.output)
        return False
    return True

def main():
    success = True
    for file_path in sys.argv[1:]:
        if not execute_jupytext(file_path):
            success = False

    # Exit with a non-zero status code if any file failed to process
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()