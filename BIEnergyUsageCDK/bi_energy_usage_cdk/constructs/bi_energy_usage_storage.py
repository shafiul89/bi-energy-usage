from aws_cdk import (
    aws_s3,
    aws_iam,
    Duration,
    RemovalPolicy
)
from constructs import Construct


class EnergyUsageStorageProperties:
    """
    Configuration values for creating an instance of the EnergyUsageStorageConstruct class.
    """

    def __init__(self, base_name: str, target_account_id: str):
        """
        Create configuration values for creating an instance of the EnergyUsageStorageConstruct class.

        Parameters
        ----------
        base_name : str
            The base name for the bucket to be created.
        target_account_id : str
            The AWS account ID where the bucket is to be created.
        """
        self.base_name = base_name
        self.target_account_id = target_account_id


class EnergyUsageStorageConstruct(Construct):
    """
    A construct that creates a new S3 bucket.
    """

    def __init__(self, scope: Construct, construct_id: str, *, properties: EnergyUsageStorageProperties) -> None:
        """
        Create a construct that creates a new S3 bucket.

        IAM Policies that control access to the bucket are also created.

        Parameters
        ----------
        scope : str
            The scope where the construct should be created.
        construct_id : str
            The logical name of the construct to identify it within the scope.
        properties : EnergyUsageStorageProperties
            Configuration values for creating the construct.
        """
        super().__init__(scope, construct_id)

        s3_bucket = aws_s3.Bucket(self, 'bucket',
                                  bucket_name=properties.base_name,
                                  removal_policy=RemovalPolicy.DESTROY,
                                  block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
                                  object_ownership=aws_s3.ObjectOwnership.BUCKET_OWNER_ENFORCED)

        self.bucket = s3_bucket

        # grant permissions on the bucket to any principal in the account
        s3_bucket.add_to_resource_policy(
            aws_iam.PolicyStatement(
                sid='BucketPermissions',
                effect=aws_iam.Effect.ALLOW,
                actions=['s3:*'],
                resources=[s3_bucket.bucket_arn],
                principals=[aws_iam.AccountPrincipal(account_id=properties.target_account_id)]
            )
        )

        # grant permissions on the items in the bucket to any principal in the account
        s3_bucket.add_to_resource_policy(
            aws_iam.PolicyStatement(
                sid='ObjectPermissions',
                effect=aws_iam.Effect.ALLOW,
                actions=['s3:*'],
                resources=[s3_bucket.arn_for_objects('*')],
                principals=[aws_iam.AccountPrincipal(account_id=properties.target_account_id)]
            )
        )

        s3_bucket.add_lifecycle_rule(
            abort_incomplete_multipart_upload_after=Duration.days(1),
            enabled=True,
            expiration=Duration.days(90),
            id='ExpireObjectsAfter90Days')