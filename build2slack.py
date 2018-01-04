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


GERRIT_CHANGE_COMMIT_MESSAGE_ENV = "GERRIT_CHANGE_COMMIT_MESSAGE"
GERRIT_CHANGE_NUMBER_ENV = "GERRIT_CHANGE_NUMBER"
GERRIT_CHANGE_URL_ENV = "GERRIT_CHANGE_URL"
GERRIT_PATCHSET_NUMBER_ENV = "GERRIT_PATCHSET_NUMBER"
GERRIT_REVISION_ENV = "GERRIT_PATCHSET_REVISION"
PACKAGE_SETTINGS_FILE = 'package.yml'
SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK"


def getEnv(name):
  value = os.environ.get(name)
  assert value, name + " is not set"
  return value


def gerritRevision():
  rev = getEnv(GERRIT_REVISION_ENV)
  diff = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", rev])
  return diff.split("\n")


def dirs(files):
  return set([os.path.dirname(f) for f in files])


def getNotifiees(files):
  notifiees = set()
  for d in dirs(files):
    try:
      with open(os.path.join(d, PACKAGE_SETTINGS_FILE)) as settingsFile:
        settings = yaml.load(settingsFile.read())
        for channel in settings.get('notifications', {}).get('slack', {}).get('channels', []):
          notifiees.add("#" + channel)
    except IOError:
      # No config for this package.
      continue
  return notifiees


def notify(failed=False):
  patchset = getEnv(GERRIT_PATCHSET_NUMBER_ENV)
  title = "gerrit/%s/%s" % (getEnv(GERRIT_CHANGE_NUMBER_ENV), patchset)
  url = getEnv(GERRIT_CHANGE_URL_ENV)
  titleLink = url + "/" + patchset
  message = base64.b64decode(getEnv(GERRIT_CHANGE_COMMIT_MESSAGE_ENV)).split("\n")[0]
  payload = {"username": "jenkins",
             "icon_url": "https://a.slack-edge.com/205a/img/services/jenkins-ci_72.png"}
  payload["attachments"] = [{"color": "danger" if failed else "good",
                             "title": title,
                             "title_link": titleLink,
                             "text": message,
                             "mrkdwn_in": ["text"]}]
  files = gerritRevision()
  webHook = os.environ.get(SLACK_WEBHOOK_ENV)
  assert webHook, SLACK_WEBHOOK_ENV + " is not set"
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