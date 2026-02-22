"""
Stub file for Ignition's system module.
This module is provided by the Ignition platform at runtime.
This stub is only for IDE type checking and autocomplete support.
"""


class perspective:
    """Ignition Perspective module"""

    @staticmethod
    def print(message):
        """
        Print to the Perspective console

        Args:
            message: The message to print
        """
        pass


class dataset:
    """Ignition Dataset module"""

    @staticmethod
    def toDataSet(headers, data):
        """
        Create a dataset from headers and data

        Args:
            headers: List of column headers
            data: List of row data

        Returns:
            Dataset object
        """
        pass

    @staticmethod
    def toCSV(dataset):
        """
        Convert a dataset to CSV format

        Args:
            dataset: The dataset to convert

        Returns:
            CSV string
        """
        pass
