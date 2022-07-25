from aws_cdk import (
    aws_ssm
)
from constructs import Construct


class EnergyUsageParametersProperties:
    """
    Configuration values for creating an instance of the EnergyUsageParametersConstruct class.
    """

    def __init__(self, base_name: str,
                 parameter_definitions: dict[str, str],  # once AWS CodeBuild supports Python 3.10, add " | None"
                 parameter_values: dict[str, str]):  # once AWS CodeBuild supports Python 3.10, add " | None"
        """
        Create configuration values for creating an instance of the EnergyUsageParametersConstruct class.

        Parameters
        ----------
        base_name : str
            The base name that will be the prefix in the name of all Systems Manager parameters that are created.
        parameter_definitions : dict[str, str]
            A dictionary of parameter names and parameter descriptions.
        parameter_values : dict[str, str]
            A dictionary of parameter names and parameter values.
        """
        self.base_name = base_name
        self.parameter_definitions = parameter_definitions
        self.parameter_values = parameter_values


# The Systems Manager Parameter Store parameters could be created explicitly one-by-one below - but this
# would make them laborious to create.  A better approach is to create the parameters dynamically based on
# the contents of the cdk.json file.  This also means the parameter values are set in the CDK.json file
# which makes the parameter values much easier to maintain.

class EnergyUsageParametersConstruct(Construct):
    """
    A construct that creates a set of Systems Manager Parameter Store parameters.
    """

    def __init__(self, scope: Construct, construct_id: str, *, properties: EnergyUsageParametersProperties) -> None:
        """
        Create a construct that creates a set of Systems Manager Parameter Store parameters.

        Parameters
        ----------
        scope : str
            The scope where the construct should be created.
        construct_id : str
            The logical name of the construct to identify it within the scope.
        properties : EnergyUsageParametersProperties
            Configuration values for creating the construct.
        """
        super().__init__(scope, construct_id)

        parameters = {}

        # if we have parameter definitions and parameter values, then iterate through the parameter definitions
        # to create the corresponding AWS Systems Manager Parameter Store parameters.

        if properties.parameter_definitions is not None:
            if properties.parameter_values is None:
                raise KeyError(f'No parameter values have been specified in the cdk.json file.')

            for parameter_name, parameter_description in properties.parameter_definitions.items():
                if parameter_name not in properties.parameter_values:
                    raise KeyError(f'No value is specified in the cdk.json file for parameter {parameter_name}.')
                parameter_value = properties.parameter_values[parameter_name]
                parameter = aws_ssm.StringParameter(
                    self, parameter_name, parameter_name=f'/{properties.base_name}/{parameter_name}',
                    string_value=parameter_value, type=aws_ssm.ParameterType.STRING,
                    description=parameter_description)
                parameters[parameter_name] = parameter

        # return a dictionary that contains the parameter objects (so that they can be linked to ECS task definition)
        self.parameters = parameters
