#!/bin/bash
set -ex

# Deployment configs.
SRC_DIR=$1
REPO_OWNER=$2
PROJECT=$3
WORKER_CLUSTER=$4

# Check out fresh copy of KF and deployment workflow.
# TODO(gabrielwen): Need to make a seperate workflow to snapshot repos.
/usr/local/bin/checkout.sh ${SRC_DIR} ${REPO_OWNER} kubeflow
git clone --single-branch --branch version-snapshot \
  https://github.com/gabrielwen/testing.git ${SRC_DIR}/${REPO_OWNER}/testing
# /usr/local/bin/checkout.sh ${SRC_DIR} ${REPO_OWNER} testing

# Initiate deployment workflow.
${SRC_DIR}/${REPO_OWNER}/testing/test-infra/auto-deploy/workflows.sh \
  ${SRC_DIR} \
  ${REPO_OWNER} \
  ${PROJECT} \
  ${WORKER_CLUSTER}
