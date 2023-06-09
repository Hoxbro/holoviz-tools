from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from rich.console import Console
from rich.table import Table

COLUMNS = {
    "name": "Workflow",
    "head_branch": "Branch",
    "display_title": "Title",
    "status": "Status",
    "run_started_at": "Duration",
    "triggering_actor.login": "User",
}

REPOS = [
    # "colorcet",
    "datashader",
    "geoviews",
    # "holonote",
    "holoviews",
    # "holoviz",
    "hvplot",
    # "jupyter-panel-proxy",
    "lumen",
    "panel",
    "param",
    # "pyviz_comms",
    # "spatialpandas",
]


def get_info(repo) -> pd.DataFrame | None:
    url = f"https://api.github.com/repos/holoviz/{repo}/actions/runs"
    resp = requests.get(url, params={"per_page": 30})
    assert resp.ok, "API timeout"
    df = pd.json_normalize(resp.json(), "workflow_runs")
    df = df[df["status"] != "completed"]
    if df.empty:
        return

    df = df[list(COLUMNS)].rename(COLUMNS, axis=1)
    df["Repo"] = repo
    return df


def main() -> None:
    console = Console()
    with console.status("Getting status of Github Actions"):
        with ThreadPoolExecutor() as ex:
            futures = ex.map(get_info, REPOS)

    try:
        df = pd.concat(futures)
    except ValueError:
        print("No running Github Actions")
        return

    df = df.sort_values("Duration", ascending=False)
    df["Duration"] = (
        (pd.Timestamp.now(tz="UTC") - pd.to_datetime(df["Duration"]))
        .dt.total_seconds()
        .apply(lambda x: f"{x / 60:0.0f} min")
    )
    print_table(df, console)


def print_table(df, console) -> None:
    table = Table(title="Running Github Actions")
    for c in df.columns:
        table.add_column(c)

    for r in df.itertuples(index=False):
        table.add_row(*r)

    console.print(table)


if __name__ == "__main__":
    main()
