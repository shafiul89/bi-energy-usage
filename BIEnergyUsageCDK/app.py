#!/usr/bin/env python3
import aws_cdk as cdk
import bi_energy_usage_cdk.utilities.context_manager
from bi_energy_usage_cdk.bi_energy_usage_cdk_stack import BiEnergyUsageCdkStack


app = cdk.App()
context_mgr = bi_energy_usage_cdk.utilities.context_manager.ContextManager()
context_mgr.print_context()
BiEnergyUsageCdkStack(app, "BiEnergyUsageCdkStack")
app.synth()
