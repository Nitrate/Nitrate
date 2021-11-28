#!/usr/bin/env python3

import re
import argparse
import subprocess
from pathlib import Path

from datetime import datetime
from typing import Tuple
from pygit2 import Commit, Repository


def extract_short_log(commit: Commit) -> Tuple[str, None or str]:
    lines = commit.message.split('\n')
    subject = lines[0]
    match = re.search(r'\((#\d+)\)$', subject)
    return subject, match.groups()[0] if match else None


def generate_changelog(args: argparse.Namespace):
    repo: Repository = Repository(args.repo or '.')
    if args.since_version:
        release_tag = repo.revparse_single(args.since_version)
    else:
        release_tag = repo.revparse_single(repo.describe().split('-')[0])

    walker = repo.walk(repo.head.target)
    walker.hide(release_tag.id)
    logs = []
    found_issue_keys = []

    for commit in walker:
        subject, issue_key = extract_short_log(commit)
        if issue_key is not None:
            found_issue_keys.append(issue_key)
            subject = subject.replace(issue_key, f'`{issue_key}`_')
        logs.append(f'* {subject}')

    logs.append('')
    found_issue_keys.sort()
    for item in found_issue_keys:
        logs.append(f'.. _{item}: https://github.com/Nitrate/Nitrate/issues/{item[1:]}')

    return '\n'.join(logs)


def validate_version(value):
    if value.startswith('v'):
        raise argparse.ArgumentTypeError('Version should not be prefixed with v.')
    return value


parser = argparse.ArgumentParser()
parser.add_argument('--repo', help='Path to git repository.')
parser.add_argument('--since-version', required=False,
                    type=validate_version,
                    help='Collect commits since this version.')
parser.add_argument('new_version', metavar='NEW_VERSION',
                    type=validate_version,
                    help='The version to be released.')

args = parser.parse_args()
new_version = args.new_version

Path('VERSION.txt').unlink()
Path('VERSION.txt').write_text(new_version, "utf-8")

template = Path('contrib/scripts/release-notes.tmpl.rst').read_text("utf-8")
Path(f'docs/source/releases/{new_version}.rst').write_text(
    template.format(
        new_version=new_version,
        doc_ref=new_version,
        title_marker=len(new_version) * '=',
        change_logs=generate_changelog(args),
        release_date=datetime.now().strftime('%b %d, %Y')
    ),
    "utf-8",
)

readme_md = Path('container/README.md')
content = readme_md.read_text("utf-8")
readme_md.unlink()
readme_md.write_text(
    re.sub(r'quay.io/nitrate/nitrate:\d+\.\d+(\.\d+)?',
           f'quay.io/nitrate/nitrate:{new_version}',
           content),
    "utf-8",
)

subprocess.check_call([
    'rpmdev-bumpspec',
    '-n', new_version,
    '-c', f'Built for version {new_version}',
    'python-nitrate-tcms.spec'
])
