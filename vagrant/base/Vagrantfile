# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

DOMAIN = ".ndn.endlessm.com"

$SCRIPT = <<SCRIPT
LANG=C nfdc add-nexthop -c 20 /endlessm/ udp4://172.17.0.255
SCRIPT

DOCKER_NAME = 'eos-ndn-dev'
NMACHINES = 32

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  (0..(NMACHINES - 1)).each do | (id) |
    sid = id.to_s
    name = "ndn" + sid

    config.vm.define name do | machine |
      machine.vm.provider "docker" do |d|
        d.image = DOCKER_NAME
        d.has_ssh = true
        d.expose = [6363]
        d.vagrant_machine = "ndn"
      end

      machine.vm.hostname = name + DOMAIN
    end
  end
  config.vm.provision "shell", inline: $SCRIPT
end
