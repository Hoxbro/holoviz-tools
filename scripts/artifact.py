from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from shutil import rmtree
from subprocess import check_output
from zipfile import ZipFile
from functools import cache
from datetime import datetime

import requests
import rich_click as click
from rich.console import Console

from _vendor.simple_term_menu import TerminalMenu

# Needs diff-so-fancy in path

PATH = Path("~/.cache/holoviz-cli/artifact").expanduser().resolve()
PATH.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
}
console = Console()


@cache
def download_runs(repo, workflow, page=1) -> tuple[dict, dict]:
    url = (
        f"https://api.github.com/repos/holoviz/{repo}/actions/workflows/{workflow}/runs"
    )
    resp = requests.get(url, params={"page": page, "per_page": 30}, headers=HEADERS)
    assert resp.ok

    results, urls = {}, {}
    for run in resp.json()["workflow_runs"]:
        if run["status"] == "completed":
            no = run["run_number"]
            date = datetime.fromisoformat(run["created_at"])
            display = f"{no:<5} {run['conclusion']:<13} {date:%Y-%m-%d %H:%M}    branch: {run['head_branch']} "
            results[no] = display
            urls[no] = run["url"] + "/artifacts"

    return results, urls


def select_runs(repo, workflow) -> tuple[int, int]:
    with console.status("Fetching runs..."):
        runs, _ = download_runs(repo, workflow)

    terminal_menu = TerminalMenu(
        runs.values(),
        title=f"Select a good run for {repo}",
    )
    menu = terminal_menu.show()
    good_run = list(runs)[menu]
    del runs[good_run]

    terminal_menu = TerminalMenu(
        runs.values(),
        title=f"Select a bad run for {repo}",
    )
    menu = terminal_menu.show()
    bad_run = list(runs)[menu]

    return good_run, bad_run


def get_artifact_urls(repo, workflow, good_run, bad_run) -> tuple[str, str]:
    good_url, bad_url = None, None
    for page in range(1, 10):
        _, urls = download_runs(repo, workflow, page)
        if good_run in urls:
            good_url = urls[good_run]
        if bad_run in urls:
            bad_url = urls[bad_run]
        if good_url and bad_url:
            break
    return good_url, bad_url


def download_artifact(repo, pr, url) -> None:
    download_path = PATH / f"{repo}_{pr}"
    if download_path.exists():
        return

    resp = requests.get(url, headers=HEADERS)
    assert resp.ok
    artifact = resp.json()["artifacts"]
    if not artifact:
        download_path.mkdir(exist_ok=True)
        return
    download_url = artifact[0]["archive_download_url"]
    zipfile = requests.get(download_url, headers=HEADERS)
    assert resp.ok

    bio = BytesIO(zipfile.content)
    bio.seek(0)
    with ZipFile(bio) as zip_ref:
        zip_ref.extractall(download_path)


def get_files(
    repo, good_run, bad_run, test, os, python, workflow, force
) -> tuple[Path, Path]:
    if good_run is None or bad_run is None:
        good_run, bad_run = select_runs(repo, workflow)
        click.echo(f"Selected good run {good_run} and bad run {bad_run}")

    good_path = PATH / f"{repo}_{good_run}"
    bad_path = PATH / f"{repo}_{bad_run}"

    if force:
        rmtree(good_path, ignore_errors=True)
        rmtree(bad_path, ignore_errors=True)

    with console.status("Downloading artifacts..."):
        good_url, bad_url = get_artifact_urls(repo, workflow, good_run, bad_run)
        download_artifact(repo, good_run, good_url)
        download_artifact(repo, bad_run, bad_url)

    found = False
    for file in good_path.iterdir():
        name = file.name.lower()
        if os in name and python in name and f"_{test}" in name:
            found = True
            break

    if not found:
        return None, None

    good_file = good_path / file.name
    bad_file = bad_path / file.name
    return good_file, bad_file


@click.command(context_settings={"show_default": True})
@click.argument("good_run", type=int, required=False)
@click.argument("bad_run", type=int, required=False)
@click.option(
    "--repo",
    default="holoviews",
    type=click.Choice(["holoviews", "panel", "hvplot", "datashader", "geoviews"]),
    help="Repository",
)
@click.option(
    "--test",
    default="unit",
    type=click.Choice(["unit", "ui", "core"]),
    help="Test type",
)
@click.option(
    "--os",
    default="linux",
    type=click.Choice(["linux", "mac", "windows"]),
    help="Operating system",
)
@click.option(
    "--python",
    default="3.11",
    type=click.Choice(["3.8", "3.9", "3.10", "3.11"]),
    help="Python version",
)
@click.option(
    "--workflow",
    default="test.yaml",
    type=str,
    help="Workflow filename",
)
@click.option(
    "--force/--no-force",
    default=False,
    help="Force download artifacts",
)
def cli(good_run, bad_run, repo, test, os, python, workflow, force) -> None:
    good_file, bad_file = get_files(
        repo, good_run, bad_run, test, os, python, workflow, force
    )

    if not good_file or not good_file.exists():
        console.print(
            "Good artifact does not exists. Please check the options.",
            style="bright_red",
        )
        return
    if not bad_file or not bad_file.exists():
        console.print(
            "Bad artifact does not exists. Please check the options.",
            style="bright_red",
        )
        return

    cmd = f"git diff {bad_file} {good_file} | diff-so-fancy"
    diff = check_output(cmd, shell=True).decode()

    if diff:
        click.echo(diff)
    else:
        click.echo("No differences found for the given parameters.")


if __name__ == "__main__":
    cli()
