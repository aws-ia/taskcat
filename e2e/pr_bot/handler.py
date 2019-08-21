import json
import logging
import os
import traceback

import boto3

from github import Github

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

S3_CLIENT = boto3.client("s3")
CB_CLIENT = boto3.client("codebuild")
SSM_CLIENT = boto3.client("ssm")

BUILD_JOB_NAME = os.environ.get("BUILD_JOB_NAME", "")

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
S3_KEY = os.environ.get("S3_KEY", "")

GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "")
MAINTAINERS = json.loads(os.environ.get("PROJECT_MAINTAINERS", ""))
TEST_TAGS = json.loads(os.environ.get("TEST_TAGS", ""))


def get_token():
    param = os.environ.get("GITHUB_TOKEN", "")
    resp = SSM_CLIENT.get_parameters(Names=[param], WithDecryption=True)
    return resp["Parameters"][0]["Value"]


def get_history():
    if not S3_BUCKET_NAME or not S3_KEY:
        raise ValueError("Environment variables for s3 bucket not set")
    try:
        data = S3_CLIENT.get_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY)["Body"]
    except S3_CLIENT.exceptions.NoSuchKey:
        return []
    return json.loads(data.read())


def set_history(history):
    history = list(set(history))
    body = bytes(json.dumps(history).encode("utf8"))
    S3_CLIENT.put_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY, Body=body)


def comment_is_command(comment):
    for l in comment.split("\n"):
        for t in TEST_TAGS:
            if l.startswith(t):
                return True
    return False


def get_pending_builds(history):
    comments = {}
    repo = Github(get_token()).get_repo(GITHUB_REPO_NAME)
    prs = repo.get_pulls(state="open")
    for pr in prs:
        if pr.base.ref != "master":
            continue
        for comment in pr.get_issue_comments():
            if comment.id in history:
                continue
            if not comment_is_command(comment.body):
                continue
            if comment.user.login not in MAINTAINERS:
                LOG.warning(f"{comment.user.login} is not listed as a maintainer")
                continue
            if pr.number in comments:
                comments[pr.number]["comment_ids"].add(comment.id)
                continue
            comments[pr.number] = {
                "comment_ids": {comment.id},
                "pr_repo_name": pr.head.repo.full_name.split("/")[1],
                "pr_github_org": pr.head.repo.full_name.split("/")[0],
                "pr_branch": pr.head.ref,
            }
    return comments


def handler(_, __):
    history = get_history()
    builds = get_pending_builds(history)
    for pr_number, pr_details in builds.items():
        try:
            LOG.info(
                f"starting build for pr #{pr_number} due to comments "
                f"{pr_details['comment_ids']}"
            )
            CB_CLIENT.start_build(
                projectName=BUILD_JOB_NAME,
                environmentVariablesOverride=[
                    {"name": "PR_NUMBER", "value": str(pr_number), "type": "PLAINTEXT"},
                    {
                        "name": "PR_REPO_NAME",
                        "value": pr_details["pr_repo_name"],
                        "type": "PLAINTEXT",
                    },
                    {
                        "name": "PR_GITHUB_ORG",
                        "value": pr_details["pr_github_org"],
                        "type": "PLAINTEXT",
                    },
                    {
                        "name": "PR_BRANCH",
                        "value": pr_details["pr_branch"],
                        "type": "PLAINTEXT",
                    },
                ],
            )
            history += list(pr_details["comment_ids"])
        except Exception:
            LOG.error("failed to start build")
            traceback.print_exc()
    set_history(history)
