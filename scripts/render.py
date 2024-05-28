"""
Short module to render the `README.md` file from the `README.template` file and
the `mapping.py`.
"""
import argparse
import importlib.util
import sys
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from lazydocs import MarkdownGenerator
from lyscripts.data.lyproxify import generate_markdown_docs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="render",
        description=__doc__,
    )
    parser.add_argument(
        "-m", "--mapping", type=Path, default="mapping.py",
        help="Path to the mapping file.",
    )
    parser.add_argument(
        "-t", "--template", type=Path, default="README.template",
        help="Path to the template file.",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default="README.md",
        help="Path to the output file.",
    )
    parser.add_argument(
        "-d", "--data", type=Path, default="data.csv",
        help="Path to the data file.",
    )
    args = parser.parse_args()

    # get number of patients from data file
    data = pd.read_csv(args.data, header=[0, 1, 2])
    num_patients = len(data)

    # dynamically load mapping module
    spec = importlib.util.spec_from_file_location("mapping", args.mapping)
    mapping = importlib.util.module_from_spec(spec)
    sys.modules["mapping"] = mapping
    spec.loader.exec_module(mapping)

    # get generator to generate markdown docs
    generator = MarkdownGenerator()

    # use jinja2 to render the template
    parent_dir = Path(__file__).parent
    env = Environment(loader=FileSystemLoader(args.template.parent))
    template = env.get_template(args.template.name)
    result = template.render(
        num_patients=num_patients,
        column_description=generate_markdown_docs(mapping.COLUMN_MAP),
        mapping_docs=generator.import2md(mapping, depth=2),
    )

    # write result to output file
    with open(args.output, mode="w", encoding="utf-8") as f:
        f.write(result)
