from aws_cdk import (
    aws_sns,
    aws_sns_subscriptions
)
from constructs import Construct


class EnergyUsageNotificationProperties:
    """
    Configuration values for creating an instance of the EnergyUsageNotificationConstruct class.
    """

    def __init__(self, base_name: str, subscription_email_address: str):
        """
        Create configuration values for creating an instance of the EnergyUsageNotificationConstruct class.

        Parameters
        ----------
        base_name : str
            The base name of the SNS resources to creates.
        subscription_email_address : str
            The single email address to subscribe to the SNS topic.  It is expected this will be the email
            address of a CRUK AD distribution group.
        """
        self.base_name = base_name
        self.subscription_email_address = subscription_email_address


class EnergyUsageNotificationConstruct(Construct):
    """
    A construct that creates an SNS topic and SNS subscription.
    """

    def __init__(self, scope: Construct, construct_id: str, *, properties: EnergyUsageNotificationProperties) -> None:
        """
        Create a construct that creates a new SNS topic and SNS subscription.

        Parameters
        ----------
        scope : str
            The scope where the construct should be created.
        construct_id : str
            The logical name of the construct to identify it within the scope.
        properties : EnergyUsageNotificationProperties
            Configuration values for creating the construct.
        """
        super().__init__(scope, construct_id)

        topic = aws_sns.Topic(self, "topic", topic_name=properties.base_name, display_name=properties.base_name)
        email_subscription = aws_sns_subscriptions.EmailSubscription(properties.subscription_email_address)
        topic.add_subscription(email_subscription)
        self.topic = topic
