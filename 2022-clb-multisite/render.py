"""
Short module to render the `README.md` file from the `README.template` file and
the `mapping.py`.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from lyscripts.data.lyproxify import generate_markdown_docs

from mapping import COLUMN_MAP

if __name__ == "__main__":
    parent_dir = Path(__file__).parent
    env = Environment(loader=FileSystemLoader(parent_dir))
    template = env.get_template("README.template")
    result = template.render(description=generate_markdown_docs(COLUMN_MAP))

    with open(parent_dir / "README.partial", "w") as f:
        f.write(result)
