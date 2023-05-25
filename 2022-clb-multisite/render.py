"""
Short module to render the `README.md` file from the `README.template` file and
the `mapping.py`.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from lazydocs import MarkdownGenerator

from lyscripts.data.lyproxify import generate_markdown_docs

import mapping


if __name__ == "__main__":
    generator = MarkdownGenerator()
    parent_dir = Path(__file__).parent
    env = Environment(loader=FileSystemLoader(parent_dir))
    template = env.get_template("README.template")
    result = template.render(
        column_description=generate_markdown_docs(mapping.COLUMN_MAP),
        mapping_docs=generator.import2md(mapping, depth=2),
    )

    with open(parent_dir / "README.md", mode="w", encoding="utf-8") as f:
        f.write(result)
