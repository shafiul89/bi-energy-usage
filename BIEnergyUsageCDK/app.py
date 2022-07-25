#!/usr/bin/env python3
import aws_cdk as cdk
import bi_energy_usage_cdk.utilities.context_manager as ctxmgr

from bi_energy_usage_cdk.stacks.bi_energy_usage_pipeline_stack \
    import EnergyUsagePipelineStack

context = ctxmgr.ContextManager()

app = cdk.App()

# deployment pipeline

pipeline_stack = EnergyUsagePipelineStack(app, 'pipeline', context)

# done - all stacks defined

app.synth()