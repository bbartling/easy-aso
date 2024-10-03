import unittest
from abc import ABC
from easy_aso.easy_aso import EasyASO


class TestEasyASOAbstractMethods(unittest.TestCase):
    def test_easy_aso_is_abstract(self):
        # Check that EasyASO is an abstract class
        self.assertTrue(issubclass(EasyASO, ABC))


class TestValidEasyASOImplementation(unittest.TestCase):
    def test_valid_easy_aso_subclass(self):
        # Define a valid subclass that implements all abstract methods
        class ValidEasyASO(EasyASO):
            async def on_start(self):
                pass

            async def on_step(self):
                pass

            async def on_stop(self):
                pass

        # Mock or pass a safe argument list to prevent argument parsing issues
        instance = ValidEasyASO(args=["--name", "test", "--instance", "1"])

        # Ensure the instance is created without errors
        self.assertIsInstance(instance, ValidEasyASO)


if __name__ == "__main__":
    unittest.main()
