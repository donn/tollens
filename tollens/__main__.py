# This is free and unencumbered software released into the public domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.

# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# For more information, please refer to <https://unlicense.org/>
import fnmatch

import click
from rich.progress import Progress

from .github import GitHubSession, opt_token
from .scripts import mirror_repo, recreate_issues


@click.group()
def cli():
    pass


@click.command()
@opt_token
@click.option(
    "-T", "--target", help="Target repository in the format organization/repo"
)
@click.argument("source")
def copy_issues(source, target):
    """
    Recreate issues and pull requests in a mirrored/forked repository
    """
    with Progress() as pb:
        recreate_issues(pb, source, target)


cli.add_command(copy_issues)


@click.command(hidden=True)
@opt_token
@click.option("-F", "--from", "from_user", required=True)
@click.option("-T", "--to", "tgt_org", required=True)
@click.argument("include_filters", nargs=-1)
def mirror_repos(from_user, tgt_org, include_filters):

    if len(include_filters) == 0:
        include_filters = ("*",)

    included_repos_by_name = {}
    repos = []
    page = 0
    last = None
    while last is None or len(last) == 100:
        page += 1
        last = GitHubSession.inst.api(
            "GET",
            f"/orgs/{from_user}/repos?per_page=100&page={page}",
        )
        repos += last
    for repo in repos:
        for filter in include_filters:
            if fnmatch.fnmatch(repo["name"], filter):
                included_repos_by_name[repo["name"]] = repo
                break

    with Progress() as pb:
        repo_ctr = pb.add_task("Repositories", total=len(included_repos_by_name))
        for i, data in enumerate(included_repos_by_name.values()):
            pb.update(task_id=repo_ctr, completed=i)
            mirror_repo(pb, tgt_org, data)


cli.add_command(mirror_repos)

if __name__ == "__main__":
    cli()
