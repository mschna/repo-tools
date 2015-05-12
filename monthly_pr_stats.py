#!/usr/bin/env python
"""
Calculate pull requests opened and their current status by month.

Returns the raw # of PRs opened, and their resultant state in a table:
Month | #merged | #rejected | #unresolved | #opened |

Note that this means the stats will change over time until all PRs are resolved.
The sum of the first three data columns (#merged, #rejected, #unresolved) must equal
the final column (#opened).
"""

from __future__ import print_function

import argparse
import collections
import datetime
import itertools
import re
import sys

from helpers import (
    date_bucket_quarter, date_bucket_month, date_bucket_week,
    date_arg, make_timezone_aware, lines_in_pull, print_repo_output
)
from repos import Repo


def get_all_repos(date_bucket_fn, start, lines=False, internal=False):
    repos = [r for r in Repo.from_yaml() if r.track_pulls]

    dimensions = [["merged", "closed", "unresolved", "opened"]]
    if internal:
        dimensions.append(["internal"])
    else:
        dimensions.append(["external"])

    keys = [" ".join(prod) for prod in itertools.product(*dimensions)]
    bucket_blank = dict.fromkeys(keys, 0)

    buckets = collections.defaultdict(lambda: dict(bucket_blank))
    for repo in repos:
        get_bucket_data(buckets, repo.name, date_bucket_fn, start=start, lines=lines, internal=internal)

    print_repo_output(keys, buckets)


def get_bucket_data(buckets, repo_name, date_bucket_fn, start, lines=False, internal=False):
    print(repo_name)
    pull_details = "all" if lines else "list"
    for pull in get_pulls(repo_name, state="all", pull_details=pull_details, org=True):
        # print("{0.id}: {0.combinedstate} {0.intext}".format(pull))

        intext = pull.intext  # internal or external
        # if internal is True, only want to look at "internal" PRs, and if
        # internal is False, only want to look at "external" PRs.
        if (internal and intext != 'internal') or (not internal and intext != 'external'):
            continue

        ignore_ref = "(^release$|^rc/)"
        if re.search(ignore_ref, pull.base_ref):
            # print("Ignoring pull #{0.number}: {0.title}".format(pull))
            continue

        if lines:
            increment = lines_in_pull(pull)
        else:
            increment = 1

        created = make_timezone_aware(pull.created_at)
        bucket_key = date_bucket_fn(created)
        if created >= start:
            buckets[bucket_key]["opened " + intext] += increment

            # Bucket based on its current state 
            if pull.combinedstate == "merged":
                buckets[bucket_key]["merged " + intext] += increment
            elif pull.combinedstate == "closed":
                buckets[bucket_key]["closed " + intext] += increment
            else:
                # PR is still open
                buckets[bucket_key]["unresolved " + intext] += increment


def main(argv):
    parser = argparse.ArgumentParser(description="Calculate external pull requests opened, and their current resolution status, by month.")
    parser.add_argument(
        "--quarterly", action="store_true",
        help="Report on quarters instead of months"
    )
    parser.add_argument(
        "--weekly", action="store_true",
        help="Report on weeks instead of months"
    )
    parser.add_argument(
        "--internal", action="store_true",
        help="Report on internal, rather than external, prs."
    )
    parser.add_argument(
        "--lines", action="store_true",
        help="Count the number of lines changed instead of number of pull requests"
    )
    parser.add_argument(
        "--start", type=date_arg,
        help="Date to start collecting, format is flexible: "
        "20141225, Dec/25/2014, 2014-12-25, etc"
    )
    parser.add_argument(
        "--db", action="store_true",
        help="Use WebhookDB instead of GitHub API"
    )
    args = parser.parse_args(argv[1:])

    if args.quarterly:
        date_bucket_fn = date_bucket_quarter
    elif args.weekly:
        date_bucket_fn = date_bucket_week
    else:
        date_bucket_fn = date_bucket_month

    if args.start is None:
        # Start keeping track Jun 1 2013 (when we became open source)
        args.start = make_timezone_aware(datetime.datetime(2013, 6, 1))

    global get_pulls
    if args.db:
        from webhookdb import get_pulls
    else:
        from githubapi import get_pulls

    get_all_repos(date_bucket_fn, start=args.start, lines=args.lines, internal=args.internal)


if __name__ == "__main__":
    sys.exit(main(sys.argv))