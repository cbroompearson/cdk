#!/usr/bin/env python3

from aws_cdk import core

from cdk.cdk_stack import CdkStack


app = core.App()

# Params and stage info
stage = app.node.try_get_context('stage')
props = app.node.try_get_context(stage)
service = app.node.try_get_context('serviceName')
app_id = app.node.try_get_context('appId')
cost_centre = app.node.try_get_context('costCentre')
dcl = app.node.try_get_context('dcl')
name = app.node.try_get_context('Name')
region = app.node.try_get_context(stage)['region']

# Build out stack
CdkStack(app, "{0}-{1}".format(service, stage), props=props, env={'region': region, 'account': "829809672214"})

# Tagging
core.Tag.add(app, 't_environment', stage.upper())
core.Tag.add(app, 't_AppID', app_id)
core.Tag.add(app, 't_cost_centre', cost_centre)
core.Tag.add(app, 't_dcl', dcl)
core.Tag.add(app, 'Application', service)
core.Tag.add(app, 'Name', name)


# Synth the CF template
app.synth()
