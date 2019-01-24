#!/bin/bash
set -ex

# Deployment configs.
SRC_DIR=/src
REPO_OWNER=kubeflow
PROJECT=kubeflow-ci
WORKER_CLUSTER=kubeflow-testing

# Check out fresh copy of KF and deployment workflow.
# TODO(gabrielwen): Need to make a seperate workflow to snapshot repos.
/usr/local/bin/checkout.sh ${SRC_DIR} ${REPO_OWNER} kubeflow
git clone --single-branch --branch cron-ci \
  https://github.com/gabrielwen/testing.git ${SRC_DIR}/${REPO_OWNER}/testing
# /usr/local/bin/checkout.sh ${SRC_DIR} ${REPO_OWNER} testing

# Initiate deployment workflow.
${SRC_DIR}/${REPO_OWNER}/testing/test-infra/auto-deploy/workflows.sh \
  ${SRC_DIR} \
  ${REPO_OWNER} \
  ${PROJECT} \
  ${WORKER_CLUSTER}
