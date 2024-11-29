import pulumi
from pulumi_azure_native import resources, network, compute
from pulumi_kubernetes import Provider
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

# Create Azure VMs
vm_list = []
for i in range(3):  # 3 nodes for HA
    vm = compute.VirtualMachine(
        f"k3s-node-{i}",
        resource_group_name=resource_group.name,
        location=location,
        vm_size=vm_size,
        network_profile={
            "network_interfaces": [
                {
                    "id": pulumi.Output.all(resource_group.name, subnet.id).apply(
                        lambda args: compute.NetworkInterface(
                            f"nic-{i}",
                            resource_group_name=args[0],
                            ip_configurations=[
                                {
                                    "name": "ipconfig",
                                    "subnet": {"id": args[1]},
                                }
                            ],
                        ).id
                    )
                }
            ]
        },
        os_profile={
            "computer_name": f"k3s-node-{i}",
            "admin_username": admin_username,
            "linux_configuration": {
                "ssh": {"public_keys": [{"key_data": ssh_key, "path": "/home/{admin_username}/.ssh/authorized_keys"}]},
            },
        },
        storage_profile={"image_reference": {"publisher": "Canonical", "offer": "UbuntuServer", "sku": "18.04-LTS"}},
    )
    vm_list.append(vm)

# Output public IPs
pulumi.export("node_ips", [vm.public_ip for vm in vm_list])
