#!/bin/sh
vagrant up ndn0 && vagrant ssh ndn0 -c 'sh /vagrant/demo/demo.sh'
