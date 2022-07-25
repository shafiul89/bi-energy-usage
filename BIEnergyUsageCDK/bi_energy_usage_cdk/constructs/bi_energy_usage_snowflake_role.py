from aws_cdk import (
    aws_s3,
    aws_iam,
    Stack
)
from constructs import Construct


class EnergyUsageSnowflakeRoleProperties:
    """
    Configuration values for creating an instance of the EnergyUsageSnowflakeRoleConstruct class.
    """

    def __init__(self, snowflake_principal_arn: str, snowflake_principal_external_id: str, bucket: aws_s3.Bucket):
        """
        Create configuration values for creating an instance of the EnergyUsageSnowflakeRoleConstruct class.

        Parameters
        ----------
        snowflake_principal_arn : str
            The AWS ARN of the Snowflake principal - taken from the Snowflake storage integration.
        snowflake_principal_external_id : str
            The external ID value  - taken from the Snowflake storage integration.
        bucket : aws_s3.Bucket
            The S3 bucket which Snowflake is granted permission to read/write to.
        """
        self.snowflake_principal_arn = snowflake_principal_arn
        self.snowflake_principal_external_id = snowflake_principal_external_id
        self.bucket = bucket


class EnergyUsageSnowflakeRoleConstruct(Construct):
    """
    A construct that creates a new IAM role and grants Snowflake permission to assume that role to access S3 buckets.
    """

    def __init__(self, scope: Construct, construct_id: str, *, properties: EnergyUsageSnowflakeRoleProperties) -> None:
        """
        Create an IAM role with associated policies for Snowflake to assume in order to access CRUK S3 buckets.

        Parameters
        ----------
        scope : str
            The scope where the construct should be created.
        construct_id : str
            The logical name of the construct to identify it within the scope.
        properties : EnergyUsageSnowflakeRoleProperties
            Configuration values for creating the construct.
        """
        super().__init__(scope, construct_id)

        if len(properties.snowflake_principal_arn) < 5 or len(properties.snowflake_principal_external_id) < 5:
            snowflake_role = aws_iam.Role(self, "role",
                                          assumed_by=aws_iam.AccountPrincipal(Stack.of(self).account))
        else:
            snowflake_role = aws_iam.Role(self, "role",
                                          assumed_by=aws_iam.ArnPrincipal(properties.snowflake_principal_arn),
                                          external_ids=[properties.snowflake_principal_external_id])

        snowflake_role.add_to_policy(
            aws_iam.PolicyStatement(
                sid='SnowflakeBucketPermissions',
                effect=aws_iam.Effect.ALLOW,
                actions=['s3:ListBucket', 's3:GetBucketLocation'],
                resources=[properties.bucket.bucket_arn]
            )
        )

        snowflake_role.add_to_policy(
            aws_iam.PolicyStatement(
                sid='SnowflakeObjectPermissions',
                effect=aws_iam.Effect.ALLOW,
                actions=['s3:PutObject', 's3:GetObject',
                         's3:GetObjectVersion', 's3:DeleteObject', 's3:DeleteObjectVersion'],
                resources=[properties.bucket.arn_for_objects('*')]
            )
        )
