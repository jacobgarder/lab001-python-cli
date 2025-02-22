"""
Command line tool for changing keys and secret strings in the network.
"""

import click
import os
import yaml
from .utils.restconf import Restconf
from .utils.cli_config import CliConfig
from .utils.utils import debug_msg, check_result

# TODO: The following must be considered as part of all work on this exercise
#       - Provide good help messages to users for all commands and options
#       - All CLI sub-commands need access to the values for inventory, device credentials, debug values, and restconf preference
# TODO: Update all "print" statements in this file to use a Click equivalent to ensure support accross Operating Systems
#       - Additional requirements for certain text output is listed where relevant


# TODO: Configure cli to be the main CLI command accessible as `rotatekey`
#       - Set a good help message for command an all options
# TODO: Support 2 debugging / verbosity options
#       - Ensure these options are available to all other commands in the CLI tool using context
#       - "--debug" : Used to display detailed debug messages to user during operation
#       - "--cli-verbose" : Used to output detailed messages to user during device interactions over CLI
# TODO: Add the "--inventory" option to specify a YAML file wiht device connection information
#       - Also available with shorter "-i" option
#       - Default to the value "inventory.yaml"
# TODO: Add an option "--prefer-restconf" that controls whether the tool will attempt to use RESTCONF for all communications

@click.group()
@click.option('--debug',  is_flag=True, default=False, help="Print debug messages during procesing")
@click.option('--cli-verbose', is_flag=True, help="Stream CLI connection info to screen")
@click.option('--prefer-restconf',  is_flag=True, help="Attempt to use RESTCONF even if not defined in inventory.")
@click.option('--inventory','-i', help="The network inventory file to operate on", default='inventory.yaml')
@click.pass_context
def cli(ctx, inventory, debug, cli_verbose, prefer_restconf):
    """
    Utilities for rotating network secrets and keys.

    Be sure to set the following envrironment variables:

        - NETWORK_USERNAME
        - NETWORK_PASSWORD

    Args:
        ctx (Click.Context):
        inventory (str): Network inventory file
        debug (bool): Debug flag
        cli_verbose (bool): Debug flag
        prefer_restconf (bool): Attempt to use RESTCONF on all devices
    """
    # Check for network credentials set as environment variables
    if "NETWORK_USERNAME" not in os.environ or "NETWORK_PASSWORD" not in os.environ:

        click.secho("ERROR: You must set the NETWORK_USERNAME and NETWORK_PASSWORD environment variables.", fg='red')
        exit(1)

    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    # Set and store the flags for command
    ctx.obj["debug"] = debug
    ctx.obj["cli_verbose"] = cli_verbose
    ctx.obj["prefer_restconf"] = prefer_restconf

    # load the inventory file
    with open(inventory) as f:
        inventory = yaml.safe_load(f)

    # save the inventory file in the context
    ctx.obj["inventory"] = inventory
    ctx.obj["network_username"] = os.getenv("NETWORK_USERNAME")
    ctx.obj["network_password"] = os.getenv("NETWORK_PASSWORD")

    # Setup RESTCONF Objects for each device if supported
    debug_msg(ctx.obj["debug"], f"Prefer RESTCONF status: {prefer_restconf}")
    for device in ctx.obj["inventory"]:
        # Check for RESTCONF support if the device is set to "restconf: True" in inventory
        # or if the "prefer-restconf" flag was set. Otherwise, set the device's restconf = False
        if device.get("restconf", False) or prefer_restconf:
            debug_msg(ctx.obj["debug"], f"Testing device {device['device_name']} for RESTCONF Support")
            device_restconf = Restconf(device["address"], ctx.obj["network_username"], ctx.obj["network_password"])
            device["restconf"] = device_restconf.enabled
        else:
            debug_msg(ctx.obj["debug"], f"Device {device['device_name']} will use CLI connection")
            device["restconf"] = False


@cli.command()
@click.pass_context
def check_inventory(ctx):
    """
    Display status of communication protocols for each device in inventory.
    """
    for device in ctx.obj["inventory"]:
        click.echo(f"Device {device['device_name']} RESTCONF enabled: {device['restconf']}")


# TODO: Make snmp a new command group under the CLI command as `rotatekey snmp`
@cli.group()
def snmp():
    """
    Manipulate the SNMP communities configured on network devices.
    """
    pass


@snmp.command('list')
@click.pass_context
def snmp_list(ctx):
    """
    Lookup and list the SNMP communities created on the devices in inventory.
    """
    click.echo(f"{'Device':15} {'Community':15} {'Rights':5}")
    click.echo("-" * 40)
    for device in ctx.obj["inventory"]:
        debug_msg(ctx.obj["debug"], f"Processing device {device['device_name']}")
        # Use RESTCONF if it is enabled
        if device["restconf"]:
            device_manager = Restconf(
                device["address"],
                ctx.obj["network_username"],
                ctx.obj["network_password"],
            )
        # Attempt to use CLI instead
        else:
            device_manager = CliConfig(
                device["address"],
                ctx.obj["network_username"],
                ctx.obj["network_password"],
                verbose=ctx.obj["cli_verbose"],
            )

        current_snmp = device_manager.lookup_snmp_communities()
        debug_msg(ctx.obj["debug"], f"SNMP Lookup Results: {current_snmp}")
        for snmp in current_snmp:
            print(f"{device['device_name']:15} {snmp['name']:15} {snmp['permission']:5}")

        # Close connection to device
        device_manager.disconnect()


@snmp.command('update')
@click.option('--delete-current','-d', is_flag=True, help="Whether to delete all current SNMP communities")
@click.option('--ro-community', '--ro', help='The new Read-Only community string to create')
@click.option('--rw-community', '--rw', help="The new Read-Write community string to create")
@click.pass_context
def snmp_update(ctx, delete_current: bool, ro_community: str, rw_community: str):
    """
    Update the SNMP community strings configured on devices in the inventory.
    """
    print("Updating the network devices to: ")
    if delete_current:
        click.secho("  - All currently configured SNMP community strings will be removed", fg='red')
    if ro_community:
        click.secho(f"  - A new read-only community string '{ro_community}' will be created", fg='blue')
    if rw_community:
        click.secho(f"  - A new read-write community string '{rw_community}' will be created", fg='green')

    # Loop through each device in inventory
    for device in ctx.obj["inventory"]:
        debug_msg(ctx.obj["debug"], f"Processing device {device['device_name']}")

        # Use RESTCONF if supported
        if device["restconf"]:
            device_manager = Restconf(
                device["address"],
                ctx.obj["network_username"],
                ctx.obj["network_password"],
            )
        # Attempt to use CLI instead
        else:
            device_manager = CliConfig(
                device["address"],
                ctx.obj["network_username"],
                ctx.obj["network_password"],
                verbose=ctx.obj["cli_verbose"],
            )

        # Delete Current Communities
        if delete_current:
            debug_msg(ctx.obj["debug"], "Clearing all currently configured communties")
            result = device_manager.clear_snmp_communities()
            check_result(device["device_name"], "snmp-delete-current", result, ctx.obj["debug"])

        # Read Only Community Create
        if ro_community:
            debug_msg(ctx.obj["debug"], f"Creating new Read-Only Community: {ro_community}")
            result = device_manager.create_snmp_community(ro_community)
            check_result(
                device["device_name"],
                f"snmp-create-ro [{ro_community}]",
                result,
                ctx.obj["debug"],
            )

        # Read Write Community Create
        if rw_community:
            debug_msg(ctx.obj["debug"], f"Creating new Read-Write Community: {rw_community}")
            result = device_manager.create_snmp_community(rw_community, "rw")
            check_result(
                device["device_name"],
                f"snmp-create-rw [{rw_community}]",
                result,
                ctx.obj["debug"],
            )

        # Close connection to device
        device_manager.disconnect()


# TODO: All commands and subcommands to the CLI application
if __name__ == '__main__':
    cli()