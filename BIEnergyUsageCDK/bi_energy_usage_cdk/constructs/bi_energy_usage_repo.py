from aws_cdk import (
    aws_ecr,
    aws_iam,
    RemovalPolicy
)
from constructs import Construct

from bi_energy_usage_cdk.utilities.docker_lifecycle_rules \
    import DockerImageLifecycleRules, create_repo_lifecycle_rules


class EnergyUsageEcrRepoProperties:
    """
    Configuration values for creating an instance of the EnergyUsageEcrRepoConstruct class.
    """
    
    def __init__(self, create_repo: bool, create_base_name: str,
                 create_grant_read_to_account_ids: list[str] = None,
                 create_grant_write_to_account_ids: list[str] = None,
                 create_lifecycle_rules: DockerImageLifecycleRules = DockerImageLifecycleRules.DEFAULT,
                 existing_repo_arn: str = ''):
        """
        Create configuration values for creating an instance of the EnergyUsageEcrRepoConstruct class.

        Parameters
        ----------
        create_repo : bool
            True to create a new ECR repository, False to link to an existing ECR repository.
        create_base_name : str
            The name of the ECR repository that will be created.
        create_grant_read_to_account_ids : list[str]
            A list of AWS account IDs to be granted read access to the ECR repository that will be created.
        create_grant_write_to_account_ids : list[str]
            A list of AWS account IDs to be granted write access to the ECR repository that will be created.
        create_lifecycle_rules : DockerImageLifecycleRules
            A set of docker image lifecycle rules to be applied to the ECR repository that will be created.
        existing_repo_arn : str
            The AWS ARN of the existing ECR repository that will be linked to.
        """
        self.create_repo = create_repo
        self.create_base_name = create_base_name
        self.create_grant_read_to_account_ids = create_grant_read_to_account_ids
        self.create_grant_write_to_account_ids = create_grant_write_to_account_ids
        self.create_lifecycle_rules = create_lifecycle_rules
        self.existing_repo_arn = existing_repo_arn


class EnergyUsageEcrRepoConstruct(Construct):
    """
    A construct that creates a new ECR repository or links to an existing ECR repository.
    """

    def __init__(self, scope: Construct, construct_id: str, *, properties: EnergyUsageEcrRepoProperties) -> None:
        """
        Create a construct that creates a new ECR repository or links to an existing ECR repository.

        IAM policies are also created that grant access to the ECR repository.

        Parameters
        ----------
        scope : str
            The scope where the construct should be created.
        construct_id : str
            The logical name of the construct to identify it within the scope.
        properties : EnergyUsageEcrRepoProperties
            Configuration values for creating the construct.
        """
        super().__init__(scope, construct_id)

        if properties.create_repo:
            # create repo
            repo = aws_ecr.Repository(self, 'repo',
                                      repository_name=properties.create_base_name,
                                      removal_policy=RemovalPolicy.DESTROY,
                                      lifecycle_rules=create_repo_lifecycle_rules(properties.create_lifecycle_rules))

            # grant specific accounts permission to read from this repo (e.g. so test can read from the dev repo)
            account_ids = properties.create_grant_read_to_account_ids
            if account_ids is not None and len(account_ids) > 0:
                account_principals = [aws_iam.AccountPrincipal(account_id) for account_id in account_ids]
                repo_policy = aws_iam.PolicyStatement(
                    sid='allowCrossAccountPull',
                    effect=aws_iam.Effect.ALLOW,
                    principals=account_principals,
                    actions=['ecr:ListImages',
                             'ecr:DescribeImages',
                             'ecr:GetDownloadUrlForLayer',
                             'ecr:BatchCheckLayerAvailability',
                             'ecr:BatchGetImage',
                             'ecr:ListTagsForResource']
                )
                repo.add_to_resource_policy(repo_policy)

            # grant specific accounts permission to push to this repo (i.e. so pipeline in dev can push to prod account)
            account_ids = properties.create_grant_write_to_account_ids
            if account_ids is not None and len(account_ids) > 0:
                account_principals = [aws_iam.AccountPrincipal(account_id) for account_id in account_ids]
                repo_policy = aws_iam.PolicyStatement(
                    sid='allowCrossAccountPush',
                    effect=aws_iam.Effect.ALLOW,
                    principals=account_principals,
                    actions=[
                        'ecr:ListImages',
                        'ecr:DescribeImages',
                        'ecr:GetDownloadUrlForLayer',
                        'ecr:BatchCheckLayerAvailability',
                        'ecr:BatchGetImage',
                        'ecr:ListTagsForResource',
                        'ecr:InitiateLayerUpload',
                        'ecr:UploadLayerPart',
                        'ecr:CompleteLayerUpload',
                        'ecr:PutImage'
                    ]
                )
                repo.add_to_resource_policy(repo_policy)

            self.repo = repo
        else:
            self.repo = aws_ecr.Repository.from_repository_arn(self, 'repo', properties.existing_repo_arn)