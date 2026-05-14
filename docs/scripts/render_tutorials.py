from pathlib import Path
import subprocess
import os


def check_quarto():
    try:
        subprocess.run(
            ["quarto", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def find_tutorials():
    tutorials_dir = Path("..") / "docs" / "tutorials" / "quarto"
    return list(tutorials_dir.glob("*.qmd"))


def render_tutorial(tutorial_path):
    org_path = os.getcwd()
    os.chdir(tutorial_path.parent)

    command = [
        "quarto",
        "render",
        str(tutorial_path.name),
        # "--to",
        # "gfm",
        # "--output",
        # str(tutorial_path.with_suffix(".md").name),
        # "--quiet",
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Successfully rendered {tutorial_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error rendering {tutorial_path}: {e}")
    finally:
        os.chdir(org_path)

    # Move the rendered markdown file one directory up
    rendered_md = tutorial_path.with_suffix(".md")
    if rendered_md.exists():
        rendered_md.rename(tutorial_path.parent.parent / rendered_md.name)

    renderend_ipynb = tutorial_path.with_suffix(".ipynb")
    if renderend_ipynb.exists():
        renderend_ipynb.rename(tutorial_path.parent.parent / renderend_ipynb.name)


if __name__ == "__main__":
    if not check_quarto():
        print(
            "Quarto is not installed or not found in PATH. Please install Quarto to render the tutorials."
        )
        exit(1)

    tutorials = find_tutorials()

    for tutorial in tutorials:
        render_tutorial(tutorial)
