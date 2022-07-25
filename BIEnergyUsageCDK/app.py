#!/usr/bin/env python3
import aws_cdk as cdk
import bi_energy_usage_cdk.utilities.context_manager as ctxmgr

from bi_energy_usage_cdk.utilities.docker_lifecycle_rules import DockerImageLifecycleRules

from bi_energy_usage_cdk.stacks.bi_energy_usage_app_stack \
    import EnergyUsageAppProperties, EnergyUsageAppStack

from bi_energy_usage_cdk.stacks.bi_energy_usage_pipeline_stack \
    import EnergyUsagePipelineStack

context = ctxmgr.ContextManager()

app = cdk.App()

# dev app stack

dev_app_properties = EnergyUsageAppProperties(
    context=context,
    environment=context.environments.dev,
    create_repo=True,
    create_grant_read_to_account_ids=[context.environments.stg.account_id],
    create_lifecycle_rules=DockerImageLifecycleRules.NON_PROD
)
dev_app_stack = EnergyUsageAppStack(app, 'dev-app', dev_app_properties)

# deployment pipeline

pipeline_stack = EnergyUsagePipelineStack(app, 'pipeline', context)

# done - all stacks defined

app.synth()