from typing import List, Union

from taskcat._config import Config
from taskcat._tui import TerminalPrinter
from taskcat.testing import CFNTest
from taskcat.testing.ab_test import Test

T = List[Test]


class TestManager:
    """Manages the lifecycle of different kinds of Tests. All Tests
    must implement a run and clean_up method. They must also take a Config and
    Printer objest. See the Abstract Class Test for more info.
    """

    def __init__(
        self,
        config: Config,
        printer: Union[TerminalPrinter, None] = None,
        tests: Union[T, None] = None,
    ):

        self.config = config
        self.printer = printer
        # The defaults in the future will be Lint, Unit, Deploy in that order.
        self.tests: T = [CFNTest(config, printer)]

        if tests:
            self.update_tests(tests)

    def start(self):
        """Calls the run method of the configured tests.
        """

        for test in self.tests:
            test.run()

    def end(self):
        """Calls the clean_up method on all configured tests.
        """

        for test in self.tests:
            test.clean_up()

    def update_tests(self, tests: T) -> None:
        new_tests: T = []

        # This may have not been the best way to do this
        # but its important that the lis of tests maintain their order.
        for i in range(len(self.tests)):
            match = False
            for test in tests:
                # Mypy unable to understand `type(self.tests[i]) is type(test)`
                if type(self.tests[i]).__name__ == type(test).__name__:
                    new_tests.append(test)
                    match = True
                    break
            if not match:
                new_tests.append(self.tests[i])
