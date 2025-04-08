#!/usr/bin/env python3
import os
import sys
import json
import requests
import argparse

BASE_URL = "https://api.gremlin.com/v1"

ALLOWED_TYPES = {
    "JIRA", "DATADOG", "DATADOG_EU", "DATADOG_US3", "DATADOG_US5",
    "DATADOG_US1_FED", "PAGERDUTY", "NEWRELIC", "GRAFANA", "DYNATRACE",
    "APPDYNAMICS", "CUSTOM", "K6", "LOAD_GENERATOR_CUSTOM", "AWS"
}

def get_external_integrations(team_id, headers):
    url = f"{BASE_URL}/external-integrations/status-check?teamId={team_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        # If the response is already a list, return it; otherwise assume it's an object with key "integrations"
        if isinstance(data, list):
            return data
        else:
            return data.get("integrations", [])
    else:
        print(f"Error fetching external integrations for team {team_id}: {resp.status_code} {resp.text}")
        return []

def delete_existing_health_checks(team_id, headers):
    print(f"\nDeleting existing health checks from destination team {team_id}...")
    url = f"{BASE_URL}/status-checks?teamId={team_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Error fetching health checks: {resp.text}")
        return
    checks = resp.json()
    if not checks:
        print("No existing health checks found in destination team.")
        return
    for check in checks:
        identifier = check.get("identifier")
        name = check.get("name", "Unnamed")
        if not identifier:
            continue
        del_url = f"{BASE_URL}/status-checks/{identifier}?teamId={team_id}"
        del_resp = requests.delete(del_url, headers=headers)
        if del_resp.status_code in (200, 204):
            print(f"Deleted health check: {name}")
        else:
            print(f"Failed to delete health check '{name}': {del_resp.status_code} {del_resp.text}")

def delete_existing_scenarios(team_id, headers):
    print(f"\nDeleting existing scenarios from destination team {team_id}...")
    url = f"{BASE_URL}/scenarios?teamId={team_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Error fetching scenarios: {resp.text}")
        return
    scenarios = resp.json()
    if not scenarios:
        print("No scenarios found in destination team.")
        return
    for scenario in scenarios:
        scenario_id = scenario.get("guid") or scenario.get("identifier")
        name = scenario.get("name", "Unnamed")
        if not scenario_id:
            continue
        del_url = f"{BASE_URL}/scenarios/{scenario_id}?teamId={team_id}"
        del_resp = requests.delete(del_url, headers=headers)
        if del_resp.status_code in (200, 204):
            print(f"Deleted scenario: {name}")
        else:
            print(f"Failed to delete scenario '{name}': {del_resp.status_code} {del_resp.text}")

def copy_external_integrations(source_team_id, dest_team_id, source_headers, dest_headers):
    print(f"\n--- Copying External Integrations from source team {source_team_id} ---")
    src_integrations = get_external_integrations(source_team_id, source_headers)
    print(f"Found {len(src_integrations)} external integrations in source team {source_team_id}.")
    dst_integrations = get_external_integrations(dest_team_id, dest_headers)
    dst_names = {integ.get("name") for integ in dst_integrations if integ}
    
    for integ in src_integrations:
        if integ is None:
            continue
        name = integ.get("name")
        if name in dst_names:
            print(f"Destination already has integration '{name}'.")
        else:
            # Build query parameters.
            qparams = {"teamId": dest_team_id}
            source_type = integ.get("type", "CUSTOM")
            if source_type:
                source_type = source_type.upper()
            else:
                source_type = "CUSTOM"
            if source_type == "CUSTOM":
                qparams["observabilityToolType"] = "CUSTOM"
            else:
                qparams["type"] = source_type
            if integ.get("domain") is not None:
                qparams["domain"] = integ.get("domain")
            # Build the request body.
            body = {
                "name": name,
                "url": integ.get("url"),
                "headers": integ.get("headers", {}),
                "integrationSpecificValues": integ.get("integrationSpecificValues", {}),
                "lastAuthenticationStatus": integ.get("lastAuthenticationStatus", "AUTHENTICATED"),
                "privateNetwork": integ.get("privateNetwork", False)
            }
            post_url = f"{BASE_URL}/external-integrations/status-check"
            post_resp = requests.post(post_url, headers=dest_headers, params=qparams, json=body)
            if post_resp.status_code in (200, 201):
                print(f"Created integration '{name}' in destination team.")
            else:
                print(f"Failed to create integration '{name}': {post_resp.status_code} {post_resp.text}")
    dst_integrations = get_external_integrations(dest_team_id, dest_headers)
    return dst_integrations

def copy_health_checks(source_team_id, target_team_id, source_headers, dest_headers, dest_integrations):
    print(f"\nFetching health checks from source team {source_team_id}...")
    url = f"{BASE_URL}/status-checks?teamId={source_team_id}"
    resp = requests.get(url, headers=source_headers)
    if resp.status_code != 200:
        print(f"Error fetching source health checks: {resp.text}")
        return {}
    checks = resp.json()
    if not checks:
        print("No health checks found in source team.")
        return {}
    
    id_mapping = {}
    for check in checks:
        src_id = check.get("identifier")
        new_check = check.copy()
        # If endpointConfiguration is empty, try using rawEndpointConfiguration headers.
        raw_ep = new_check.get("rawEndpointConfiguration", {})
        ep = new_check.get("endpointConfiguration", {})
        if raw_ep and (not ep.get("headers") or not ep["headers"]):
            ep["headers"] = raw_ep.get("headers", {})
            new_check["endpointConfiguration"] = ep
        for field in ["teamId", "identifier", "createdBy", "createdAt", "updatedBy", "updatedAt", "thirdPartyPresets", "rawEndpointConfiguration"]:
            new_check.pop(field, None)
        # Process external integration.
        if "teamExternalIntegration" in new_check:
            src_integ = new_check["teamExternalIntegration"]
            src_name = src_integ.get("name")
            matched = None
            if dest_integrations and src_name:
                for d_integ in dest_integrations:
                    if d_integ.get("name") == src_name:
                        if d_integ.get("type", "").upper() == "CUSTOM":
                            matched = {
                                "observabilityToolType": "CUSTOM",
                                "domain": d_integ.get("domain"),
                                "name": d_integ.get("name")
                            }
                        else:
                            matched = {
                                "type": d_integ.get("type"),
                                "domain": d_integ.get("domain"),
                                "name": d_integ.get("name")
                            }
                        break
            if matched:
                new_check["teamExternalIntegration"] = matched
            else:
                new_check.pop("teamExternalIntegration", None)
        new_check["teamId"] = target_team_id

        post_url = f"{BASE_URL}/status-checks?teamId={target_team_id}"
        post_resp = requests.post(post_url, headers=dest_headers, json=new_check)
        if post_resp.status_code in (200, 201):
            try:
                created = post_resp.json()
                dest_id = created.get("identifier")
            except Exception:
                dest_id = post_resp.text.strip()
            if dest_id:
                id_mapping[src_id] = dest_id
                put_url = f"{BASE_URL}/status-checks/{dest_id}?teamId={target_team_id}"
                put_resp = requests.put(put_url, headers=dest_headers, json=new_check)
                if put_resp.status_code in (200, 201):
                    print(f"Copied and updated health check: {new_check.get('name', 'Unnamed')}")
                else:
                    print(f"Copied health check but failed to update {new_check.get('name', 'Unnamed')}: {put_resp.status_code} {put_resp.text}")
            else:
                print(f"Copied health check: {new_check.get('name', 'Unnamed')} (identifier not returned)")
        else:
            print(f"Failed to copy health check {new_check.get('name', 'Unnamed')}: {post_resp.status_code} {post_resp.text}")
    return id_mapping

def recursive_update_status_check(obj, mapping):
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key == "statusCheckId":
                val = obj[key]
                if isinstance(val, list):
                    new_list = []
                    for item in val:
                        if item in mapping:
                            new_list.append(mapping[item])
                        else:
                            print(f"Warning: health check id '{item}' not found in mapping; removing it from scenario.")
                    if new_list:
                        obj[key] = new_list
                    else:
                        obj.pop(key)
                else:
                    if val in mapping:
                        obj[key] = mapping[val]
                    else:
                        print(f"Warning: health check id '{val}' not found in mapping; removing it from scenario.")
                        obj.pop(key)
            else:
                recursive_update_status_check(obj[key], mapping)
    elif isinstance(obj, list):
        for item in obj:
            recursive_update_status_check(item, mapping)
    return obj

def copy_scenarios(source_team_id, target_team_id, source_headers, dest_headers, hc_mapping):
    print(f"\nFetching scenarios from source team {source_team_id}...")
    url = f"{BASE_URL}/scenarios?teamId={source_team_id}"
    resp = requests.get(url, headers=source_headers)
    if resp.status_code != 200:
        print(f"Error fetching scenarios for team {source_team_id}: {resp.text}")
        return
    scenarios = resp.json()
    if not scenarios:
        print("No scenarios found in source team.")
        return

    for scenario in scenarios:
        new_scenario = scenario.copy()
        # Remove system fields and shared linkage fields so the scenario is treated as a standalone, customized scenario.
        for field in ["teamId", "identifier", "createdBy", "createdAt", "updatedBy", "updatedAt",
                      "sharedScenario", "sharedScenarioGuid", "baseScenarioId",
                      "created_from_type", "created_from_id", "org_id"]:
            new_scenario.pop(field, None)
        new_scenario = recursive_update_status_check(new_scenario, hc_mapping)
        new_scenario["teamId"] = target_team_id

        post_url = f"{BASE_URL}/scenarios?teamId={target_team_id}"
        post_resp = requests.post(post_url, headers=dest_headers, json=new_scenario)
        if post_resp.status_code in (200, 201):
            print(f"Copied scenario: {new_scenario.get('name', 'Unnamed')}")
        else:
            print(f"Failed to copy scenario {new_scenario.get('name', 'Unnamed')}: {post_resp.status_code} {post_resp.text}")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Gremlin Health Checks, Integrations, and Scenarios Replicator"
    )
    parser.add_argument("--source-api-key", help="Source API key (or set GREMLIN_SOURCE_API_KEY env variable)")
    parser.add_argument("--dest-api-key", help="Destination API key (or set GREMLIN_DEST_API_KEY env variable)")
    parser.add_argument("--source-team-ids", nargs="+", required=True, help="One or more source team IDs (space-separated)")
    parser.add_argument("--target-team-id", required=True, help="Destination team ID")
    parser.add_argument("--delete-health-checks", action="store_true", help="Delete existing health checks in destination team")
    parser.add_argument("--delete-scenarios", action="store_true", help="Delete existing scenarios in destination team")
    return parser.parse_args()

def main():
    # If no command-line args are provided, print help and exit.
    if len(sys.argv) == 1:
        print("No arguments provided.\n")
        parser = argparse.ArgumentParser(
            description="Gremlin Health Checks, Integrations, and Scenarios Replicator"
        )
        parser.print_help()
        sys.exit(1)
    
    args = parse_args()
    
    # Use provided API keys or fallback to environment variables.
    source_api_key = args.source_api_key or os.environ.get("GREMLIN_SOURCE_API_KEY")
    if not source_api_key:
        print("Source API key is required.")
        sys.exit(1)
    dest_api_key = args.dest_api_key or os.environ.get("GREMLIN_DEST_API_KEY")
    if not dest_api_key:
        print("Destination API key is required.")
        sys.exit(1)
    
    source_headers = {"Authorization": f"Key {source_api_key}", "Content-Type": "application/json"}
    dest_headers = {"Authorization": f"Key {dest_api_key}", "Content-Type": "application/json"}
    
    source_team_ids = args.source_team_ids
    target_team_id = args.target_team_id
    
    # Optionally delete existing health checks and scenarios.
    if args.delete_health_checks:
        delete_existing_health_checks(target_team_id, dest_headers)
    if args.delete_scenarios:
        delete_existing_scenarios(target_team_id, dest_headers)
    
    overall_hc_mapping = {}
    # Process each source team.
    for src_team in source_team_ids:
        print(f"\n=== Processing source team {src_team} ===")
        dest_integrations = copy_external_integrations(src_team, target_team_id, source_headers, dest_headers)
        if dest_integrations:
            print(f"Destination team now has {len(dest_integrations)} external integrations for status checks.")
        else:
            print("No external integrations present in destination team after attempted copy.")
    
        hc_mapping = copy_health_checks(src_team, target_team_id, source_headers, dest_headers, dest_integrations)
        overall_hc_mapping.update(hc_mapping)
        copy_scenarios(src_team, target_team_id, source_headers, dest_headers, overall_hc_mapping)
    
    print("\nFinished replicating health checks, integrations, and scenarios.")

if __name__ == "__main__":
    main()

