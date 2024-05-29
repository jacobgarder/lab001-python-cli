"""
RESTCONF releated classes and functions for interacting with network devices.
"""

from __future__ import annotations
from typing import Optional
import requests
import urllib3
import xmltodict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Restconf(object):
    """
    A helper class for interacting with IOS XE devices with RESTCONF for common operations.
    """

    def __init__(self, address: str, username: str, password: str):
        """
        Setup a Restconf object for a device.

        Args:
            address (str): address for network device
            username (str): username for network device
            password (str): password for network device

        """
        self.address = address
        self.base_url = f"https://{address}"
        self.username = username
        self.password = password

        self.http_session = requests.Session()
        self.http_session.auth = (username, password)
        self.http_session.headers.update(
            {
                "Content-Type": "application/yang-data+json",
                "Accept": "application/yang-data+json",
            }
        )
        self.http_session.verify = False
        self.validate()

    def disconnect(self) -> None:
        """
        Disconnect from the device.
        """
        pass

    def validate(self) -> bool:
        """
        Check if RESTCONF is supported on the device by testing the .well-known/host-meta path.

        Returns:
            enabled (bool): Whether RESTCONF is enabled on device
        """
        try:
            response = self.http_session.get(f"{self.base_url}/.well-known/host-meta")
            if response.status_code == 200:
                body = xmltodict.parse(response.text)
                restconf_resource = body["XRD"]["Link"]["@href"]
                self.base_url = f"{self.base_url}{restconf_resource}"
                self.enabled = True
            else:
                self.enabled = False
        except requests.exceptions.ConnectionError:
            self.enabled = False

        return self.enabled

    def lookup_snmp_communities(self) -> list[dict[str, str]]:
        """
        Lookup the currently configured SNMP communities.

        Returns:
            snmp_communtites (list): List of SNMP communities and permissions
        """
        target_resource = (
            "/data/Cisco-IOS-XE-native:native/snmp-server/community-config"
        )
        response = self.http_session.get(f"{self.base_url}{target_resource}")

        if response.status_code == 200:
            body = response.json()
            snmp_communities = body["Cisco-IOS-XE-snmp:community-config"]
            return snmp_communities
        elif response.status_code == 204:
            return []
        else:
            return None

    def create_snmp_community(
        self, community_name: str, permission: Optional[str] = "ro"
    ) -> tuple[bool, str]:
        """
        Create a new SNMP community string entry using RESTCONF.

        Args:
            community_name (str): The name of the community string to create
            permission (str): The permission level (ro or rw) for the community

        Returns:
            action_result (tuple): Details on result (success_bool, reason)
        """
        target_resource = "/data/Cisco-IOS-XE-native:native/snmp-server/"

        body = {
            "Cisco-IOS-XE-snmp:community-config": [
                {"name": community_name, "permission": permission}
            ]
        }

        response = self.http_session.post(
            f"{self.base_url}{target_resource}", json=body
        )

        if response.status_code == 201:
            return (True, None)
        else:
            return (False, response.reason)

    def delete_snmp_community(self, community_name: str) -> tuple[bool, str]:
        """
        Delete the provided community name using RESTCONF.

        Args:
            community_name (str): The name of the community to delete.

        Returns:
            action_result (tuple): Details on result (success_bool, reason)
        """
        target_resource = f"/data/Cisco-IOS-XE-native:native/snmp-server/community-config={community_name}"
        response = self.http_session.delete(f"{self.base_url}{target_resource}")

        if response.status_code == 204:
            return (True, None)
        else:
            return (False, response.reason)

    def clear_snmp_communities(self) -> tuple[bool, str]:
        """
        Delete all community strings currently configured on a devices.

        Returns:
            action_result (tuple): Details on result (success_bool, reason)
        """
        # Lookup all communities
        current_communities = self.lookup_snmp_communities()

        return_status = True
        return_reasons = []

        for community in current_communities:
            success, reason = self.delete_snmp_community(community["name"])
            if not success:
                return_status = False
                return_reasons = return_reasons.append(
                    f"Community {community}, {reason}"
                )

        return (return_status, ", ".join(return_reasons))
