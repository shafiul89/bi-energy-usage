import enum

from aws_cdk import (
    aws_ecr,
    Duration
)


class DockerImageLifecycleRules(enum.Enum):
    DEFAULT = 0,
    PROD = 1,
    NON_PROD = 2


def create_repo_lifecycle_rules(create_lifecycle_rules: DockerImageLifecycleRules):
    """
    Create a set of ECR lifecycle rules for managing docker images in an ECR repository.

    Two different sets of lifecycle rules can be created:

    PROD = retain prod-current image for 100 years and the previous nine images.

    NON_PROD = retain stg-current, int-current, test-current and dev-current images for 100 years and all other
    images for seven days.

    Parameters
    ----------
    create_lifecycle_rules : DockerImageLifecycleRules
        The set of lifecycle rules to create.

    Returns
    -------
    list[DockerImageLifecycleRules]
        A list of ECR lifecycle rules.
    """
    if create_lifecycle_rules == DockerImageLifecycleRules.PROD:
        prod_rule = aws_ecr.LifecycleRule(description='Retain prod-current for 100 years',
                                          tag_status=aws_ecr.TagStatus.TAGGED,
                                          tag_prefix_list=['prod-current'],
                                          max_image_age=Duration.days(36500),
                                          rule_priority=1)
        count = 10
        default_rule = aws_ecr.LifecycleRule(description=f'Retain last {count} images.',
                                             tag_status=aws_ecr.TagStatus.ANY,
                                             max_image_count=count)
        lifecycle_rules = [prod_rule, default_rule]
    else:
        dev_rule = aws_ecr.LifecycleRule(description='Retain dev-current for 100 years',
                                         tag_status=aws_ecr.TagStatus.TAGGED,
                                         tag_prefix_list=['dev-current'],
                                         max_image_age=Duration.days(36500),
                                         rule_priority=1)
        test_rule = aws_ecr.LifecycleRule(description='Retain test-current for 100 years',
                                          tag_status=aws_ecr.TagStatus.TAGGED,
                                          tag_prefix_list=['test-current'],
                                          max_image_age=Duration.days(36500),
                                          rule_priority=2)
        int_rule = aws_ecr.LifecycleRule(description='Retain int-current for 100 years',
                                         tag_status=aws_ecr.TagStatus.TAGGED,
                                         tag_prefix_list=['int-current'],
                                         max_image_age=Duration.days(36500),
                                         rule_priority=3)
        stg_rule = aws_ecr.LifecycleRule(description='Retain stg-current for 100 years',
                                         tag_status=aws_ecr.TagStatus.TAGGED,
                                         tag_prefix_list=['stg-current'],
                                         max_image_age=Duration.days(36500),
                                         rule_priority=4)
        days = 7
        default_rule = aws_ecr.LifecycleRule(description=f'Retain other images for {days} days.',
                                             tag_status=aws_ecr.TagStatus.ANY,
                                             max_image_age=Duration.days(days))
        lifecycle_rules = [dev_rule, test_rule, int_rule, stg_rule, default_rule]
    return lifecycle_rules
