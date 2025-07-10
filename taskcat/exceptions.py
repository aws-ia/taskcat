"""
TaskCat Exception Classes

This module defines custom exception classes used throughout the TaskCat application.
These exceptions provide specific error handling for various failure scenarios that
can occur during CloudFormation template testing and deployment operations.

The exception hierarchy allows for granular error handling and provides meaningful
error messages to help users diagnose and resolve issues.
"""


class TaskCatException(Exception):
    """
    Base exception class for all TaskCat-specific errors.
    
    This is the parent class for all custom exceptions in TaskCat. It should be
    raised when TaskCat experiences a fatal error that prevents normal operation.
    
    This exception is typically caught at the CLI level to provide user-friendly
    error messages and appropriate exit codes.
    
    Attributes:
        message (str): Human-readable error message describing the issue
    """
    
    def __init__(self, message="TaskCat encountered a fatal error"):
        """
        Initialize the TaskCat exception.
        
        Args:
            message (str): Descriptive error message. Defaults to generic message.
        """
        self.message = message
        super().__init__(self.message)


class InvalidActionError(TaskCatException):
    """
    Exception raised when an invalid action or command is supplied to TaskCat.
    
    This exception is typically raised during command-line argument parsing or
    when validating user input that specifies what action TaskCat should perform.
    
    Attributes:
        expression (str): The invalid input expression that caused the error
        message (str): Human-readable error message
    """

    def __init__(self, expression, message=None):
        """
        Initialize the InvalidActionError exception.
        
        Args:
            expression (str): The invalid input expression that triggered the error
            message (str, optional): Custom error message. If not provided, a default
                                   message will be generated using the expression.
        """
        self.expression = expression
        
        # Generate default message if none provided
        if message is None:
            message = f"Invalid action or expression: '{expression}'"
        
        self.message = message
        super().__init__(self.message)
