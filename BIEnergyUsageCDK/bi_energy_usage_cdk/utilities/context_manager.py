import aws_cdk
import os


class AppInfoContext:
    """
    Values from the 'app-info' section of the cdk.json file.

    Attributes
    ----------
    root_name : str
        The prefix for AWS resource names.
    service_name : :obj:`int`, optional
        The service name part of AWS resource names.
    product_name : str
        If a value is specified, then a product_name tag with the specified value is attached to all AWS resources.
    support_level : str
        If a value is specified, then a support_level tag with the specified value is attached to all AWS resources.
    cost_centre : str
        If a value is specified, then a cost_centre tag with the specified value is attached to all AWS resources.
    sub_project_code : str
        If a value is specified, then a sub_project_code tag with the specified value is attached to all AWS resources.
    """

    def __init__(self, context_data: dict):
        """
        Create a context object representing values from the 'app-info' section of the cdk.json file.

        Parameters
        ----------
        context_data : dict
            A dictionary of values from the 'app-info' section of the config file.
        """
        # values used for resource naming
        self.root_name = str(context_data['root-name'])
        self.service_name = str(context_data['service-name'])
        # values to be tagged onto all resources created
        self.product_name = str(context_data['product-name'])
        self.support_level = str(context_data['support-level'])
        self.cost_centre = str(context_data['cost-centre'])
        self.sub_project_code = str(context_data['sub-project-code'])


class CodeConnectionContext:
    """
    Values from the 'code-connection' section of the cdk.json file.

    Attributes
    ----------
    arn : str
        The ARN of the Code Connection in AWS (which must be manually created).
    github_owner_name : str
        The account name of the GitHub account where the solution source code is located.
    github_repo_name : str
        The name of the GitHub repo where the solution source code is located.
    github_branch_name : str
        The name of the branch where the solution source code is to be taken from.
    """

    def __init__(self, context_data: dict):
        """
        Create a context object representing values from the 'code-connection' section of the cdk.json file.

        Parameters
        ----------
        context_data : dict
            A dictionary of values from the 'code-connection' section of the config file.
        """
        self.arn = str(context_data['arn'])
        self.github_owner_name = str(context_data['github-owner-name'])
        self.github_repo_name = str(context_data['github-repo-name'])
        self.github_branch_name = str(context_data['github-branch-name'])


class PipelineContext:
    """
    Values from the 'pipeline' section of the cdk.json file.

    Attributes
    ----------
    trigger_on_push : bool
        Should the pipeline automatically executed when a change is committed to the repo in GitHub?
    docker_deploy : bool
        Should then pipeline build and deploy the docker image?
    """

    def __init__(self, context_data: dict):
        """
        Create a context object representing values from the 'pipeline' section of the cdk.json file.

        Parameters
        ----------
        context_data : dict
            A dictionary of values from the 'pipeline' section of the config file.
        """
        self.trigger_on_push = bool(context_data['trigger-on-push'])
        self.docker_deploy = bool(context_data['docker-deploy'])


class EnvironmentSettingsContext:
    """
    Values from the per environment 'settings' section of the cdk.json file.

    Attributes
    ----------
    use_default_root_name : bool
        If True then the app-info/root-name value is used as the prefix for AWS resource names, otherwise the prefix
        for AWS resource names is taken from the CRUK_BI_CUSTOM_RESOURCE_ROOT_NAME environment variable.
    """

    def __init__(self, context_data: dict):
        """
        Create a context object representing values from the per environment 'settings' section of the cdk.json file.

        Parameters
        ----------
        context_data : dict
            A dictionary of values from the per environment 'settings' section of the config file.
        """
        self.use_default_root_name = context_data['use-default-root-name'].upper() == 'Y'


class EnvironmentContext:
    """
    Values from the per environment section of the cdk.json file.

    Attributes
    ----------
    environment_name : str
        The name of the environment.
    account_id : str
        The AWS account ID where the environment will be deployed.
    vpc_id : str
        The ID of the AWS VPC to be used for those AWS resources requiring a VPC.
    private_subnet_ids : list(str)
        A list of subnet IDs to be used for those AWS resources requiring a subnet.
    settings : EnvironmentSettingsContext
        A set of general environment-specific settings.
    """

    def __init__(self, environment_name: str, context_data: dict):
        """
        Create a context object representing values from the per environment section of the cdk.json file.

        Parameters
        ----------
        context_data : dict
            A dictionary of values from the per environment section of the config file.
        """
        self.environment_name = environment_name
        self.account_id = str(context_data['account-id'])
        self.vpc_id = str(context_data['vpc-id'])
        self.private_subnet_ids = [str(x) for x in context_data['private-subnet-ids']]
        self.settings = EnvironmentSettingsContext(context_data['settings'])


class EnvironmentsContext:
    """
    Values from the 'environments' section of the cdk.json file.

    Attributes
    ----------
    sbox : EnvironmentContext
        Context/settings for the sandbox environment.
    pers : EnvironmentContext
        Context/settings for a personal development environment.
    dev : EnvironmentContext
        Context/settings for the development environment.
    test : EnvironmentContext
        Context/settings for the test environment.
    int : EnvironmentContext
        Context/settings for the integration environment.
    stg : EnvironmentContext
        Context/settings for the staging environment.
    prod : EnvironmentContext
        Context/settings for the production environment.
    """

    def __init__(self, context_data: dict):
        """
        Create a context object representing values from the 'environments' section of the cdk.json file.

        Parameters
        ----------
        context_data : dict
            A dictionary of values from the 'environments' section of the config file.
        """
        self.sbox = EnvironmentContext('sbox', context_data['sbox'])
        self.pers = EnvironmentContext('pers', context_data['pers'])
        self.dev = EnvironmentContext('dev', context_data['dev'])
        self.test = EnvironmentContext('test', context_data['test'])
        self.int = EnvironmentContext('int', context_data['int'])
        self.stg = EnvironmentContext('stg', context_data['stg'])
        self.prod = EnvironmentContext('prod', context_data['prod'])
        self.all = {
            "sbox": self.sbox,
            "pers": self.pers,
            "dev": self.dev,
            "test": self.test,
            "int": self.int,
            "stg": self.stg,
            "prod": self.prod,
        }

    def get_dict(self):
        """
        Get a dictionary that contains the context/setting values for each environment.

        This is a utility method that helps generate a printable set of context/setting values.  The vars() function
        returns the property/field values of an object as a dictionary (which is printable) which - compared to the
        original object (an instance of the EnvironmentContext class) is not printable.

        Returns
        -------
        dict(str)
            A dictionary containing the context/setting values for each environment.
        """
        x = {
            "sbox": vars(self.sbox),
            "pers ": vars(self.pers),
            "dev": vars(self.dev),
            "test": vars(self.test),
            "int": vars(self.int),
            "stg": vars(self.stg),
            "prod": vars(self.prod)
        }
        return x


class ContextManager:
    """
    The ContextManager class makes it easier to access values in the cdk.json file.

    Attributes
    ----------
    app_info : AppInfoContext
        Context/settings from the 'app-info' part of the cdk.json file.
    code_connection : CodeConnectionContext
        Context/settings from the 'code-connection' part of the cdk.json file.
    pipeline : PipelineContext
        Context/settings from the 'pipeline' part of the cdk.json file.
    region : str
        The AWS region where the resources will be deployed, e.g. eu-west-2.
    environments : EnvironmentsContext
        Context/settings from the 'environments' part of the cdk.json file.
    """

    def __init__(self):
        """
        Create a context object to read values from the cdk.json file.
        """
        app = aws_cdk.App()
        context_data = app.node.try_get_context("cruk-context")
        self.app_info = AppInfoContext(context_data['app-info'])
        self.code_connection = CodeConnectionContext(context_data['code-connection'])
        self.pipeline = PipelineContext(context_data['pipeline'])
        self.region = str(context_data['region'])
        self.environments = EnvironmentsContext(context_data['environments'])

    def get_resource_base_name(self, environment_name: str, suffix: str, use_default_root_name: bool = True):
        """
        Compute a resource name based on context/settings, the environment and other parameters.

        The resource name is computed as follows:

        (root name)-(environment name)-(service name)-(suffix, if specified)

        e.g. cruk-bi-dev-energy-usage-repo

        The root name is taken from the app-info/root-name value in the cdk.json file.
        If use_default_root_name = False, then the root-name is taken from the CRUK_BI_CUSTOM_RESOURCE_ROOT_NAME
        environment variable.

        The service name is taken from the app-info/service-name value in the cdk.json file.

        The environment name and suffix are passed as parameters to the function.

        Parameters
        ----------
        environment_name : str
            The name of the environment, e.g. dev
        suffix : str
            The suffix of the name, often the logical name of the resource, e.g. repo
        use_default_root_name : bool
            True to take the root-name from the cdk.json file, False to the take root-name from the
            CRUK_BI_CUSTOM_RESOURCE_ROOT_NAME environment variable.

        Returns
        -------
        str
            The generate resource name.
        """
        if use_default_root_name:
            base_name = self.app_info.root_name
            if len(base_name) == 0 or base_name.isspace():
                raise ValueError('app-info/root-name must be specified in the cdk.json file.')
        else:
            base_name = os.getenv('CRUK_BI_CUSTOM_RESOURCE_ROOT_NAME', '')
            if len(base_name) == 0 or base_name.isspace():
                raise ValueError('The CRUK_BI_CUSTOM_RESOURCE_ROOT_NAME environment variable must be set.')
        if environment_name is not None and len(environment_name) > 0 and not environment_name.isspace():
            base_name += '-' + environment_name
        base_name += '-' + self.app_info.service_name
        if suffix is not None and len(suffix) > 0 and not suffix.isspace():
            base_name += '-' + suffix
        return base_name

    def print_context(self):
        """
        Print the context values for debugging purposes.

        Returns
        -------
        None
            No return value.
        """
        print('Context Manager Contents')
        print('  app_info = ' + str(vars(self.app_info)))
        print('  code_connection = ' + str(vars(self.code_connection)))
        print('  pipeline = ' + str(vars(self.pipeline)))
        print('  region = ' + str(self.region))
        print('  environments = ' + str(self.environments.get_dict()))