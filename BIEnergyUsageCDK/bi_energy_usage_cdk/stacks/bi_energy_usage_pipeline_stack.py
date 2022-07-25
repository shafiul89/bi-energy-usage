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

        # Add Development stage
        dev_env = self.context.environments.dev
        dev_create_change_set_action, dev_execute_change_set_action = self.create_cloud_formation_actions(
            dev_env, synth_artifact, 1
        )
        dev_actions = [dev_create_change_set_action, dev_execute_change_set_action]
        if context.pipeline.docker_deploy:
            dev_docker_build_action = self.create_dev_docker_build_action(source_artifact, 3)
            dev_actions.append(dev_docker_build_action)
        pipeline.add_stage(stage_name='Development', actions=dev_actions)

        # Add Test stage
        test_env = self.context.environments.test
        test_approval_action = self.create_manual_approval_action('Test', source_variable_namespace, 1)
        test_create_change_set_action, test_execute_change_set_action = self.create_cloud_formation_actions(
            test_env, synth_artifact, 2
        )
        test_actions = [test_approval_action, test_create_change_set_action, test_execute_change_set_action]
        if context.pipeline.docker_deploy:
            test_retag_action = self.create_docker_retag_image_action(source_artifact, test_env.environment_name, 4)
            test_actions.append(test_retag_action)
        pipeline.add_stage(stage_name='Test', actions=test_actions)

        # Add Stg stage
        stg_env = self.context.environments.stg
        stg_approval_action = self.create_manual_approval_action('Stg', source_variable_namespace, 1)
        stg_create_change_set_action, stg_execute_change_set_action = self.create_cloud_formation_actions(
            stg_env, synth_artifact, 2
        )
        stg_actions = [stg_approval_action, stg_create_change_set_action, stg_execute_change_set_action]
        if context.pipeline.docker_deploy:
            stg_retag_action = self.create_docker_retag_image_action(source_artifact, stg_env.environment_name, 4)
            stg_actions.append(stg_retag_action)
        pipeline.add_stage(stage_name='Staging', actions=stg_actions)

        # Add Prod stage
        prod_env = self.context.environments.prod
        prod_approval_action = self.create_manual_approval_action('Prod', source_variable_namespace, 1)
        prod_create_change_set_action, prod_execute_change_set_action = self.create_cloud_formation_actions(
            prod_env, synth_artifact, 2
        )
        prod_actions = [prod_approval_action, prod_create_change_set_action, prod_execute_change_set_action]
        if context.pipeline.docker_deploy:
            prod_docker_image_copy_action = self.create_prod_docker_image_copy_action(source_artifact, 4)
            prod_actions.append(prod_docker_image_copy_action)
        pipeline.add_stage(stage_name='Production', actions=prod_actions)

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

    # -------------------- CREATE CLOUD FORMATION CHANGE SET ACTIONS --------------------

    def create_cloud_formation_actions(self,
                                       environment: ctxmgr.EnvironmentContext,
                                       synth_artifact: aws_codepipeline.Artifact,
                                       run_order_from: int):
        """
        Create CodePipeline CloudFormation actions to deploy AWS resource changes for a specific environment.

        Two CodePipeline CloudFormation actions are created:

        The first action created is a "Create Change Set" action which compares the output of the CDK Synth
        to the currently deployed stack (if any) in the specified environment.  The change set describes the
        AWS resource changes that need to be applied to make the stack in AWS match the resources specified
        in the CDK project.

        The second action created is an "Execute Change Set" action.  This executes the change set created in
        the first action to apply the changes to the resources in the stack in AWS.

        Parameters
        ----------
        environment : ctxmgr.EnvironmentContext
            Context/settings for the environment where the CloudFormation changes are to be applied.
        synth_artifact : aws_codepipeline.Artifact
            The output from the CDK Synth action earlier in the pipeline.
        run_order_from : int
            The position of these actions in the CodePipeline stage.

        Returns
        -------
        (aws_codepipeline_actions.CloudFormationCreateReplaceChangeSetAction,
        aws_codepipeline_actions.CloudFormationExecuteChangeSetAction)
            Two CodePipeline CloudFormation actions.
        """
        # Variations of environment name
        env_name_lower = environment.environment_name.lower()
        env_name_title = environment.environment_name.title()
        # Create change set action
        # This creates a pipeline action that will create a CloudFormation change set when the pipeline is executed
        # i.e. the change set is not created now, rather a 'Create Change Set' action is created
        create_change_set_action = aws_codepipeline_actions.CloudFormationCreateReplaceChangeSetAction(
            action_name=f'Create-Change-Set-{env_name_title}',
            admin_permissions=True,
            change_set_name=f'{env_name_title}-Stack-Changes',
            stack_name=self.context.get_resource_base_name(env_name_title, 'App'),
            template_path=aws_codepipeline.ArtifactPath(synth_artifact, f'{env_name_lower}-app.template.json'),
            account=environment.account_id,
            region=self.context.region,
            run_order=run_order_from
        )
        # Execute change set action
        # This creates a pipeline action that will execute a CloudFormation change set when the pipeline is executed
        # i.e. no change set is executes now, rather an 'Execute Change Set' action is created
        execute_change_set_action = aws_codepipeline_actions.CloudFormationExecuteChangeSetAction(
            action_name=f'Execute-Change-Set-{env_name_title}',
            change_set_name=f'{env_name_title}-Stack-Changes',
            stack_name=self.context.get_resource_base_name(env_name_title, 'App'),
            account=environment.account_id,
            region=self.context.region,
            run_order=run_order_from + 1
        )
        return create_change_set_action, execute_change_set_action

    # -------------------- DOCKER IMAGE BUILD ACTION --------------------

    def create_dev_docker_build_action(self, source_artifact: aws_codepipeline.Artifact, run_order: int):
        """
        Create a CodePipeline CodeBuild action that will build a docker image.

        This includes creating the CodeBuild project and Log Group.

        This also includes creating the necessary IAM policies to allow CodeBuild to interact with the ECR repo
        to push the docker image into the repo.

        Parameters
        ----------
        source_artifact : aws_codepipeline.Artifact
            The CodePipeline artifact containing the source code from GitHub.
        run_order : int
            The position of this action in the CodePipeline stage.

        Returns
        -------
        aws_codepipeline_actions.CodeBuildAction
            The CodePipeline CodeBuild action
        """
        # constants
        dev_account_id = self.context.environments.dev.account_id
        dev_env_name = self.context.environments.dev.environment_name
        dev_repo_name = self.context.get_resource_base_name(dev_env_name, '').lower()
        dev_repo_arn = f'arn:aws:ecr:{self.context.region}:{dev_account_id}:repository/{dev_repo_name}'
        dev_image_name = f'{dev_account_id}.dkr.ecr.{self.context.region}.amazonaws.com/{dev_repo_name}'

        # ECR IAM policies for docker push
        add_policy_1 = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,  # cannot refer to repo object across stage boundaries, so use repo arn
            actions=['ecr:*', 'sts:GetServiceBearerToken'],
            resources=[dev_repo_arn]
        )
        add_policy_2 = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=['ecr:GetAuthorizationToken'],
            resources=['*']
        )

        # Docker image build commands
        src_image_name = 'energy-usage-app'
        docker_build_cmd = f'docker build -t {src_image_name}:latest .'
        get_pwd_cmd = f'aws ecr get-login-password --region {self.context.region} | '
        get_pwd_cmd += f'docker login --username AWS --password-stdin '
        get_pwd_cmd += f'{dev_account_id}.dkr.ecr.{self.context.region}.amazonaws.com'
        tag_cmd_1 = f'docker tag {src_image_name}:latest {dev_image_name}:$CODEBUILD_RESOLVED_SOURCE_VERSION'
        tag_cmd_2 = f'docker tag {src_image_name}:latest {dev_image_name}:{dev_env_name.lower()}-current'
        tag_cmd_3 = f'docker tag {src_image_name}:latest {dev_image_name}:{dev_env_name.lower()}-$CRUKTAGTIMEUTC'
        tag_cmd_4 = f'docker tag {src_image_name}:latest {dev_image_name}:latest'
        # since there are multiple tags, we could either push each tag individually (e.g. as shown below)
        # push_cmd_1 = f'docker push {target_image_name}:$CODEBUILD_RESOLVED_SOURCE_VERSION'
        # push_cmd_2 = f'docker push {target_image_name}:dev'
        # push_cmd_3 = f'docker push {target_image_name}:latest'
        # or simply omit the tag and push all tags for the specified image
        push_cmd = f'docker push {dev_image_name} --all-tags'
        describe_cmd = f'aws ecr describe-images --region {self.context.region} --repository-name {dev_repo_name} ' + \
                       f'--image-ids imageTag=$CODEBUILD_RESOLVED_SOURCE_VERSION'

        # Docker image build codebuild spec
        docker_build_spec = {
            'version': '0.2',
            'phases': {
                'build': {
                    'commands': [
                        'printenv',
                        'docker version',
                        'cd BIEnergyUsageApp',
                        docker_build_cmd,
                        get_pwd_cmd,
                        'CRUKTAGTIMEUTC=$(date +"%Y-%m-%d--%H-%M-%S")',
                        'echo $CRUKTAGTIMEUTC',
                        tag_cmd_1,
                        tag_cmd_2,
                        tag_cmd_3,
                        tag_cmd_4,
                        push_cmd,
                        describe_cmd
                    ]
                }
            }
        }

        # Docker build Project
        project_name = self.context.get_resource_base_name(dev_env_name.title(), 'Docker-Build')
        log_group = aws_logs.LogGroup(self, dev_env_name.lower() + '-docker-build-log-group',
                                      log_group_name=f'/pipeline/{project_name.lower()}',
                                      removal_policy=RemovalPolicy.DESTROY,
                                      retention=aws_logs.RetentionDays.TWO_YEARS)
        docker_build_project = aws_codebuild.Project(
            self, f'Build-Docker-Image-{dev_env_name.title()}',
            project_name=project_name,
            build_spec=aws_codebuild.BuildSpec.from_object(docker_build_spec),
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_5_0,
                privileged=True,
            ),
            logging=aws_codebuild.LoggingOptions(
                cloud_watch=aws_codebuild.CloudWatchLoggingOptions(
                    enabled=True, log_group=log_group, prefix='pipeline'
                ),
            ),
            queued_timeout=Duration.hours(8),
            timeout=Duration.hours(1)
        )
        docker_build_project.role.add_to_principal_policy(add_policy_1)
        docker_build_project.role.add_to_principal_policy(add_policy_2)

        # Docker Build Action
        docker_build_action = aws_codepipeline_actions.CodeBuildAction(
            action_name='Build-Docker-Image',
            input=source_artifact,
            project=docker_build_project,
            run_order=run_order
        )
        return docker_build_action

    # -------------------- MANUAL APPROVAL ACTION --------------------

    def create_manual_approval_action(self, environment_name: str, source_variable_namespace: str, run_order: int):
        """
        Create a CodePipeline action to request a manual approval before pipeline execution can continue.

        The manual approval prompt includes a link to the commit in GitHub.

        Parameters
        ----------
        environment_name : str
            The name of the environment being deployed to at this stage in the pipeline.
        source_variable_namespace : str
            The variable namespace where CodePipeline source variables are stored.
        run_order : int
            The position of this action in the CodePipeline stage.

        Returns
        -------
        aws_codepipeline_actions.ManualApprovalAction
            A CodePipeline manual approval action.
        """
        cc = self.context.code_connection
        commit_url = f'https://github.com/{cc.github_owner_name}/{cc.github_repo_name}/commit/'
        commit_url += '#{' + source_variable_namespace + '.CommitId}'
        test_approval_action = aws_codepipeline_actions.ManualApprovalAction(
            action_name=f'{environment_name}-Approval',
            additional_information='Commit:  #{' + source_variable_namespace + '.CommitMessage}',
            external_entity_link=commit_url,
            run_order=run_order
        )
        return test_approval_action

    # -------------------- DOCKER IMAGE RETAG ACTION --------------------

    def create_docker_retag_image_action(self,
                                         source_artifact: aws_codepipeline.Artifact,
                                         environment_name: str,
                                         run_order: int):
        """
        Create a CodePipeline CodeBuild action that will retag a docker image.

        Two tags will be added to the image:

        (environment_name)-current, e.g. test-current

        (environment_name)-yyyy-mm-dd--HH-MM-SS, e.g. test-20220722--124756

        This method also creates the CodeBuild project and Log Group.

        This also includes creating the necessary IAM policies to allow CodeBuild to interact with the ECR repo
        to push the docker image tags into the repo.

        Parameters
        ----------
        source_artifact : aws_codepipeline.Artifact
            The CodePipeline artifact containing the source code from GitHub.
        environment_name : str
            The name of the environment, e.g. test.
        run_order : int
            The position of this action in the CodePipeline stage.

        Returns
        -------
        aws_codepipeline_actions.CodeBuildAction
            The CodePipeline CodeBuild action
        """
        # constants
        dev_account_id = self.context.environments.dev.account_id
        dev_env_name = self.context.environments.dev.environment_name
        dev_repo_name = self.context.get_resource_base_name(dev_env_name, '').lower()
        dev_repo_arn = f'arn:aws:ecr:{self.context.region}:{dev_account_id}:repository/{dev_repo_name}'
        dev_image_name = f'{dev_account_id}.dkr.ecr.{self.context.region}.amazonaws.com/{dev_repo_name}'
        dev_image_name_and_tag = dev_image_name + ':$CODEBUILD_RESOLVED_SOURCE_VERSION'
        env_name_lower = environment_name.lower()
        env_name_title = environment_name.title()

        # ECR IAM policies for docker push
        add_policy_1 = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,  # cannot refer to repo object across stage boundaries, so use repo arn
            actions=['ecr:*', 'sts:GetServiceBearerToken'],
            resources=[dev_repo_arn]
        )
        add_policy_2 = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=['ecr:GetAuthorizationToken'],
            resources=['*']
        )

        # Docker image re-tagging for non-prod environments after dev
        get_pwd_cmd = f'aws ecr get-login-password --region {self.context.region} | '
        get_pwd_cmd += f'docker login --username AWS --password-stdin '
        get_pwd_cmd += f'{dev_account_id}.dkr.ecr.{self.context.region}.amazonaws.com'
        docker_pull_cmd = f'docker pull {dev_image_name_and_tag}'
        tag_cmd_1 = f'docker tag {dev_image_name_and_tag} {dev_image_name}:{env_name_lower}-current'
        tag_cmd_2 = f'docker tag {dev_image_name_and_tag} {dev_image_name}:{env_name_lower}-$CRUKTAGTIMEUTC'
        push_cmd = f'docker push {dev_image_name} --all-tags'
        describe_cmd = f'aws ecr describe-images --region {self.context.region} --repository-name {dev_repo_name} ' + \
                       f'--image-ids imageTag=$CODEBUILD_RESOLVED_SOURCE_VERSION'

        # Docker image re-tag codebuild spec
        docker_retag_spec = {
            'version': '0.2',
            'phases': {
                'build': {
                    'commands': [
                        'printenv',
                        'docker version',
                        get_pwd_cmd,
                        docker_pull_cmd,
                        'CRUKTAGTIMEUTC=$(date +"%Y-%m-%d--%H-%M-%S")',
                        'echo $CRUKTAGTIMEUTC',
                        tag_cmd_1,
                        tag_cmd_2,
                        push_cmd,
                        describe_cmd
                    ]
                }
            }
        }

        # Docker build Project
        project_name = self.context.get_resource_base_name(env_name_title, 'Docker-Retag')
        log_group = aws_logs.LogGroup(self, env_name_lower + '-docker-retag-log-group',
                                      log_group_name=f'/pipeline/{project_name.lower()}',
                                      removal_policy=RemovalPolicy.DESTROY,
                                      retention=aws_logs.RetentionDays.TWO_YEARS)
        docker_retag_project = aws_codebuild.Project(
            self, f'Docker-{env_name_title}-Retag',
            project_name=project_name,
            build_spec=aws_codebuild.BuildSpec.from_object(docker_retag_spec),
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_5_0,
                privileged=True,
            ),
            logging=aws_codebuild.LoggingOptions(
                cloud_watch=aws_codebuild.CloudWatchLoggingOptions(
                    enabled=True, log_group=log_group, prefix='pipeline'
                ),
            ),
            queued_timeout=Duration.hours(8),
            timeout=Duration.hours(1)
        )
        docker_retag_project.role.add_to_principal_policy(add_policy_1)
        docker_retag_project.role.add_to_principal_policy(add_policy_2)

        # Docker Action
        docker_retag_action = aws_codepipeline_actions.CodeBuildAction(
            action_name=f'Retag-Docker-Image-{env_name_title}',
            input=source_artifact,
            project=docker_retag_project,
            run_order=run_order
        )
        return docker_retag_action

    # -------------------- DOCKER IMAGE COPY ACTION --------------------

    def create_prod_docker_image_copy_action(self,
                                             source_artifact: aws_codepipeline.Artifact,
                                             run_order: int):
        """
        Create a CodePipeline CodeBuild action that will copy a docker image from a non-prod repo to a prod repo.

        Three tags will be added to the image:

        - git commit id, e.g. 6018db2b40d6ed662e94854bbe59a55a40cd02be
        - prod-current
        - prod-yyyy-mm-dd--HH-MM-SS, e.g. prod-20220722--124756

        This method also creates the CodeBuild project and Log Group.

        This also includes creating the necessary IAM policies to allow CodeBuild to interact with the ECR repos
        to pull/push the docker image and tags.

        Parameters
        ----------
        source_artifact : aws_codepipeline.Artifact
            The CodePipeline artifact containing the source code from GitHub.
        run_order : int
            The position of this action in the CodePipeline stage.

        Returns
        -------
        aws_codepipeline_actions.CodeBuildAction
            The CodePipeline CodeBuild action
        """
        # constants
        dev_account_id = self.context.environments.dev.account_id
        dev_env_name = self.context.environments.dev.environment_name
        dev_repo_name = self.context.get_resource_base_name(dev_env_name, '').lower()
        dev_repo_arn = f'arn:aws:ecr:{self.context.region}:{dev_account_id}:repository/{dev_repo_name}'
        dev_image_name = f'{dev_account_id}.dkr.ecr.{self.context.region}.amazonaws.com/{dev_repo_name}'
        dev_image_name_and_tag = dev_image_name + ':$CODEBUILD_RESOLVED_SOURCE_VERSION'
        prod_account_id = self.context.environments.prod.account_id
        prod_env_name = self.context.environments.prod.environment_name
        prod_repo_name = self.context.get_resource_base_name(prod_env_name, '').lower()
        prod_repo_arn = f'arn:aws:ecr:{self.context.region}:{prod_account_id}:repository/{prod_repo_name}'
        prod_image_name = f'{prod_account_id}.dkr.ecr.{self.context.region}.amazonaws.com/{prod_repo_name}'
        prod_image_name_and_tag = prod_image_name + ':$CODEBUILD_RESOLVED_SOURCE_VERSION'

        # ECR IAM policies for docker pull and push
        add_policy_1 = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,  # cannot refer to repo object across stage boundaries, so use repo arn
            actions=['ecr:*', 'sts:GetServiceBearerToken'],
            resources=[dev_repo_arn, prod_repo_arn]
        )
        add_policy_2 = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=['ecr:GetAuthorizationToken'],
            resources=['*']
        )

        # Docker image copy to prod repo and re-tagging for Prod environment
        get_pwd_cmd_1 = f'aws ecr get-login-password --region {self.context.region} | '
        get_pwd_cmd_1 += f'docker login --username AWS --password-stdin '
        get_pwd_cmd_1 += f'{dev_account_id}.dkr.ecr.{self.context.region}.amazonaws.com'
        docker_pull_cmd = f'docker pull {dev_image_name_and_tag}'
        tag_cmd_1 = f'docker tag {dev_image_name_and_tag} {prod_image_name_and_tag}'
        tag_cmd_2 = f'docker tag {dev_image_name_and_tag} {prod_image_name}:{prod_env_name.lower()}-current'
        tag_cmd_3 = f'docker tag {dev_image_name_and_tag} {prod_image_name}:{prod_env_name.lower()}-$CRUKTAGTIMEUTC'
        get_pwd_cmd_2 = f'aws ecr get-login-password --region {self.context.region} | '
        get_pwd_cmd_2 += f'docker login --username AWS --password-stdin '
        get_pwd_cmd_2 += f'{prod_account_id}.dkr.ecr.{self.context.region}.amazonaws.com'
        push_cmd_1 = f'docker push {prod_image_name_and_tag}'
        push_cmd_2 = f'docker push {prod_image_name}:{prod_env_name}-current'
        push_cmd_3 = f'docker push {prod_image_name}:{prod_env_name}-$CRUKTAGTIMEUTC'
        describe_cmd = f'aws ecr describe-images --region {self.context.region} --repository-name {prod_repo_name} ' + \
                       f'--registry-id {prod_account_id} --image-ids imageTag=$CODEBUILD_RESOLVED_SOURCE_VERSION'

        # docker image build spec
        docker_push_spec = {
            'version': '0.2',
            'phases': {
                'build': {
                    'commands': [
                        'printenv',
                        'docker version',
                        get_pwd_cmd_1,
                        docker_pull_cmd,
                        'CRUKTAGTIMEUTC=$(date +"%Y-%m-%d--%H-%M-%S")',
                        'echo $CRUKTAGTIMEUTC',
                        tag_cmd_1,
                        tag_cmd_2,
                        tag_cmd_3,
                        get_pwd_cmd_2,
                        push_cmd_1,
                        push_cmd_2,
                        push_cmd_3,
                        describe_cmd
                    ]
                }
            }
        }

        # Docker push project
        project_name = self.context.get_resource_base_name(prod_env_name.title(), 'Docker-Push')
        log_group = aws_logs.LogGroup(self, prod_env_name.lower() + '-docker-push-log-group',
                                      log_group_name=f'/pipeline/{project_name.lower()}',
                                      removal_policy=RemovalPolicy.DESTROY,
                                      retention=aws_logs.RetentionDays.TWO_YEARS)
        docker_push_project = aws_codebuild.Project(
            self, f'Docker-Push-{prod_env_name.title()}',
            project_name=project_name,
            build_spec=aws_codebuild.BuildSpec.from_object(docker_push_spec),
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_5_0,
                privileged=True,
            ),
            logging=aws_codebuild.LoggingOptions(
                cloud_watch=aws_codebuild.CloudWatchLoggingOptions(
                    enabled=True, log_group=log_group, prefix='pipeline'
                ),
            ),
            queued_timeout=Duration.hours(8),
            timeout=Duration.hours(1)
        )
        docker_push_project.role.add_to_principal_policy(add_policy_1)
        docker_push_project.role.add_to_principal_policy(add_policy_2)

        # Docker Action
        docker_push_action = aws_codepipeline_actions.CodeBuildAction(
            action_name=f'Push-Docker-Image-{prod_env_name.title()}',
            input=source_artifact,
            project=docker_push_project,
            run_order=run_order
        )
        return docker_push_action
