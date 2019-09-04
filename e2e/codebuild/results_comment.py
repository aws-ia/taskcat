import os
import sys

import boto3

from github import Github

SSM_CLIENT = boto3.client("ssm")

GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "")
PR_NUMBER = os.environ.get("PR_NUMBER", "")
FAILED = bool(int(sys.argv[2]))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


if __name__ == "__main__":
    repo = Github(GITHUB_TOKEN).get_repo(GITHUB_REPO_NAME)
    pr = repo.get_pull(int(PR_NUMBER))
    message, event = ("end to end tests failed", "REQUEST_CHANGES")
    if not FAILED:
        message, event = ("end to end tests passed\n", "APPROVE")
        with open("../../cov_report", "r") as fh:
            cov = fh.read().replace(f"/{GITHUB_REPO_NAME}/", "")
            message += f"```{cov}```"
    pr.create_review(body=message, event=event, commit=repo.get_commit(sys.argv[1]))
