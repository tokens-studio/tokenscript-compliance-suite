#!/usr/bin/env python3

import os
import json
import argparse
import tempfile
import subprocess
import sys
from pathlib import Path


def get_user_input_with_editor(initial_content=""):
    """Get user input using the default editor."""
    with tempfile.NamedTemporaryFile(suffix=".tmp", mode="w+", delete=False) as temp:
        temp.write(initial_content)
        temp.flush()
        temp_path = temp.name

    # Get default editor from environment or fall back to vim/nano
    editor = os.environ.get('EDITOR', 'vim' if os.system('which vim > /dev/null 2>&1') == 0 else 'nano')

    try:
        subprocess.check_call([editor, temp_path])
    except subprocess.CalledProcessError:
        print(f"Error opening editor {editor}. Please set the EDITOR environment variable.")
        os.unlink(temp_path)
        return None

    with open(temp_path, 'r') as temp:
        content = temp.read()

    os.unlink(temp_path)
    return content


def generate_editor_template(test_data=None):
    """Generate a template for the editor, optionally pre-populated with test data."""
    if test_data is None:
        # Default empty template
        return """\
# Edit the test details below. Lines starting with # will be ignored.
# Save and close the editor when done.

name: Test name here

# For input expression, write it between the START and END markers below
# You can use multiple lines for complex TokenScript expressions
# START_INPUT
Your TokenScript expression here
# END_INPUT

# For expected output, write it between the START and END markers below
# START_EXPECTED_OUTPUT
Expected result here
# END_EXPECTED_OUTPUT

expectedOutputType: Number # or String, Boolean, etc.

# Context (variables) section - use JSON format
# Remove the {} and add your context variables if needed, e.g.:
# {
#   "x": 3,
#   "y": "hello"
# }
context: {}
"""
    else:
        # Pre-populate template with existing test data
        # Convert the context back to JSON string with pretty formatting
        context_str = json.dumps(test_data.get("context", {}), indent=2)

        # Handle the expected output type
        output_type = test_data.get("exceptedOutputType", "") or test_data.get("expectedOutputType", "")

        # Create template with existing data
        return f"""\
# Edit the test details below. Lines starting with # will be ignored.
# Save and close the editor when done.

name: {test_data.get("name", "Test name here")}

# For input expression, write it between the START and END markers below
# You can use multiple lines for complex TokenScript expressions
# START_INPUT
{test_data.get("input", "Your TokenScript expression here")}
# END_INPUT

# For expected output, write it between the START and END markers below
# START_EXPECTED_OUTPUT
{test_data.get("expectedOutput", "Expected result here")}
# END_EXPECTED_OUTPUT

expectedOutputType: {output_type} # or String, Boolean, etc.

# Context (variables) section - use JSON format
context: {context_str}
"""


def parse_editor_content(user_input):
    """Parse the content from the editor."""
    test_data = {}
    context_json = "{}"

    # Extract multi-line input
    sections = {
        "input": {"start": "# START_INPUT", "end": "# END_INPUT"},
        "expectedOutput": {"start": "# START_EXPECTED_OUTPUT", "end": "# END_EXPECTED_OUTPUT"}
    }

    lines = user_input.split('\n')
    current_section = None
    section_content = []

    for line in lines:
        line_stripped = line.strip()

        # Check if line starts a section
        for section, markers in sections.items():
            if line_stripped == markers["start"]:
                current_section = section
                section_content = []
                break
            elif line_stripped == markers["end"]:
                if current_section:
                    # Join the collected lines and assign to test_data
                    section_text = '\n'.join(section_content).strip()
                    test_data[current_section] = section_text
                    current_section = None
                break

        # If we're in a section, collect the content
        if current_section and not line_stripped.startswith("#") and not line_stripped in [
            sections[current_section]["start"], sections[current_section]["end"]]:
            section_content.append(line)

        # Process regular key-value lines outside of sections
        if not current_section and ":" in line and not line.strip().startswith('#'):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key == "expectedOutputType":
                output_type = value.split("#")[0].strip()  # Remove any comments
                test_data[key] = output_type
            elif key not in test_data and key != "context" and key not in sections:
                test_data[key] = value

            if key == "context":
                context_json = value

    # Parse context JSON
    try:
        test_data["context"] = json.loads(context_json)
    except json.JSONDecodeError:
        print("Error parsing context JSON. Please check the format.")
        sys.exit(1)

    return test_data


def find_test_files():
    """Find all test files recursively in the tests directory."""
    test_files = []
    tests_dir = Path("tests")

    if not tests_dir.exists() or not tests_dir.is_dir():
        return []

    for path in tests_dir.glob("**/*.json"):
        test_files.append(str(path))

    return test_files


def select_test_to_edit(test_files):
    """Display a menu of test files to edit."""
    if not test_files:
        print("No test files found.")
        sys.exit(1)

    print("Available test files:")
    for i, path in enumerate(test_files, 1):
        print(f"{i}. {path}")

    while True:
        try:
            choice = input("\nSelect a test to edit (number) or 'q' to quit: ")
            if choice.lower() == 'q':
                sys.exit(0)

            index = int(choice) - 1
            if 0 <= index < len(test_files):
                return test_files[index]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


def create_or_edit_test(edit_mode=False, test_path=None):
    """Create a new test or edit an existing one."""
    test_data = None

    if edit_mode:
        if not test_path:
            test_files = find_test_files()
            test_path = select_test_to_edit(test_files)

        print(f"Editing test file: {test_path}")

        try:
            with open(test_path, 'r') as f:
                test_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error opening or parsing test file: {e}")
            sys.exit(1)

        template = generate_editor_template(test_data)
        action_desc = "Editing"
    else:
        template = generate_editor_template()
        action_desc = "Creating"

    print(f"{action_desc} a TokenScript compliance test")
    print("Opening editor to input test details...")

    user_input = get_user_input_with_editor(template)
    if not user_input:
        print("No input provided. Exiting.")
        sys.exit(1)

    test_data = parse_editor_content(user_input)

    # Determine the output path
    if edit_mode and test_path:
        test_file_path = test_path
    else:
        # Get the output location for new tests
        parser = argparse.ArgumentParser(description='Create a TokenScript compliance test')
        parser.add_argument('--category', default='math', help='Test category (subdirectory under tests/)')
        parser.add_argument('--filename', help='Filename for the test (without .json extension)')

        args = parser.parse_args()

        if not args.filename:
            filename = test_data.get("name", "new_test").lower().replace(" ", "_")
            args.filename = filename

        # Ensure the filename has .json extension
        if not args.filename.endswith('.json'):
            args.filename += '.json'

        # Create the directory if it doesn't exist
        test_dir = Path('tests') / args.category
        test_dir.mkdir(parents=True, exist_ok=True)

        # Full path for the test file
        test_file_path = test_dir / args.filename

        # Ask for confirmation if file exists
        if test_file_path.exists():
            confirm = input(f"File {test_file_path} already exists. Overwrite? [y/N]: ")
            if not confirm.lower().startswith('y'):
                print("Operation cancelled.")
                sys.exit(0)

    # Fix the misspelled key if exists in edited content
    if "exceptedOutputType" in test_data and "expectedOutputType" not in test_data:
        test_data["expectedOutputType"] = test_data.pop("exceptedOutputType")

    # Write the test to file
    with open(test_file_path, 'w') as f:
        json.dump(test_data, f, indent=4)

    print(f"Test successfully saved at: {test_file_path}")


def main():
    """Main function to parse arguments and call appropriate functions."""
    parser = argparse.ArgumentParser(description='Create or edit TokenScript compliance tests')

    # Add subparsers for create and edit modes
    subparsers = parser.add_subparsers(dest='mode', help='Mode of operation')

    # Create parser
    create_parser = subparsers.add_parser('create', help='Create a new test')
    create_parser.add_argument('--category', default='math', help='Test category (subdirectory under tests/)')
    create_parser.add_argument('--filename', help='Filename for the test (without .json extension)')

    # Edit parser
    edit_parser = subparsers.add_parser('edit', help='Edit an existing test')
    edit_parser.add_argument('--path', help='Path to the test file to edit')

    # Parse arguments
    args = parser.parse_args()

    # Default to create mode if no mode specified
    if not args.mode:
        create_or_edit_test(edit_mode=False)
    elif args.mode == 'create':
        create_or_edit_test(edit_mode=False)
    elif args.mode == 'edit':
        create_or_edit_test(edit_mode=True, test_path=args.path)


if __name__ == '__main__':
    main()
