# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

$SCRIPT = <<MSG
nfd-start
MSG

GUI= false
RAM= 2048
NMACHINES= 8

DOMAIN = ".ndn.endlessm.com"
NETWORK = "10.42.42."
NETMASK = "255.255.255.0"

BOX= 'xaiki/nfd'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.provision "shell", inline: $SCRIPT

  (0..(NMACHINES - 1)).each do | (id) |
    sid = id.to_s
    name = "ndn" + sid

    config.vm.define name do |machine|
      machine.vm.box = BOX

      machine.vm.provider "virtualbox" do |vb|
        # vb.gui = true
        vb.cpus = 1
        vb.memory = RAM
      end

      ipaddr = NETWORK + "1" + sid
      machine.vm.hostname = name + DOMAIN
      machine.vm.network "private_network", ip: ipaddr, netmask: NETMASK
      machine.vm.network "forwarded_port", guest: 6363, host: "6363" + sid, protocol: "tcp"
      machine.vm.network "forwarded_port", guest: 6363, host: "6363" + sid, protocol: "udp"

      (0..(NMACHINES - 1)).each do | (m) |
        machine.vm.provision "shell", inline: "nfdc register /endlessm.com tcp://" + NETWORK + "1" + m.to_s
      end
    end
  end
end
