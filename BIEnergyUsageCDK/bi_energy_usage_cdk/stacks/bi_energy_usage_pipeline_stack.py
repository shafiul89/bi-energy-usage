import bi_energy_usage_cdk.utilities.context_manager as ctxmgr
from aws_cdk import (
    aws_codebuild,
    aws_codepipeline,
    aws_codepipeline_actions,
    aws_iam,
    aws_logs,
    aws_s3,
    Duration,
    Environment,
    RemovalPolicy,
    Stack
)
from constructs import Construct


class EnergyUsagePipelineStack(Stack):
    """
    A stack that represents a deployment of the CI/CD pipeline into the dev environment.
    """

    def __init__(self, scope: Construct, construct_id: str, context: ctxmgr.ContextManager, **kwargs) -> None:
        """
        Create a stack that represents a deployment of the CI/CD pipeline into the dev environment.

        Parameters
        ----------
        scope : str
            The scope where the stack should be created.
        construct_id : str
            The logical name of the stack to identify it within the scope.
        context : ctxmgr.ContextManager
            Context/settings from the cdk.json file.
        kwargs : Any
            Additional keyword arguments (none currently).
        """
        base_name = context.get_resource_base_name('Dev', 'Pipeline')
        dev_env = Environment(account=context.environments.dev.account_id, region=context.region)
        super().__init__(scope, construct_id, stack_name=base_name, env=dev_env, **kwargs)

        # needed below and in other methods
        self.base_name = base_name.lower()  # base_name to lower case for all subsequent resources
        self.context = context

        # Pipeline storage
        pipeline_bucket = aws_s3.Bucket(self, 'pipeline-bucket',
                                        bucket_name=base_name.lower(),
                                        encryption=aws_s3.BucketEncryption.KMS,
                                        removal_policy=RemovalPolicy.DESTROY,
                                        block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL)

        # Pipeline construct
        pipeline = aws_codepipeline.Pipeline(self, 'pipeline',
                                             artifact_bucket=pipeline_bucket,
                                             cross_account_keys=True,
                                             pipeline_name=base_name)

        # Add Source stage
        source_artifact, source_variable_namespace, code_connection_action = self.create_code_connection_action()
        pipeline.add_stage(stage_name='Source', actions=[code_connection_action])

        # Add Synth stage
        synth_project = self.create_synth_code_build_project()
        synth_artifact, synth_action = self.create_synth_action(source_artifact, synth_project)
        pipeline.add_stage(stage_name='Build', actions=[synth_action])

    # -------------------- CREATE CODE CONNECTION TO GITHUB --------------------

    def create_code_connection_action(self):
        """
        Create a code connection that allows a CodePipeline instance to read source code from GitHub.

        The return value is a tuple containing:

        - The CodePipeline artifact that represents the source code from GitHub.
        - The variable namespace where CodePipeline source variables are stored.
        - The code connection object to be added to the CodePipeline instance.

        Returns
        -------
        (aws_codepipeline.Artifact, str, aws_codepipeline_actions.CodeStarConnectionsSourceAction)
            A tuple of three values - see above for details.
        """
        source_artifact_name = self.base_name + '-Source'
        source_artifact = aws_codepipeline.Artifact(artifact_name=source_artifact_name)
        source_variable_namespace = self.base_name.lower() + '-source-vars'
        code_connection_action = aws_codepipeline_actions.CodeStarConnectionsSourceAction(
            connection_arn=self.context.code_connection.arn,
            owner=self.context.code_connection.github_owner_name,
            repo=self.context.code_connection.github_repo_name,
            branch=self.context.code_connection.github_branch_name,
            output=source_artifact,
            trigger_on_push=self.context.pipeline.trigger_on_push,
            action_name='Get-Source',
            variables_namespace=source_variable_namespace
        )
        return source_artifact, source_variable_namespace, code_connection_action

    # -------------------- CREATE SYNTH ACTION TO BUILD CDK PROJECT --------------------

    def create_synth_code_build_project(self):
        """
        Create a CodeBuild project that will perform a CDK synth.

        Returns
        -------
        aws_codebuild.Project
            The CodeBuild project containing the build spec and log group definition.

        """
        # CDK Synth build-spec
        synth_build_spec = {
            'version': '0.2',
            'phases': {
                'build': {
                    'commands': [
                        'printenv',
                        'cd BIEnergyUsageCDK',
                        'pip install -r requirements.txt',
                        'npm install -g aws-cdk',
                        'cdk synth'
                    ]
                }
            },
            'artifacts': {
                'base-directory': 'BIEnergyUsageCDK/cdk.out',
                'files': '**/*'
            }
        }
        # CDK Synth Project
        project_name = self.context.get_resource_base_name('Dev', 'Synth')
        log_group = aws_logs.LogGroup(self, 'cdk-synth-log-group',
                                      log_group_name=f'/pipeline/{project_name.lower()}',
                                      removal_policy=RemovalPolicy.DESTROY,
                                      retention=aws_logs.RetentionDays.TWO_YEARS)
        synth_project = aws_codebuild.Project(
            self, 'Build-Project',
            project_name=project_name,
            build_spec=aws_codebuild.BuildSpec.from_object(synth_build_spec),
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_5_0,
                privileged=True,
            ),
            logging=aws_codebuild.LoggingOptions(
                cloud_watch=aws_codebuild.CloudWatchLoggingOptions(
                    enabled=True, log_group=log_group, prefix='pipeline'
                ),
            ),
            queued_timeout=Duration.hours(1),
            timeout=Duration.hours(1)
        )
        return synth_project

    def create_synth_action(self, source_artifact: aws_codepipeline.Artifact, synth_project: aws_codebuild.Project):
        """
        Create a CodePipeline action that executes a CodeBuild project to perform a CDK synth.

        Parameters
        ----------
        source_artifact : aws_codepipeline.Artifact
            A CodePipeline artifact containing the source code from GitHub.
        synth_project : aws_codebuild.Project
            A CodeBuild project that executes a CDK Synth.

        Returns
        -------
        (aws_codepipeline.Artifact, aws_codepipeline_actions.CodeBuildAction)
            A tuple consisting of the CDK Synth output artifact and the CodePipleline action to perform the CDK synth.
        """
        # CDK Synth Action
        synth_artifact_name = self.base_name + '-Synth'
        synth_artifact = aws_codepipeline.Artifact(artifact_name=synth_artifact_name)
        synth_action = aws_codepipeline_actions.CodeBuildAction(
            action_name='Synth',
            input=source_artifact,
            project=synth_project,
            outputs=[synth_artifact]
        )
        return synth_artifact, synth_action