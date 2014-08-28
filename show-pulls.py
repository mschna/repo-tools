#!/usr/bin/env python
from __future__ import print_function

import argparse
import collections
import datetime
import more_itertools
import operator
import sys

import dateutil.parser

from helpers import paginated_get, requests
from pulls import get_pulls
from repos import Repo

ISSUE_FMT = (
    "{number:5d:white:bold} {repo:3s} {user.login:>17s:cyan} {comments:3d:red}"
    "  {title:.100s}"
    " {pull.commits}c{pull.changed_files}f"
    " {pull.additions:green}+{pull.deletions:red}-"
    " {combinedstate:pad:{combinedstatecolor}:negative}"
    " {updated_at:ago:white} {created_at:%b %d:yellow}"
    " {labels:spacejoin:pad:yellow:negative}"
)
COMMENT_FMT = "{:31}{user.login:cyan} {created_at:%b %d:yellow}  \t{body:oneline:.100s:white}"


def show_pulls(labels=None, show_comments=False, state="open", since=None, org=False, intext=None):
    num = 0
    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]
    for repo in repos:
        issues = get_pulls(repo.name, labels, state, since, org=org or intext, pull_details="all")

        category = None
        for issue in issues:
            issue["repo"] = repo.nick
            if intext is not None:
                if issue["intext"] != intext:
                    continue
            if org and issue.get("org") != category:
                # new category! print category header
                category = issue["org"]
                print("-- {category} ----".format(category=category))

            if 0:
                import pprint
                pprint.pprint(issue.obj)
            print(issue.format(ISSUE_FMT))
            num += 1

            if show_comments:
                comments_url = URLObject(issue['comments_url'])
                comments_url = comments_url.set_query_param("sort", "created")
                comments_url = comments_url.set_query_param("direction", "desc")
                comments = paginated_get(comments_url)
                last_five_comments = reversed(more_itertools.take(5, comments))
                for comment in last_five_comments:
                    print(comment.format(COMMENT_FMT))

    print()
    print("{num} pull requests".format(num=num))


if 0:
    """
    db.prs.find({  created_at: {   $gte: "2014-01-01T00:00:00.000Z",   $lt: "2014-04-01T00:00:00.000Z"  } }).count()
    db.prs.find({  created_at: {   $gte: "2014-04-01T00:00:00.000Z",   $lt: "2014-07-01T00:00:00.000Z"  } }).count()
    db.prs.find({ "pull.merged": true, "pull.merged_at": {   $gte: "2014-04-01T00:00:00.000Z",   $lt: "2014-07-01T00:00:00.000Z"  } }).count()
    db.prs.find({ "pull.merged": true, "pull.merged_at": {   $gte: "2014-01-01T00:00:00.000Z",   $lt: "2014-04-01T00:00:00.000Z"  } }).count()
    """

    from pymongo import MongoClient
    def insert_pulls(labels=None, state="open", since=None, org=False):
        mongo_client = MongoClient()
        mongo_collection = mongo_client.prs.prs

        issues = get_pulls("edx/edx-platform", labels, state, since, org)
        for issue in issues:
            mongo_collection.insert(issue)


if 0:
    def yearmonth(d):
        return dateutil.parser.parse(d).strftime("%Y%m")

    def show_pulls(labels=None, show_comments=False, state="open", since=None, org=False):
        months = collections.defaultdict(lambda: {'opened': 0, 'merged': 0})
        issues = get_pulls("edx/edx-platform", labels, state, since, org, pull_details="all")
        for issue in issues:
            months[yearmonth(issue['created_at'])]['opened'] += 1
            if issue['pull.merged']:
                months[yearmonth(issue['pull.merged_at'])]['merged'] += 1

        print(months)
        for ym, data in sorted(months.items()):
            print("{ym},{data[opened]},{data[merged]}".format(ym=ym, data=data))


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("--closed", action='store_true',
        help="Include closed pull requests",
        )
    parser.add_argument("--open", action='store_true',
        help="Include open pull requests",
        )
    parser.add_argument("--external", action='store_true',
        help="Include external pull requests",
        )
    parser.add_argument("--internal", action='store_true',
        help="Include internal pull requests",
        )
    parser.add_argument("--comments", dest="show_comments", action='store_true',
        help="Also show 5 most recent comments",
        )
    parser.add_argument("--debug",
        help="See what's going on.  DEBUG=http or json are fun.",
        )
    parser.add_argument("--org", action='store_true',
        help="Include and sort by affiliation",
        )
    parser.add_argument("--since", metavar="DAYS", type=int,
        help="Include pull requests active in the last DAYS days.",
        )

    args = parser.parse_args(argv[1:])

    if args.debug == "requests":
        requests.all_requests = []

    if args.open:
        if args.closed:
            state = "all"
        else:
            state = "open"
    else:
        if args.closed:
            state = "closed"
        else:
            state = "open"

    if args.internal:
        intext = "internal"
    elif args.external:
        intext = "external"
    else:
        intext = None

    since = None
    if args.since:
        since = datetime.datetime.now() - datetime.timedelta(days=args.since)

    show_pulls(
        show_comments=args.show_comments,
        state=state,
        since=since,
        org=args.org,
        intext=intext,
    )

    if args.debug == "requests":
        print("{} requests:".format(len(requests.all_requests)))
        for req in requests.all_requests:
            print(req)

if __name__ == "__main__":
    main(sys.argv)
