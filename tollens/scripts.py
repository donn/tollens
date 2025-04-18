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
import os
import sys
import time
import tempfile
import subprocess

import httpx
from rich.progress import Progress
from sortedcontainers import SortedDict

from .github import GitHubSession
from .clean_body import clean_body


def do_comments(src_repo, tgt_repo, issue):
    comments = GitHubSession.inst.api(
        "GET",
        f"/repos/{src_repo}/issues/{issue['number']}/comments",
    )

    for cmt in comments:
        body = f"[Originally posted]({cmt['html_url']}) by [{cmt['user']['login']}]({cmt['user']['html_url']}) at {cmt['created_at']}\n\n---\n\n"
        body += clean_body(cmt["body"])

        GitHubSession.inst.api(
            "POST",
            f"/repos/{tgt_repo}/issues/{issue['number']}/comments",
            json={"body": body},
        )
        time.sleep(1)


def recreate_pr(src_repo, tgt_repo, issue):
    print(f"Recreating '{issue['title']}' (#{issue['number']})…")

    body = f"Pull Request [originally created]({issue['html_url']}) by [{issue['user']['login']}]({issue['user']['html_url']}) on {issue['created_at']}\n\n"
    body += f"Merging: {issue['head']['ref']} @ {issue['head']['sha']}\n\n"
    body += f"To base branch: {issue['base']['ref']} @ {issue['base']['sha']}\n\n"

    body += "---\n\n"

    body += clean_body(issue["body"])

    exists = True
    try:
        GitHubSession.inst.api(
            "GET",
            f"/repos/{tgt_repo}/issues/{issue['number']}",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            exists = False
        else:
            raise e from None
    if exists:
        GitHubSession.inst.api(
            "PATCH",
            f"/repos/{tgt_repo}/issues/{issue['number']}",
            json={"title": f"[PR] {issue['title']}", "body": body},
        )
    else:
        GitHubSession.inst.api(
            "POST",
            f"/repos/{tgt_repo}/issues",
            json={"title": f"[PR] {issue['title']}", "body": body},
        )

    # Comment with PR content
    patch = GitHubSession.inst.request("GET", issue["diff_url"]).text
    patch_lines = patch.splitlines()
    current_body = ""
    while len(patch_lines):
        line = patch_lines.pop(0)
        current_body += f"{line}\n"
        if len(current_body) >= 60000:
            GitHubSession.inst.api(
                "POST",
                f"/repos/{tgt_repo}/issues/{issue['number']}/comments",
                json={"body": f"``````diff\n{current_body}\n``````"},
            )
            current_body = ""

    if len(current_body):
        GitHubSession.inst.api(
            "POST",
            f"/repos/{tgt_repo}/issues/{issue['number']}/comments",
            json={"body": f"``````diff\n{current_body}\n``````"},
        )

    do_comments(src_repo, tgt_repo, issue)

    if close_date := issue["closed_at"]:
        action = "Merged" if "merged_at" in issue else "Closed"

        GitHubSession.inst.api(
            "POST",
            f"/repos/{tgt_repo}/issues/{issue['number']}/comments",
            json={
                "body": f"{action} by [{issue['user']['login']}]({issue['user']['html_url']}) on {close_date}"
            },
        )

        GitHubSession.inst.api(
            "PATCH",
            f"/repos/{tgt_repo}/issues/{issue['number']}",
            json={"state": "closed"},
        )


def recreate_issue(src_repo, tgt_repo, issue):
    print(f"Recreating '{issue['title']}' (#{issue['number']})…")
    body = ""

    header = f"Issue [originally created]({issue['html_url']}) by [{issue['user']['login']}]({issue['user']['html_url']}) on {issue['created_at']}"

    body += header + "\n\n---\n\n"

    body += clean_body(issue["body"])
    exists = True
    try:
        GitHubSession.inst.api(
            "GET",
            f"/repos/{tgt_repo}/issues/{issue['number']}",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            exists = False
        else:
            raise e from None
    if exists:
        GitHubSession.inst.api(
            "PATCH",
            f"/repos/{tgt_repo}/issues/{issue['number']}",
            json={"title": f"{issue['title']}", "body": body},
        )
    else:
        GitHubSession.inst.api(
            "POST",
            f"/repos/{tgt_repo}/issues",
            json={"title": f"{issue['title']}", "body": body},
        )

    do_comments(src_repo, tgt_repo, issue)

    if close_date := issue["closed_at"]:
        GitHubSession.inst.api(
            "POST",
            f"/repos/{tgt_repo}/issues/{issue['number']}/comments",
            json={
                "body": f"Closed by [{issue['user']['login']}]({issue['user']['html_url']}) on {close_date}"
            },
        )

        GitHubSession.inst.api(
            "PATCH",
            f"/repos/{tgt_repo}/issues/{issue['number']}",
            json={"state": "closed"},
        )


def recreate_issues(pb: Progress, src_repo, tgt_repo):
    issues = []
    page = 0
    last = None
    while last is None or len(last) == 100:
        page += 1
        last = GitHubSession.inst.api(
            "GET",
            f"/repos/{src_repo}/issues?per_page=100&page={page}&state=all",
        )
        issues += last
        time.sleep(1)
    page = 0
    last = None
    while last is None or len(last) == 100:
        page += 1
        last = GitHubSession.inst.api(
            "GET",
            f"/repos/{src_repo}/pulls?per_page=100&page={page}&state=all",
        )
        issues += last
        time.sleep(1)

    issues_by_number = SortedDict()
    for issue in issues:
        issues_by_number[issue["number"]] = issue

    issue_ctr = pb.add_task("Issues", total=len(issues_by_number))
    for number, info in issues_by_number.items():
        if str(info["number"]) != "94":
            continue
        pb.update(task_id=issue_ctr, completed=number)
        is_pr = "patch_url" in info
        if is_pr:
            recreate_pr(src_repo, tgt_repo, info)
        else:
            recreate_issue(src_repo, tgt_repo, info)
        time.sleep(1)


def mirror_repo(pb: Progress, tgt_org, repo):
    src_repo = repo["full_name"]
    tgt_repo = f"{tgt_org}/{repo['name']}"

    # 0. Get username
    try:
        user = GitHubSession.inst.api("GET", "/user")
    except httpx.HTTPStatusError as e:
        print(
            f"Valid token is required for mirroring repos: {e}",
            file=sys.stderr,
        )
        exit(-1)

    # 1. Create repo
    GitHubSession.inst.api(
        "POST",
        f"/orgs/{tgt_org}/repos",
        json={"name": repo["name"], "description": repo["description"]},
    )

    # 2. Mirror repo
    with tempfile.TemporaryDirectory("tollens") as td:
        subprocess.check_call(
            ["git", "clone", "--bare", "--verbose", repo["clone_url"]],
            cwd=td,
        )
        clone_path = os.path.join(td, repo["name"] + ".git")
        subprocess.check_call(
            [
                "git",
                "push",
                "--mirror",
                f"https://{user['login']}:{GitHubSession.Token.get_gh_token()}@github.com/{tgt_repo}",
            ],
            cwd=clone_path,
        )

    # 3. Mirror issues and PRs
    recreate_issues(pb, src_repo, tgt_repo)
