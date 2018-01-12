#!/usr/bin/env python
# Copyright (c) 2018 Arista Networks, Inc.  All rights reserved.
# Arista Networks, Inc. Confidential and Proprietary.

import argparse
import base64
import json
import os
import requests
import subprocess
import yaml


PACKAGE_SETTINGS_FILE = 'package.yml'


def getEnv(name):
  value = os.environ.get(name)
  assert value, name + " is not set"
  return value


def filesInRevision():
  rev = getEnv("GERRIT_REVISION")
  diff = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", rev])
  return diff.split("\n")


def dirs(files):
  return set(os.path.dirname(f) for f in files)


def getNotifiees(files):
  notifiees = set()
  for d in dirs(files):
    ancestor = d
    settings = None
    while not settings:
      settingsFile = os.path.join(ancestor, PACKAGE_SETTINGS_FILE)
      if not os.path.isfile(settingsFile):
        if ancestor:
          ancestor = os.path.dirname(ancestor)
          continue
        break
      with open(os.path.join(d, PACKAGE_SETTINGS_FILE)) as settingsFile:
        settings = yaml.load(settingsFile.read())
        for channel in settings.get('notifications', {}).get('slack', {}).get('channels', []):
          notifiees.add("#" + channel)
  return notifiees


def notify(failed=False):
  patchset = getEnv("GERRIT_PATCHSET_NUMBER")
  title = "gerrit/%s/%s" % (getEnv("GERRIT_CHANGE_NUMBER"), patchset)
  url = getEnv("GERRIT_CHANGE_URL")
  titleLink = url + "/" + patchset
  message = base64.b64decode(getEnv("GERRIT_CHANGE_COMMIT_MESSAGE")).split("\n")[0]
  message += '\n_by ' + getEnv("GERRIT_CHANGE_OWNER_EMAIL").split("@")[0] + "_"
  payload = {"username": "jenkins",
             "icon_url": "https://a.slack-edge.com/205a/img/services/jenkins-ci_72.png"}
  payload["attachments"] = [{"color": "danger" if failed else "good",
                             "title": title,
                             "title_link": titleLink,
                             "text": message,
                             "mrkdwn_in": ["text"]}]
  files = filesInRevision()
  webHook = getEnv("SLACK_WEBHOOK")
  for channel in getNotifiees(files):
    payload['channel'] = channel
    requests.post(webHook, data=json.dumps(payload))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--result", choices=["SUCCESS", "FAILURE"], required=True)
  args = parser.parse_args()
  notify(failed=(args.result == "FAILURE"))


if __name__ == "__main__":
    main()
