#!/usr/bin/python
# Copyright (C) 2016  Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the COPYING file.

"""Parses the build log and posts some in-line comments to Gerrit."""

import json
import os
import re
import subprocess
import sys
import time
import urllib2

debug = False

jenkinsHome = os.environ["JENKINS_HOME"]
jobName = os.environ["JOB_NAME"]
jobUrl = os.environ["JOB_URL"]
buildNum = os.environ["BUILD_NUMBER"]
log = "%s/jobs/%s/builds/%s/log" % (jenkinsHome, jobName, buildNum)

try:
  logFile = open(log)
except IOError:
  logFile = urllib2.urlopen("%s/%s/consoleText" % (jobUrl, buildNum))

regexp = re.compile(r"(?:deadcode: )?(?:./)?([-a-zA-Z_/]*\.go):([0-9]+)(?::[0-9]+)?: (.*)")
# 3-level deep map.
# 1st level: path -> comments for this path
# 2nd level: line num -> comments for this line
# 3rd level: comment -> True (to remove duplicate comments)
comments = {}
for line in logFile:
  m = regexp.match(line)
  if not m:
    #print "no match %r" % line
    continue
  path, linenum, msg = m.groups()
  comments.setdefault(path, {}).setdefault(linenum, {}).setdefault(msg, True)

if not comments:
  sys.exit(0)

for path, msgs in comments.iteritems():
  comments[path] = [{"line": line, "message": "\n".join(sorted(msg))}
                    for line, msg in msgs.iteritems()]

url = ("http://gerrit/a/changes/%s/revisions/%s/review"
       % (os.getenv("GERRIT_CHANGE_NUMBER"), os.getenv("GERRIT_PATCHSET_NUMBER")))

review = {
  "message": ("See the full build log at %s" % os.path.join(jobUrl, buildNum, "console")),
  "labels": {"Verified": -1},
  "comments": comments,
}

if debug:
  print json.dumps(review, indent=2)
  sys.exit(0)

curl = subprocess.Popen("curl --digest --netrc -X POST -d @-"
  " -H 'Content-Type: application/json; charset=UTF-8' " + url,
  shell=True, stdin=subprocess.PIPE)
json.dump(review, curl.stdin, indent=2)
curl.stdin.close()

for attempt in xrange(50):
  rv = curl.poll()
  if rv is not None:
    break
  time.sleep(0.1)
else:
  curl.terminate()
  rv = curl.poll()
  if rv is None:
    curl.kill()

sys.exit(curl.wait())
