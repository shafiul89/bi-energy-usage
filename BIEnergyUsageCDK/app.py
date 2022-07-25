#!/usr/bin/env python3
import aws_cdk as cdk
import os
import bi_energy_usage_cdk.utilities.context_manager as ctxmgr

from bi_energy_usage_cdk.utilities.docker_lifecycle_rules import DockerImageLifecycleRules

from bi_energy_usage_cdk.stacks.bi_energy_usage_app_stack \
    import EnergyUsageAppProperties, EnergyUsageAppStack

from bi_energy_usage_cdk.stacks.bi_energy_usage_pipeline_stack \
    import EnergyUsagePipelineStack

context = ctxmgr.ContextManager()

app = cdk.App()

# personal dev stack (a single standalone environment)

if os.getenv('CODEBUILD_CI', '') == '':
    pers_app_properties = EnergyUsageAppProperties(
        context=context,
        environment=context.environments.pers,
        create_repo=True,
        create_lifecycle_rules=DockerImageLifecycleRules.NON_PROD,
        parameter_definitions=context.systems_manager_parameters,
        parameter_values=context.environments.pers.systems_manager_parameter_values,
        task_definition_env_vars=context.environments.pers.task_definition_env_vars
    )
    pers_app_stack = EnergyUsageAppStack(app, 'pers-app', pers_app_properties)

# dev app stack

dev_app_properties = EnergyUsageAppProperties(
    context=context,
    environment=context.environments.dev,
    create_repo=True,
    create_grant_read_to_account_ids=[context.environments.stg.account_id],
    create_lifecycle_rules=DockerImageLifecycleRules.NON_PROD,
    parameter_definitions=context.systems_manager_parameters,
    parameter_values=context.environments.dev.systems_manager_parameter_values,
    task_definition_env_vars=context.environments.dev.task_definition_env_vars
)
dev_app_stack = EnergyUsageAppStack(app, 'dev-app', dev_app_properties)

# resources in one stack cannot reference another, so the cross environment/account repo link is looser
# i.e. we must generate the name/arn the same here as in the EnergyUsageEcrRepoConstruct class

dev_context = context.environments.dev
dev_repo_name = context.get_resource_base_name(dev_context.environment_name, '',
                                               dev_context.settings.use_default_root_name).lower()
dev_repo_arn = f'arn:aws:ecr:{context.region}:{dev_context.account_id}:repository/{dev_repo_name}'

# test app stack

test_app_properties = EnergyUsageAppProperties(
    context=context,
    environment=context.environments.test,
    create_repo=False,
    existing_repo_arn=dev_repo_arn,
    parameter_definitions=context.systems_manager_parameters,
    parameter_values=context.environments.test.systems_manager_parameter_values,
    task_definition_env_vars=context.environments.test.task_definition_env_vars
)
test_app_stack = EnergyUsageAppStack(app, 'test-app', test_app_properties)

# stg app stack

stg_app_properties = EnergyUsageAppProperties(
    context=context,
    environment=context.environments.stg,
    create_repo=False,
    existing_repo_arn=dev_repo_arn,
    parameter_definitions=context.systems_manager_parameters,
    parameter_values=context.environments.stg.systems_manager_parameter_values,
    task_definition_env_vars=context.environments.stg.task_definition_env_vars
)
stg_app_stack = EnergyUsageAppStack(app, 'stg-app', stg_app_properties)

# prod app stack

prod_app_properties = EnergyUsageAppProperties(
    context=context,
    environment=context.environments.prod,
    create_repo=True,
    create_grant_write_to_account_ids=[context.environments.dev.account_id],
    create_lifecycle_rules=DockerImageLifecycleRules.PROD,
    parameter_definitions=context.systems_manager_parameters,
    parameter_values=context.environments.prod.systems_manager_parameter_values,
    task_definition_env_vars=context.environments.prod.task_definition_env_vars
)
prod_app_stack = EnergyUsageAppStack(app, 'prod-app', prod_app_properties)

# deployment pipeline

pipeline_stack = EnergyUsagePipelineStack(app, 'pipeline', context)

# done - all stacks defined

app.synth()
