# Adapted from Volare
#
# Copyright 2022-2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
import os
import sys
import subprocess
from typing import Any, ClassVar, Callable, Optional

import click
import hishel
import httpx
import ssl

from .version import __version__


class GitHubSession(hishel.CacheClient):
    inst: ClassVar["GitHubSession"]

    class Token(object):
        override: ClassVar[Optional[str]] = None

        @classmethod
        def get_gh_token(Self) -> Optional[str]:
            token = None

            # 0. Lowest priority: ghcli
            try:
                token = subprocess.check_output(
                    [
                        "gh",
                        "auth",
                        "token",
                    ],
                    encoding="utf8",
                    stderr=subprocess.PIPE,
                ).strip()
            except FileNotFoundError:
                pass
            except subprocess.CalledProcessError:
                pass

            # 1. Higher priority: environment GITHUB_TOKEN
            env_token = os.getenv("GITHUB_TOKEN")
            if env_token is not None and env_token.strip() != "":
                token = env_token

            # 2. Highest priority: the -t flag
            if Self.override is not None:
                token = Self.override

            return token

    def __init__(
        self,
        *,
        follow_redirects: bool = True,
        github_token: Optional[str] = None,
        ssl_context=None,
        **kwargs,
    ):
        if ssl_context is None:
            try:
                import truststore

                ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            except ImportError:
                pass

        controller = hishel.Controller(
            cacheable_methods=["GET"],
            cacheable_status_codes=[200],
            allow_stale=True,
        )

        storage = hishel.FileStorage(
            base_path=os.path.join(os.getcwd(), ".httpx-cache"),
            ttl=600,
        )

        try:
            super().__init__(
                follow_redirects=follow_redirects,
                verify=ssl_context,
                controller=controller,
                storage=storage,
                **kwargs,
            )
        except ValueError as e:
            if "Unknown scheme for proxy URL" in e.args[0] and "socks://" in e.args[0]:
                print(
                    f"Invalid SOCKS proxy: Volare only supports http://, https:// and socks5:// schemes: {e.args[0]}",
                    file=sys.stderr,
                )
                exit(-1)
            else:
                raise e from None
        github_token = github_token or GitHubSession.Token.get_gh_token()
        self.github_token = github_token

        raw_headers = {
            "User-Agent": type(self).get_user_agent(),
        }
        if github_token is not None:
            raw_headers["Authorization"] = f"Bearer {github_token}"
        self.headers = httpx.Headers(raw_headers)

    def api(
        self,
        method: str,
        endpoint: str,
        *args,
        **kwargs,
    ) -> Any:
        url = "https://api.github.com" + endpoint
        req = self.request(method, url, *args, **kwargs)
        req.raise_for_status()
        return req.json()

    @classmethod
    def get_user_agent(Self) -> str:
        return f"tollens/{__version__}"


GitHubSession.inst = GitHubSession()


def set_token_cb(
    ctx: click.Context,
    param: click.Parameter,
    value: Optional[str],
):
    GitHubSession.Token.override = value
    GitHubSession.inst = GitHubSession()


def opt_token(function: Callable) -> Callable:
    function = click.option(
        "-t",
        "--token",
        "session",
        default=None,
        required=False,
        expose_value=False,
        help="Replace the GitHub token used for GitHub requests, which is by default the value of the environment variable GITHUB_TOKEN or None.",
        callback=set_token_cb,
    )(function)
    return function
