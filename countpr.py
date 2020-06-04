import csv
import itertools
import sys
import time
from pprint import pprint

import requests

def count_prs(q):
    while True:
        resp = requests.get(
            "https://api.github.com/search/issues",
            params={ "q": " ".join(q) },
        )
        if resp.status_code == 403:
            reset = int(resp.headers.get('X-RateLimit-Reset', '0'))
            if reset:
                wait = reset - time.time()
                if wait > 0:
                    time.sleep(wait)
                continue
        elif resp.status_code != 200:
            print("** {}: {}".format(resp.status_code, resp.url))
            return 0
        return resp.json()["total_count"]

def quarters(ystart, yend):
    for year in range(ystart, yend+1):
        yield "CY{}Q1".format(year % 100), "{0}-01-01..{0}-03-31".format(year)
        yield "CY{}Q2".format(year % 100), "{0}-04-01..{0}-06-30".format(year)
        yield "CY{}Q3".format(year % 100), "{0}-07-01..{0}-09-30".format(year)
        yield "CY{}Q4".format(year % 100), "{0}-10-01..{0}-12-31".format(year)

def doit():
    csvw = csv.writer(sys.stdout)
    kinds = ["total", "external", "bd", "open"]
    states = ["total", "open", "closed", "merged", "unmerged", "rejected"]
    cols = list(itertools.product(kinds, states))
    csvw.writerow(["when"] + [kind for kind, _ in cols])
    csvw.writerow(["when"] + [state for _, state in cols])

    q = ["org:edx is:pr"]
    for qlabel, qrange in quarters(2018, 2020):
        nums = []
        for kind, state in cols:
            if kind == "open":
                # subtract
                w = len(states)
                nums.append(nums[-2 * w] - nums[-w])
            else:
                if state == "rejected":
                    nums.append(nums[-3] - nums[-2])
                else:
                    qkind = ['label:"open-source-contribution"'] if kind != "total" else []
                    qcreated = ["created:" + qrange]
                    qstate = ["is:" + state] if state != "total" else []
                    qbd = ['"BD"'] if kind == "bd" else []
                    count = count_prs(q + qkind + qcreated + qstate + qbd)
                    nums.append(count)
        csvw.writerow([qlabel] + nums)

doit()
