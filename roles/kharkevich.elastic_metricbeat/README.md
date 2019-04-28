# Ansible Role: Metricbeat for Elastic [![Build Status](https://travis-ci.org/kharkevich/ansible-elastic-metricbeat.svg?branch=master)](https://travis-ci.org/kharkevich/ansible-elastic-metricbeat)

An Ansible Role that installs [Metricbeat](https://www.elastic.co/products/beats/metricbeat) on RedHat or Debian family distributives.

## Requirements

None.

## Role Variables

All available see in `defaults/main.yml`.

## Dependencies

None.

## Example Playbook

    - hosts: all
      roles:
        - kharkevich.metricbeat
      vars:
        kibana_host: "http://kibana.example.com:5601"
        elasticsearch_hosts:
      	  - elastic0.example.com:9200
      	  - elastic1.example.com:9200

## License

Apache

## Author Information

This role was created by [Aliaksandr Kharkevich](https://github.com/kharkevich)