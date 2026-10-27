"""Base Pipeline Class"""
from abc import ABC, abstractmethod
from datetime import datetime
import logging


class PipelineBase(ABC):
    """Base class for all pipelines."""

    def __init__(self):
        """
        Start the pipeline with the name and logger.
        """
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.start_time = None
        self.end_time = None

    def run(self) -> bool:
        """
        Run the pipeline and log the start and end time.

        :returns: True if the pipeline finished successfully, False otherwise.
        :rtype: bool
        """
        try:
            self.start_time = datetime.now()
            self.logger.info('Pipeline "%s" started at "%s".',
                             self.name, self.start_time)

            self.setup_pipeline()
            self.execute_pipeline()

            self.end_time = datetime.now()
            elapsed_time = self.end_time - self.start_time
            self.logger.info(
                'Pipeline "%s" finalized at "%s". Elapsed time: "%s".', self.name, self.end_time, elapsed_time)
            return True
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Uma falha isolada nao interrompe as demais pipelines; o main.py consolida o status final.
            self.logger.error(
                'Error in "%s". Pipeline execution error. Message: "%s"',
                self.name,
                e,
                exc_info=True
            )
            return False

    def setup_pipeline(self):
        """
        Optional hook to setup the pipeline before execution.
        """

    @abstractmethod
    def execute_pipeline(self):
        """
        Abstract method to execute the pipeline.
        """
