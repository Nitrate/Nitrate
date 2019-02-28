#!/usr/bin/python3

import argparse
import git
import re

parser = argparse.ArgumentParser()
parser.add_argument('--repo', help='Path to git repository.')
parser.add_argument('--since-version', required=False, help='Collect commits since this version.')
parser.add_argument('--link-issues', required=False, action='store_true',
                    help='Generate link markup for issues.')

args = parser.parse_args()

repo = git.Repo(args.repo or '.')

if args.since_version:
    last_version = args.since_version
else:
    last_version = repo.git.describe().split('-')[0]

issue_numbers = []

for commit in repo.iter_commits(f'HEAD...{last_version}'):
    match = re.search(r'Fixes #(\d+)', commit.message, re.MULTILINE)
    if match:
        if args.link_issues:
            issue_number = match.groups()[0]
            fixed_issue = f'- `#{issue_number}`_ '
            issue_numbers.append(issue_number)
        else:
            fixed_issue = '- #{} '.format(match.groups()[0])
    else:
        fixed_issue = ''
    print(f'* {commit.summary} {fixed_issue}({commit.author})')

if args.link_issues:
    print()
    for item in sorted(map(int, issue_numbers)):
        print(f'.. _#{item}: https://github.com/Nitrate/Nitrate/issues/{item}/')
