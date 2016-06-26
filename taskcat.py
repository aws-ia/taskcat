#!/usr/bin/env python
# authors:avattathil@gmail.com
# upstream_repo: https://avattathil/taskcat.io
# docs: http://taskcat.io
#
# taskcat is short for task (cloudformation automated testing)
# This program takes as input:
# cfn template and json formated parameter input file
# inputs can be passed as cli for single test
# for more diverse scenarios you can use a ymal configuration 
# Planed Features: 
# - Tests in only specific regions
# - Email test results to owner of project

# Example config.yml
# --Begin
ymal = '''
global:
  notification: true
  owner: avattathil@gmail.com
  project: projectx
  regions:
    - us-east-1
    - us-west-1
    - us-west-2
  report_email-to-owner: true
  report_publish-to-s3: true
  report_s3bucket: "s3:/taskcat-reports"
  template_s3bucket: "s3://taskcat-testing"
tests:
  projectx-senario-1:
    parameter_input: projectx-senario-1.json
    regions:
      - us-west-1
      - us-east-1
    template_file: projectx.template
  projetx-main-senario-all-regions:
    parameter_input: projectx-senario-all-regions.json
    template_file: projectx.template
'''
# --End
# Example config.yml

version='v.01'
# --imports --
import os
import sys
import pyfiglet

def main():
	pass

if __name__ == '__main__':
    me = os.path.basename(__file__)
    banner = pyfiglet.Figlet(font='standard')
    print banner.renderText(me.replace('.py', ' '))
    print "version %s" % version
    main()
