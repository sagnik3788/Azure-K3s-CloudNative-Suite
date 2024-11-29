provider "azurerm" {
  features {}

  subscription_id = "5ee78f37-b02d-4014-86a4-543b4373e03c"
}

# Load configuration variables
variable "location" {
  default = "WestUS2"
}

variable "resource_group_name" {
  default = "my-resource-group"
}

variable "admin_username" {
  default = "adminuser"
}

variable "ssh_key_path" {
  default = "~/.ssh/iam_key.pub"
}

variable "vm_size" {
  default = "Standard_B1s"
}

variable "k3s_version" {
  default = "v1.26.3+k3s1"
}

variable "vm_count" {
  default = 3
}

# Create a resource group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# Create a virtual network
resource "azurerm_virtual_network" "main" {
  name                = "vnet"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]
}

# Create a subnet
resource "azurerm_subnet" "main" {
  name                 = "subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Create public IP addresses and network interfaces for each VM
# resource "azurerm_public_ip" "main" {
#   count               = var.vm_count
#   name                = "public_ip-${count.index}"
#   location            = azurerm_resource_group.main.location
#   resource_group_name = azurerm_resource_group.main.name
#   allocation_method   = "Dynamic"
# }
resource "azurerm_public_ip" "main" {
  count               = 3
  name                = "example-pip-${count.index}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"  # Ensure you are using the Standard SKU
  allocation_method   = "Static"   # Use Static IP allocation

  tags = {
    environment = "production"
  }
}


resource "azurerm_network_interface" "main" {
  count               = var.vm_count
  name                = "nic-${count.index}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "ipconfig-${count.index}"
    subnet_id                     = azurerm_subnet.main.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.main[count.index].id
  }
}

# Create virtual machines for K3s cluster nodes
resource "azurerm_linux_virtual_machine" "main" {
  count               = var.vm_count
  name                = "k3s-vm-${count.index}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  size                = var.vm_size
  admin_username      = var.admin_username
  network_interface_ids = [
    azurerm_network_interface.main[count.index].id
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "19_04-gen2"
    version   = "latest"
  }

  custom_data = base64encode(<<-EOF
    #cloud-config
    runcmd:
      - curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644 --node-taint CriticalAddonsOnly=true:NoExecute --disable-agent
  EOF
  )
}

# Output the public IP addresses of VMs
output "vm_public_ips" {
  value = [for ip in azurerm_public_ip.main : ip.ip_address]
}
