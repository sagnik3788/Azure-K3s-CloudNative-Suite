import pulumi
from pulumi_azure_native import resources, network, compute
from pulumi import Output

# Configurations
config = pulumi.Config()
resource_group_name = config.require("resource_group")
location = config.get("location") or "East US"
vm_size = config.get("vm_size") or "Standard_B2s"
admin_username = config.require("admin_username")
ssh_key = config.require("ssh_key")  # Public key content

# Resource Group
resource_group = resources.ResourceGroup(resource_group_name, location=location)

# Virtual Network and Subnet
vnet = network.VirtualNetwork(
    "k3s-vnet",
    resource_group_name=resource_group.name,
    location=location,
    address_space={"address_prefixes": ["10.0.0.0/16"]},
)

subnet = network.Subnet(
    "k3s-subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
)

# Create public IP addresses and network interfaces for VMs
vm_list = []
nic_list = []
public_ip_list = []

for i in range(3):  # 3 nodes for HA
    # Create public IP for each VM
    public_ip = network.PublicIPAddress(
        f"public-ip-{i}",
        resource_group_name=resource_group.name,
        location=location,
        public_ip_allocation_method="Dynamic",
    )
    public_ip_list.append(public_ip)

    # Create network interface
    nic = compute.NetworkInterface(
        f"nic-{i}",
        resource_group_name=resource_group.name,
        location=location,
        ip_configurations=[
            {
                "name": "ipconfig",
                "subnet": {"id": subnet.id},
                "public_ip_address": {"id": public_ip.id},
            }
        ],
    )
    nic_list.append(nic)

    # Create VM
    vm = compute.VirtualMachine(
        f"k3s-node-{i}",
        resource_group_name=resource_group.name,
        location=location,
        vm_size=vm_size,
        network_profile={
            "network_interfaces": [
                {"id": nic.id}
            ]
        },
        os_profile={
            "computer_name": f"k3s-node-{i}",
            "admin_username": admin_username,
            "linux_configuration": {
                "ssh": {
                    "public_keys": [
                        {
                            "key_data": ssh_key,
                        }
                    ]
                },
                "script": {
                    "script_content": """#!/bin/bash
                    curl -sfL https://get.k3s.io | sh -
                    """
                }
            },
        },
        storage_profile={"image_reference": {"publisher": "Canonical", "offer": "UbuntuServer", "sku": "18.04-LTS"}},
    )
    vm_list.append(vm)

# Outputs
pulumi.export("public_ips", [ip.ip_address for ip in public_ip_list])
