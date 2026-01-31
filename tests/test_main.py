import unittest
from seal.main import main

class TestMain(unittest.TestCase):
    def test_main(self):
        self.assertEqual(main(), "Hello from Seal!")

if __name__ == '__main__':
    unittest.main()
