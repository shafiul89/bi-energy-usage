import bi_energy_usage_cdk.utilities.context_manager as ctxmgr
from aws_cdk import (
    Environment,
    Stack,
    StackProps,
    Tags
)
from constructs import Construct
from bi_energy_usage_cdk.utilities.docker_lifecycle_rules import DockerImageLifecycleRules
from bi_energy_usage_cdk.constructs.bi_energy_usage_repo \
    import EnergyUsageEcrRepoProperties, EnergyUsageEcrRepoConstruct
from bi_energy_usage_cdk.constructs.bi_energy_usage_storage \
    import EnergyUsageStorageProperties, EnergyUsageStorageConstruct
from bi_energy_usage_cdk.constructs.bi_energy_usage_snowflake_role \
    import EnergyUsageSnowflakeRoleProperties, EnergyUsageSnowflakeRoleConstruct
from bi_energy_usage_cdk.constructs.bi_energy_usage_parameters \
    import EnergyUsageParametersProperties, EnergyUsageParametersConstruct
from bi_energy_usage_cdk.constructs.bi_energy_usage_task \
    import EnergyUsageTaskProperties, EnergyUsageTaskConstruct


class EnergyUsageAppProperties(StackProps):
    """
    Configuration values for creating an instance of the EnergyUsageAppStack class.
    """

    def __init__(self,
                 context: ctxmgr.ContextManager,
                 environment: ctxmgr.EnvironmentContext,
                 create_repo: bool,
                 create_grant_read_to_account_ids: list[str] = None,
                 create_grant_write_to_account_ids: list[str] = None,
                 create_lifecycle_rules: DockerImageLifecycleRules = DockerImageLifecycleRules.DEFAULT,
                 existing_repo_arn: str = '',
                 parameter_definitions: dict[str, str] = None,  # once AWS CodeBuild supports Python 3.10, add " | None"
                 parameter_values: dict[str, str] = None,  # once AWS CodeBuild supports Python 3.10, add " | None"
                 task_definition_env_vars: dict[str, str] = None):
        """
        Create configuration values for creating an instance of the EnergyUsageAppStack class.

        Parameters
        ----------
        context : ctxmgr.ContextManager
            The context from the cdk.json file.
        environment : ctxmgr.EnvironmentContext
            The context from the cdk.json file for the target environment.
        create_repo : bool
            True to create an ECR repo, False to link to an existing ECR repo.
        create_grant_read_to_account_ids : list[str]
            A list of AWS account IDs to be granted read access to the ECR repository that will be created.
        create_grant_write_to_account_ids : list[str]
            A list of AWS account IDs to be granted write access to the ECR repository that will be created.
        create_lifecycle_rules : DockerImageLifecycleRules
            A set of docker image lifecycle rules to be applied to the ECR repository that will be created.
        existing_repo_arn :
            The AWS ARN of the existing ECR repository that will be linked to.
        parameter_definitions : dict[str, str]
            A dictionary containing parameter names and parameter descriptions which will become Systems Manager
            Parameter Store parameters.
        parameter_values : dict[str, str]
            A dictionary containing parameter names and parameter values, which sets the values of the Systems
            Manager Parameter Store parameters.
        task_definition_env_vars : dict[str, str]
            A dictionary of environment variable names and values to be created in the docker container when the
            ECS task runs.
        """
        stack_name = context.get_resource_base_name(environment.environment_name.title(), 'App',
                                                    environment.settings.use_default_root_name)
        super().__init__(stack_name=stack_name)

        base_name = context.get_resource_base_name(environment.environment_name, '',
                                                   environment.settings.use_default_root_name)
        self.base_name = base_name.lower()
        self.context = context
        self.environment = environment
        self.create_repo = create_repo
        self.create_grant_read_to_account_ids = create_grant_read_to_account_ids
        self.create_grant_write_to_account_ids = create_grant_write_to_account_ids
        self.create_lifecycle_rules = create_lifecycle_rules
        self.existing_repo_arn = existing_repo_arn
        self.image_tag = environment.environment_name.lower() + '-current'
        self.parameter_definitions = parameter_definitions
        self.parameter_values = parameter_values
        self.task_definition_env_vars = task_definition_env_vars


class EnergyUsageAppStack(Stack):
    """
    A stack that represents a deployment of the application into a single environment.
    """

    def __init__(self, scope: Construct, construct_id: str, properties: EnergyUsageAppProperties,
                 **kwargs) -> None:
        """
        Create a stack that represents a deployment of the application into a single environment.

        Parameters
        ----------
        scope : str
            The scope where the stack should be created.
        construct_id : str
            The logical name of the stack to identify it within the scope.
        properties : EnergyUsageAppProperties
            Configuration values for creating the stack.
        kwargs : Any
            Additional keyword arguments.
        """
        env = Environment(account=properties.environment.account_id, region=properties.context.region)
        super().__init__(scope, construct_id, stack_name=properties.stack_name, env=env, **kwargs)

        # ECR repository

        repo_properties = EnergyUsageEcrRepoProperties(
            create_repo=properties.create_repo,
            create_base_name=properties.base_name,
            create_grant_read_to_account_ids=properties.create_grant_read_to_account_ids,
            create_grant_write_to_account_ids=properties.create_grant_write_to_account_ids,
            create_lifecycle_rules=properties.create_lifecycle_rules,
            existing_repo_arn=properties.existing_repo_arn
        )
        repo = EnergyUsageEcrRepoConstruct(self, 'repo', properties=repo_properties)

        # S3 Bucket

        storage_properties = EnergyUsageStorageProperties(base_name=properties.base_name,
                                                          target_account_id=properties.environment.account_id)
        bucket = EnergyUsageStorageConstruct(self, 'storage', properties=storage_properties)

        # Snowflake Role

        snowflake_role_properties = EnergyUsageSnowflakeRoleProperties(
            snowflake_principal_arn=properties.environment.settings.snowflake_principal_arn,
            snowflake_principal_external_id=properties.environment.settings.snowflake_principal_external_id,
            bucket=bucket.bucket)
        EnergyUsageSnowflakeRoleConstruct(self, 'snowflake-role', properties=snowflake_role_properties)

        # Systems Manager Parameters

        parameters_properties = EnergyUsageParametersProperties(base_name=properties.base_name,
                                                                parameter_definitions=properties.parameter_definitions,
                                                                parameter_values=properties.parameter_values)
        parameters = EnergyUsageParametersConstruct(self, 'parameters', properties=parameters_properties)

        # ECS Task Definition

        task_properties = EnergyUsageTaskProperties(base_name=properties.base_name,
                                                    vpc_id=properties.environment.vpc_id,
                                                    subnet_ids=properties.environment.private_subnet_ids,
                                                    bucket=bucket.bucket,
                                                    ecr_repo=repo.repo,
                                                    image_tag=properties.image_tag,
                                                    task_definition_env_vars=properties.task_definition_env_vars,
                                                    parameters=parameters.parameters)
        EnergyUsageTaskConstruct(self, 'task', properties=task_properties)

        # Apply Tags

        product_name = properties.context.app_info.product_name
        service_name = properties.context.app_info.service_name
        environment_name = properties.environment.environment_name
        support_level = properties.context.app_info.support_level
        cost_centre = properties.context.app_info.cost_centre
        sub_project_code = properties.context.app_info.sub_project_code

        Tags.of(self).add('Product', product_name)
        Tags.of(self).add('Service', service_name)
        Tags.of(self).add('Environment', environment_name)
        if support_level is not None and len(support_level) > 0 and not support_level.isspace():
            Tags.of(self).add('Support-Level', support_level)
        if cost_centre is not None and len(cost_centre) > 0 and not cost_centre.isspace():
            Tags.of(self).add('Cost-Centre', cost_centre)
        if sub_project_code is not None and len(sub_project_code) > 0 and not sub_project_code.isspace():
            Tags.of(self).add('Sub-Project-Code', sub_project_code)
