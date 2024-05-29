"""
CLI Configuration releated classes and functions for interacting with network devices.
"""

from __future__ import annotations
from typing import Optional
from pyats.topology import Testbed, Device
from genie.conf import Genie

# import unicon
# import logging
# uut.log.setLevel(logging.WARNING)


class CliConfig(object):
    """
    A helper class for interacting with IOS XE devices with pyATS for common operations.
    """

    def __init__(
        self,
        address: str,
        username: str,
        password: str,
        verbose: Optional[bool] = False,
    ):
        """
        Setup a CliConfig object for a device.

        Args:
            address (str): address for network device
            username (str): username for network device
            password (str): password for network device
            verbose (bool): whether to log output from device to std_out

        """
        self.address = address
        self.username = username
        self.password = password
        self.verbose = verbose

        # Create a pyATS testbed object for the device
        self.testbed = Testbed(
            name=f"Testbed: {address}",
            credentials={
                "default": {
                    "username": username,
                    "password": password,
                }
            },
        )
        device = Device(
            name=address,
            # NOTE: Setting a Default OS to silence warning. learn_os is used to ensure correct OS leveraged
            os="nxos",
            connections={
                # TODO: Try to remove the message "device's os is not provided, unicon may not use correct plugins"
                # "defaults": {
                #     "class": unicon.Unicon,
                #     "log": logging.WARNING,
                # },
                "cli": {
                    "protocol": "ssh",
                    "ip": address,
                    "settings": {
                        "GRACEFUL_DISCONNECT_WAIT_SEC": 0,
                        "POST_DISCONNECT_WAIT_SEC": 0,
                    },
                },
            },
        )
        # TODO: Try to remove the message "device's os is not provided, unicon may not use correct plugins"
        # device.connections.log.setLevel(logging.WARNING)
        device.testbed = self.testbed

        # Attempt to connect to device and verify access
        self.validate()

    def disconnect(self) -> None:
        """
        Disconnect from the device.
        """
        self.testbed.disconnect()

    def validate(self) -> bool:
        """
        Check if CliConfig is supported on the device by testing.

        Returns:
            enabled (bool): Whether CliConfig is enabled on device
        """
        try:
            # Connect to the device, learn hostname and OS
            self.testbed.connect(
                learn_hostname=True,
                learn_os=True,
                log_stdout=self.verbose,
                init_exec_commands=[],
                init_config_commands=[],
            )

            # With the OS learned, enable Genie features on testbed
            self.testbed = Genie.init(self.testbed)
            self.pyats = self.testbed.devices[self.address]

            self.enabled = True
        except Exception:
            self.enabled = False

        return self.enabled

    def lookup_snmp_communities(self) -> list[dict[str, str]]:
        """
        Lookup the currently configured SNMP communities.

        Returns:
            snmp_communities (list): List of SNMP communities and permissions
        """
        # Note 1: pyATS lacks a parser for snmp community
        # Note 2: No show command on IOS displays the permissions on a community
        # Note 3: Will use the well known structure of `snmp-server community STRING PERMISSION`

        snmp_communities = []

        # Lookup SNMP community string configuration
        snmp_configuration = self.pyats.execute("show run | inc snmp-server community").splitlines()
        for community in snmp_configuration:
            community = community.split()
            snmp_communities.append({"name": community[2], "permission": community[3]})

        return snmp_communities

    def create_snmp_community(self, community_name: str, permission: Optional[str] = "ro") -> tuple[bool, str]:
        """
        Create a new SNMP community string entry using pyATS.

        Args:
            community_name (str): The name of the community string to create
            permission (str): The permission level (ro or rw) for the community

        Returns:
            action_result (tuple): Details on result (success_bool, reason)
        """
        target_config = f"snmp-server community {community_name} {permission}"

        try:
            self.pyats.configure(target_config)
            return (True, None)
        except Exception as e:
            return (False, e)

    def delete_snmp_community(self, community_name: str) -> tuple[bool, str]:
        """
        Delete the provided community name using pyATS.

        Args:
            community_name (str): The name of the community to delete.

        Returns:
            action_result (tuple): Details on result (success_bool, reason)
        """
        target_config = f"no snmp-server community {community_name}"

        try:
            self.pyats.configure(target_config)
            return (True, None)
        except Exception as e:
            return (False, e)

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
                return_reasons = return_reasons.append(f"Community {community}, {reason}")

        return (return_status, ", ".join(return_reasons))
