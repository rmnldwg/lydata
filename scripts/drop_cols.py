"""Drop specified columns from a CSV file and save the result to a new CSV file."""

import pandas as pd
import typer

app = typer.Typer()


@app.command()
def drop_cols(
    input_csv: str = typer.Option(..., help="Path to the input CSV file."),
    output_csv: str = typer.Option(..., help="Path to the output CSV file."),
    cols: str = typer.Option(
        ..., help="Comma-separated list of top-level cols to drop."
    ),
):
    """Drop specified columns from a CSV file and save the result to a new CSV file."""
    # Read the input CSV file
    df = pd.read_csv(input_csv, header=[0, 1, 2])

    # Drop the specified columns
    cols_to_drop = [col.strip() for col in cols.split(",")]
    df = df.drop(columns=cols_to_drop)

    # Save the result to a new CSV file
    df.to_csv(output_csv, index=False)


if __name__ == "__main__":
    app()
