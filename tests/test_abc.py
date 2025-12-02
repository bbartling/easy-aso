import unittest
from abc import ABC
from easy_aso.easy_aso import EasyASO
import argparse


class TestEasyASOImport(unittest.TestCase):
    def test_easy_aso_is_abstract(self):
        # Check that EasyASO is an abstract class
        self.assertTrue(issubclass(EasyASO, ABC))


class TestEasyASOInitialization(unittest.TestCase):
    def test_easy_aso_initialization(self):
        # Define a valid subclass that implements all abstract methods
        class ValidEasyASO(EasyASO):
            async def on_start(self):
                pass

            async def on_step(self):
                pass

            async def on_stop(self):
                pass

        # Simulate argument parsing
        parser = argparse.ArgumentParser()
        parser.add_argument("--no-bacnet-server", action="store_true")
        args = parser.parse_args(["--no-bacnet-server"])

        # Create an instance of the subclass with parsed arguments
        instance = ValidEasyASO(args=args)

        # Ensure the instance is created without errors
        self.assertIsInstance(instance, ValidEasyASO)

        # Check if the 'no_bacnet_server' flag is set correctly
        self.assertTrue(instance.no_bacnet_server)


class TestEasyASOArguments(unittest.TestCase):
    def test_argument_parsing(self):
        # Simulate argument parsing for --no-bacnet-server flag
        parser = argparse.ArgumentParser()
        parser.add_argument("--no-bacnet-server", action="store_true")
        args = parser.parse_args(["--no-bacnet-server"])

        # Ensure the --no-bacnet-server flag is set to True
        self.assertTrue(args.no_bacnet_server)


class TestIncompleteEasyASO(unittest.TestCase):
    def test_incomplete_subclass_fails(self):
        # Define a subclass that does not implement all abstract methods
        class IncompleteEasyASO(EasyASO):
            async def on_start(self):
                pass

            async def on_step(self):
                pass

            # Missing `on_stop`

        # Expect a TypeError due to missing abstract method
        with self.assertRaises(TypeError):
            IncompleteEasyASO()


if __name__ == "__main__":
    unittest.main()
