import unittest

from abst.bastion_support.oci_bastion import Bastion


class JsonCase(unittest.TestCase):
    def test_json_generate(self):
        td = Bastion.generate_sample_dict()
        print(td)

if __name__ == '__main__':
    unittest.main()
