
import argparse
import logging
import re
import time
import uuid

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

MATCHING = re.compile("kfctl.*")

def list_resources(compute, project):
  urlMaps = compute.urlMaps()
  backendServices = compute.backendServices()
  next_page = None
  ums = {}
  while True:
    results = urlMaps.list(project=project, pageToken=next_page).execute()
    if not "items" in results:
      break
    for d in results["items"]:
      name = d.get("name", "")
      ums[name] = {}
      ums[name]["hosts"] = []
      for hr in d.get("hostRules", []):
        ums[name]["hosts"].extend(hr.get("hosts", []))
      # Check host matching for filter.
      endpoint_matched = False
      for host in ums[name]["hosts"]:
        if MATCHING.match(host):
          endpoint_matched = True
          break
      if not endpoint_matched:
        ums.pop(name, None)
        continue

      for pm in d.get("pathMatchers", []):
        ums[name]["backends"] = []
        ums[name]["healthchecks"] = []
        ums[name]["instancegroups"] = []
        for pr in pm.get("pathRules", []):
          service = pr.get("service", "")
          if service:
            backend = service.split("/")[-1]
            ums[name]["backends"].append(backend)
            bs = backendServices.get(project=project, backendService=backend).execute()
            ums[name]["healthchecks"].extend(map(lambda be: be.split("/")[-1],
                                                 bs.get("healthChecks", [])))
            ums[name]["instancegroups"].extend(map(lambda be: {
                "name": be.get("group", "").split("/")[-1],
                "zone": be.get("group", "").split("/")[-3],
            },
                                                   bs.get("backends", [])))
    next_page = results.get("nextPageToken", None)
    if not next_page:
      break
  return ums

def list_target_proxies(project, compute):
  http = compute.targetHttpProxies()
  result = http.list(project=project).execute()
  next_page = None

  maps = {}
  while True:
    for item in result.get("items", []):
      um = item.get("urlMap", "").split("/")[-1]
      maps[um] = item.get("name", "")

    next_page = result.get("nextPageToken", None)
    if not next_page:
      break
    result = http.list(project=project, pageToken=next_page).execute()

  https = compute.targetHttpsProxies()
  result = https.list(project=project).execute()
  next_page = None
  while True:
    for item in result.get("items", []):
      um = item.get("urlMap", "").split("/")[-1]

    next_page = result.get("nextPageToken", None)
    if not next_page:
      break
    result = https.list(project=project, pageToken=next_page).execute()

  return maps

def sync_delete(func):
  req_id = uuid.uuid4()
  while True:
    result = func(req_id)
    if not str(result.get("status", "")) == "DONE":
      status = str(result.get("status", ""))

      logging.info("Sync delete not finished... %s", status)
      time.sleep(10)
    else:
      return result

def delete_resources(project, compute, resources):
  logging.info("Deleting: %s", str(resources))

  urlMaps = compute.urlMaps()
  backendServices = compute.backendServices()
  healthChecks = compute.healthChecks()
  instanceGroups = compute.instanceGroups()

  for um in resources:
    logging.info("Deleting UrlMap: %s", um)
    def delete_url_maps(req_id):
      return urlMaps.delete(project=project, urlMap=um, requestId=req_id).execute()
    result = sync_delete(delete_url_maps)

    for bs in resources.get(um, {}).get("backends", []):
      logging.info("Deleting backend: %s", bs)
      def delete_backend_service(req_id):
        return backendServices.delete(project=project, backendService=bs, requestId=req_id).execute()
      result = sync_delete(delete_backend_service)
      print(result)

    for hc in resources.get(um, {}).get("healthchecks", []):
      logging.info("Deleting health check: %s", hc)
      def delete_health_checks(req_id):
        return healthChecks.delete(project=project, healthCheck=hc, requestId=req_id).execute()
      result = sync_delete(delete_health_checks)
      print(result)

    for ig in resources.get(um, {}).get("instancegroups", []):
      name, zone = (ig.get("name", ""), ig.get("zone", ""))
      logging.info("Deleting instance group: %s/%s", zone, name)
      def delete_instance_group(req_id):
        return instanceGroups.delete(project=project, zone=zone, instanceGroup=name,
                                     requestId=req_id).execute()
      result = sync_delete(delete_instance_group)
      print(result)

def main():
  logging.basicConfig(level=logging.INFO,
                      format=('%(levelname)s|%(asctime)s'
                              '|%(pathname)s|%(lineno)d| %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--project", default="kubeflow-ci", type=str, help=("The project."))

  parser.add_argument(
    "--max_age_hours", default=3, type=int, help=("The age of deployments to gc."))

  parser.add_argument('--dryrun', dest='dryrun', action='store_true')
  parser.add_argument('--no-dryrun', dest='dryrun', action='store_false')
  parser.set_defaults(dryrun=False)

  args = parser.parse_args()
  credentials = GoogleCredentials.get_application_default()
  compute = discovery.build('compute', 'v1', credentials=credentials)
  resources = list_resources(compute, args.project)

  proxies = list_target_proxies(args.project, compute)

  test = {}
  temp = False
  for um in resources:
    if um in proxies:
      logging.info("Url Mapping %s is bound to proxy %s", um, proxies[um])
    else:
      logging.info("Url Mapping %s is not bound with TargetProxy.", um)
      if not temp:
        test[um] = resources[um]
        temp = True
  delete_resources(args.project, compute, test)


if __name__ == '__main__':
  main()
